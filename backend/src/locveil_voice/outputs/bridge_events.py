"""BridgeEventsClient — the locveil-bridge scenario-job SSE adapter (ARCH-69).

One of the TWO modules that know the bridge exists (`mqtt_integration.md` §4): `bridge.py`
speaks its REST surface, this one its `GET /events/scenarios` channel (contract v1.12 "Jobs";
design `docs/design/scenario_jobs_voice.md` §2.2). Implements the domain's
`ScenarioJobEventsPort`.

- **One persistent subscription for the adapter's lifetime**, opened at `start()` whether or
  not a job runs — so "subscribe before launching" (the bridge spec §6.3) holds by
  construction and no turn ever waits for a connect.
- **The dead-stream rule IS the socket timeout**: the bridge sends a `keepalive` after each
  ~1 s of silence, so `sock_read=5 s` without any frame means the stream is dead (§8 d) and
  the reader reconnects.
- **Reconnect** with the §8 d backoff — 1, 2, 4, 8, 16, 30 s cap, ±25 % jitter — forever; a
  successful connect resets it. After EVERY successful connect (the first included) each
  subscriber gets a synthetic `STREAM_OPEN`: the follower's cue to read the record, because
  the channel never replays (§6.2).
- **Housekeeping frames** (`connected`, `keepalive`) are consumed here and never forwarded;
  a terminal event without `job_id` (the startup-restore notification) is dropped too.
- **Fan-out** by room over bounded queues; on overflow the oldest frame is dropped and a
  `STREAM_OPEN` queued so the follower re-syncs by GET — the mirror of the bridge's
  slow-consumer rule (§6.7).
- **The two GETs** reuse `BridgeClient._request_json` (one HTTP seam; tests stub one function)
  and the fallback timeout — reads, nothing published sizes them.

Hand-written SSE reader (lines `id:` / `data:` / `event:` / `:`; an empty line ends a frame)
— ~30 lines, no new dependency.
"""

import asyncio
import json
import logging
import random
from typing import Any, AsyncIterable, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple

import aiohttp

from ..intents.ports import ScenarioJobEventsPort
from ..intents.scenario_jobs import (
    JobEvent,
    JobEventKind,
    JobFailure,
    JobLookup,
    JobLookupMiss,
    JobRecord,
)

logger = logging.getLogger(__name__)

EVENTS_PATH = "/events/scenarios"
DEAD_STREAM_S = 5.0                      # §8 d: no frame of any kind for ~5 s = dead
BACKOFF_STEPS_S = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)
BACKOFF_JITTER = 0.25
QUEUE_BOUND = 64

_HOUSEKEEPING = frozenset({"connected", "keepalive"})
_TERMINAL_TYPES = frozenset({"scenario_switched", "scenario_shutdown"})
_KIND_BY_TYPE = {
    "scenario_job_started": JobEventKind.STARTED,
    "scenario_phase": JobEventKind.PHASE,
    "scenario_step": JobEventKind.STEP,
}

RequestJson = Callable[..., Awaitable[Tuple[int, Dict[str, Any]]]]


# --- wire → domain --------------------------------------------------------------------------------

