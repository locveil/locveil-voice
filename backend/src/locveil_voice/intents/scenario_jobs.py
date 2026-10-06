"""Scenario jobs — the domain view of the bridge's tier-3 job API (ARCH-69, design
`docs/design/scenario_jobs_voice.md` §2.1; contract `catalog-contract.md` "Jobs (since v1.12)").

A scenario switch on the bridge is a chain of device steps that can take most of a minute.
Sent with `wait: false` it comes back as a `202` with a `job_id`; the job is then followed
over the bridge's event stream to exactly one terminal event. This module holds what the
domain knows about such a job — the boundary types the `ScenarioJobEventsPort` yields and
the two speech-policy helpers (the ceiling bucket spoken at acceptance, the remaining
seconds spoken to a second command). It is convention-blind like `device_commands.py`: no
HTTP, no SSE, no event-type strings beyond the enum — the adapter parses the wire into these.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Union

# The watchdog W = max_duration_ms × 1.25 + 2 s (the bridge spec §6.5; round-2's sizing rule)
# and the hard cap H = W + 30 s (one more reconnect-and-GET cycle) — follower constants,
# not config (recovery policy, BUG-17 precedent; design §5/§6).
WATCHDOG_FACTOR = 1.25
WATCHDOG_MARGIN_S = 2.0
HARD_CAP_EXTRA_S = 30.0
# A record resumed later than this after acceptance is dropped silently (design §3).
STALE_RESUME_S = 3600.0


class JobEventKind(Enum):
    """What the events port yields. STREAM_OPEN is synthetic: every (re)connect of the
    underlying stream, the follower's cue to read the record (§6.2/§6.4 — no replay)."""
    STREAM_OPEN = "stream_open"
    STARTED = "started"
    PHASE = "phase"
    STEP = "step"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class JobFailure:
    """One entry of the terminal event's `failures[]` — ids, never words."""
    device: str
    command: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class JobEvent:
    kind: JobEventKind
    job_id: Optional[str] = None
    room_id: Optional[str] = None
    # terminal only
    job_state: Optional[str] = None          # "succeeded" | "failed"
    failures: Tuple[JobFailure, ...] = ()
    result_scenario: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass(frozen=True)
class JobRecord:
    """`GET /scenario/jobs/{id}` — the §3 record, as much of it as the follower speaks from."""
    job_id: str
    room_id: str
    kind: str                                # "switch" | "stop" | "reconcile"
    target: str                              # scenario id, or "none" for a stop
    state: str                               # "running" | "succeeded" | "failed"
    max_duration_ms: Optional[int] = None
    failures: Tuple[JobFailure, ...] = ()
    result_scenario: Optional[str] = None
    duration_ms: Optional[int] = None

    @property
    def terminal(self) -> bool:
        return self.state in ("succeeded", "failed")


@dataclass(frozen=True)
class JobLookupMiss:
    """The record could not be read: `unknown` (404 job_unknown — the bridge restarted and
    forgot it) or `unreachable` (the bridge did not answer at all)."""
    reason: str


JobLookup = Union[JobRecord, JobLookupMiss]


# --- timing ----------------------------------------------------------------------------------

def watchdog_seconds(max_duration_ms: int) -> float:
    """W: 61 500 → 78.875 s."""
    return max_duration_ms / 1000.0 * WATCHDOG_FACTOR + WATCHDOG_MARGIN_S


def hard_cap_seconds(max_duration_ms: int) -> float:
    """H = W + 30 s: 61 500 → 108.875 s."""
    return watchdog_seconds(max_duration_ms) + HARD_CAP_EXTRA_S


# --- speech policy (design §4.1 / §4.4) ------------------------------------------------------

def ceiling_bucket(max_duration_ms: Optional[int]) -> Optional[str]:
    """The ceiling phrase spoken at acceptance, as a template suffix key:
    None (≤ 5 s — nothing appended) | "seconds" (≤ 20 s, with N) | "half_minute" (≤ 45 s) |
    "minute" (≤ 90 s) | "minutes" (longer)."""
    if max_duration_ms is None:
        return None
    s = math.ceil(max_duration_ms / 1000.0)
    if s <= 5:
        return None
    if s <= 20:
        return "seconds"
    if s <= 45:
        return "half_minute"
    if s <= 90:
        return "minute"
    return "minutes"


def round_up_to_five(seconds: float) -> int:
    """Spoken seconds are rounded UP to a multiple of five, floor five."""
    return max(5, int(math.ceil(seconds / 5.0)) * 5)


def remaining_seconds(accepted_at: float, max_duration_ms: int, now: float) -> int:
    """How long the running job may still take, for the «секунд через N» refusal."""
    return round_up_to_five(accepted_at + max_duration_ms / 1000.0 - now)