def _failures(raw: Any) -> Tuple[JobFailure, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(JobFailure(device=str(f.get("device", "")), command=f.get("command"),
                            error=f.get("error"))
                 for f in raw if isinstance(f, dict))


def parse_job_event(payload: Dict[str, Any]) -> Optional[JobEvent]:
    """One `data:` JSON → a `JobEvent`, or None for frames the follower never sees
    (housekeeping, unknown types, a terminal without `job_id`)."""
    event_type = payload.get("eventType")
    if event_type in _HOUSEKEEPING:
        return None
    job_id = payload.get("job_id")
    room_id = payload.get("room_id")
    if event_type in _TERMINAL_TYPES:
        if not job_id:
            return None     # the startup restore's tracking notification — consumers filter on job_id
        duration = payload.get("duration_ms")
        return JobEvent(kind=JobEventKind.TERMINAL, job_id=job_id, room_id=room_id,
                        job_state=payload.get("job_state"),
                        failures=_failures(payload.get("failures")),
                        result_scenario=(payload.get("scenario_id")
                                         if event_type == "scenario_switched" else "none"),
                        duration_ms=int(duration) if duration is not None else None)
    kind = _KIND_BY_TYPE.get(str(event_type))
    if kind is None or not job_id:
        return None
    return JobEvent(kind=kind, job_id=job_id, room_id=room_id)


def parse_job_record(payload: Dict[str, Any]) -> JobRecord:
    """`GET /scenario/jobs/{id}` 200 body → the domain record."""
    ceiling = payload.get("max_duration_ms")
    duration = payload.get("duration_ms")
    return JobRecord(
        job_id=str(payload["job_id"]), room_id=str(payload.get("room_id", "")),
        kind=str(payload.get("kind", "switch")), target=str(payload.get("target", "none")),
        state=str(payload.get("state", "running")),
        max_duration_ms=int(ceiling) if ceiling is not None else None,
        failures=_failures(payload.get("failures")),
        result_scenario=payload.get("result_scenario"),
        duration_ms=int(duration) if duration is not None else None)


def backoff_seconds(attempt: int, rng: Optional[random.Random] = None) -> float:
    """The §8 d backoff for the `attempt`-th consecutive failure (0-based): 1-2-4-8-16-30 s
    with ±25 % jitter, capped."""
    base = BACKOFF_STEPS_S[min(attempt, len(BACKOFF_STEPS_S) - 1)]
    jitter = (rng or random).uniform(-BACKOFF_JITTER, BACKOFF_JITTER)
    return base * (1.0 + jitter)


async def read_sse_frames(lines: AsyncIterable[bytes]) -> AsyncIterator[Dict[str, Any]]:
    """The SSE reader: yields each frame's `data:` JSON (one `data:` line per frame on this
    channel). `id:` / `event:` / comment lines are read and ignored; an empty line ends a frame."""
    data: List[str] = []
    async for raw in lines:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if line == "":
            if data:
                try:
                    yield json.loads("\n".join(data))
                except ValueError:
                    logger.warning(f"bridge events: unparseable frame {data!r}")
                data = []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        if field == "data":
            data.append(value[1:] if value.startswith(" ") else value)
    if data:
        try:
            yield json.loads("\n".join(data))
        except ValueError:
            logger.warning(f"bridge events: unparseable trailing frame {data!r}")


# --- the adapter ----------------------------------------------------------------------------------

class BridgeEventsClient(ScenarioJobEventsPort):
    """SSE adapter to locveil-bridge's scenarios channel — the job follower's event source."""

    def __init__(self, base_url: str, request_json: RequestJson) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_json = request_json
        self._session: Optional[aiohttp.ClientSession] = None
        self._task: Optional[asyncio.Task] = None
        self._queues: List[Tuple[str, asyncio.Queue]] = []
        self.connected: bool = False

    # --- lifecycle -------------------------------------------------------------------------------

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="bridge-events")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None
        self.connected = False

    # --- the stream (one seam; tests feed `_frames`) ---------------------------------------------

    async def _open(self) -> AsyncIterator[Dict[str, Any]]:
        """One connection's frames; raises on connect failure / dead stream."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=None, sock_read=DEAD_STREAM_S))
        async with self._session.get(f"{self._base_url}{EVENTS_PATH}",
                                     headers={"Accept": "text/event-stream"}) as resp:
            if resp.status != 200:
                raise RuntimeError(f"events channel answered HTTP {resp.status}")
            self._on_connected()
            async for frame in read_sse_frames(resp.content):
                yield frame

    async def _run(self) -> None:
        attempt = 0
        while True:
            try:
                async for frame in self._open():
                    attempt = 0
                    self._dispatch(frame)
                # the bridge closed the stream (shutdown, or it dropped us as slow) → reconnect
                logger.info("bridge events stream closed by the bridge — reconnecting")
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, RuntimeError) as e:
                # the first loss of a connection is worth a warning; the retries behind the
                # backoff are not (a bridge without the channel would warn every 30 s)
                logger.log(logging.WARNING if attempt == 0 else logging.INFO,
                           f"bridge events stream lost ({e}) — reconnecting")
            except Exception as e:  # never let the reader die silently
                logger.error(f"bridge events reader error ({e!r}) — reconnecting")
            self.connected = False
            await asyncio.sleep(backoff_seconds(attempt))
            attempt += 1

    def _on_connected(self) -> None:
        self.connected = True
        logger.info("bridge events stream connected")
        for _, queue in self._queues:
            self._put(queue, JobEvent(kind=JobEventKind.STREAM_OPEN))

    def _dispatch(self, frame: Dict[str, Any]) -> None:
        event = parse_job_event(frame)
        if event is None:
            return
        for room_id, queue in self._queues:
            if event.room_id == room_id:
                self._put(queue, event)

    @staticmethod
    def _put(queue: asyncio.Queue, event: JobEvent) -> None:
        if queue.full():
            # §6.7 mirror: drop the oldest, then make the follower re-sync by GET
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            if event.kind is not JobEventKind.STREAM_OPEN:
                queue.put_nowait(JobEvent(kind=JobEventKind.STREAM_OPEN))
                if queue.full():
                    return
        queue.put_nowait(event)

    # --- ScenarioJobEventsPort -------------------------------------------------------------------

    async def events(self, room_id: str) -> AsyncIterator[JobEvent]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_BOUND)
        entry = (room_id, queue)
        self._queues.append(entry)
        if self.connected:
            # a subscriber joining an open stream still starts with a GET (§6.3)
            self._put(queue, JobEvent(kind=JobEventKind.STREAM_OPEN))
        try:
            while True:
                yield await queue.get()
        finally:
            try:
                self._queues.remove(entry)
            except ValueError:
                pass

    async def get_job(self, job_id: str) -> JobLookup:
        try:
            status, payload = await self._request_json("GET", f"/scenario/jobs/{job_id}")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"bridge unreachable reading job '{job_id}': {e}")
            return JobLookupMiss("unreachable")
        if status == 200 and isinstance(payload, dict) and "job_id" in payload:
            return parse_job_record(payload)
        if status == 404:
            # `{"detail": {"code": "job_unknown", "job_id": "…"}}` — every id from before the
            # bridge's last restart; the bridge cannot vouch for a chain it did not finish
            return JobLookupMiss("unknown")
        logger.warning(f"job read '{job_id}' failed: HTTP {status} {payload}")
        return JobLookupMiss("unreachable")

    async def get_active_scenario(self, room_id: str) -> Optional[str]:
        try:
            status, payload = await self._request_json("GET", f"/scenario/state?room={room_id}")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"bridge unreachable reading scenario state of '{room_id}': {e}")
            return None
        if status == 200 and isinstance(payload, dict) and payload.get("scenario_id"):
            return str(payload["scenario_id"])
        if status == 404:
            return "none"
        logger.warning(f"scenario state read for '{room_id}' failed: HTTP {status} {payload}")
        return None
