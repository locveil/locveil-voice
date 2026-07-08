# Irene — Release Journal

The single **active** chronological log for the release effort ("what happened, when, and why"). Append-only;
newest entries near the top of each dated section.

- **This file holds NO task status and NO scope.** The authoritative task ledger (scope + status) is
  [`RELEASE_PLAN.md`](./RELEASE_PLAN.md); findings/rationale live in `docs/review/*` + `docs/design/*`.
- Entries reference task IDs (e.g. `QUAL-27`) but never assert their status — check the ledger for that.
- **Older entries are frozen in archives** (`one-active-journal`), newest first:
  [`docs/archive/journal/2026-06-23_to_2026-07-02.md`](archive/journal/2026-06-23_to_2026-07-02.md)
  (2026-06-23 … 2026-07-02),
  [`docs/archive/journal/2026-06-15_to_2026-06-22.md`](archive/journal/2026-06-15_to_2026-06-22.md)
  (2026-06-15 … 2026-06-22), [`docs/archive/journal/pre-2026-06-15.md`](archive/journal/pre-2026-06-15.md)
  (2026-05-31 … 2026-06-14). This file keeps **2026-07-04 onward**; grep an archive when reconciliation needs older history.

---

## Action journal

- **2026-07-08 — BUILD-16 DONE (filed + completed same day) — two-disk layout, decided at the live
  WB7 shell.** The user's `df` settled it: `/` has ~800 MB free (docker's default data-root — the
  image wouldn't even fit), `/mnt/data` 2.3 GB, the SD card 61 GB empty. Rule adopted: re-obtainable
  data (checkout, docker images via a `data-root` move to `/mnt/sdcard/docker`, models, logs) → the
  card; precious runtime state → the eMMC. The split lands as one nested bind mount:
  `/mnt/data/mqtt-voice-state` over `/app/assets/state` (timer records + report spool — the only
  durable subtree, verified). An SD card death now loses nothing that can't be re-downloaded, and
  the systemd unit refuses to start with either disk unmounted (`RequiresMountsFor`). Hours-later
  amendment of BUILD-15, same files.

- **2026-07-08 — BUILD-15 DONE (filed + completed same day) — the ops deployment is rack-ready.**
  Walking the install story ahead of ARCH-25 (user question: "which mounts? how do tokens reach the
  container?") exposed that the answer was "one mount, and they don't": no logs mount (file logs
  accumulating in the container layer on flash), no env plumbing at all for `DEEPSEEK_API_KEY` /
  `IRENE_REPORTS_TOKEN` (the LLM tier and problem reporting could never activate on a controller
  deploy), plus a latent uid-1000-vs-root EACCES on the bind mounts that only the rack would have
  caught. All fixed on the bridge's proven pattern — checkout at `/mnt/data/mqtt-voice-config`
  (user-directed twin of `mqtt-bridge-config`), `.assets`/`.logs` mounts, `ops/.env` secrets file,
  chown in update.sh — and INSTALL.md now also covers the aarch64 image variant and points to the
  nginx Plane-B deploy with the `esp32_irene_upstream` wiring seam. Three fewer surprises at the rack.

- **2026-07-08 — QUAL-77 DONE + ARCH-39/ARCH-40 filed — the bridge's desync-repair surface is pinned;
  voice adoption designed-for but deferred.** The bridge maintainer left a handoff note (DRV-5/SCN-11:
  `skipped_reason` idempotence-skip marker + reserved `force` param + scenario
  `reconcile_preview`/`force_reconcile`); all claims verified against the bridge's `contracts/openapi.json`
  at `c32068e` and re-pinned into eval-commons (`7cfd5a7`, catalog/STAMP unchanged, suite 40/40). The
  note's "re-pin the catalog first" worry was already satisfied by QUAL-76 the day before. Voice-side
  analysis with the user: the cross-turn confirmation the device flow needs already exists (the QUAL-31
  one-shot `pending_clarification` slot); the real gap is `_to_delivery_result` dropping
  `no_op`/`skipped_reason`; the scenario flow leans on ARCH-28 durable F&F for its ~25 s executions.
  Decision: post-release — two separate `[deferred]` design tasks filed (ARCH-39 device-level force-confirm,
  ARCH-40 scenario force-reconcile), safety posture recorded in both (never auto-force; the confirmation
  slot IS the human feedback channel).

- **2026-07-07 — QUAL-76 DONE (filed + completed same day).** The bridge published a
  rack-verified catalog (`8159b4b0`, bridge `40f0452`): auralic learns `previous`, zappiti power
  is a toggle. Routine inward re-pin — no fixture binds either device, so only the fixtures doc's
  stamp moved. The re-pin surfaced a silent slip: QUAL-75's PIN.json wrote the bridge repo HEAD
  into `bridge_commit` where the guard expects `STAMP.bridge_commit` (the generator's commit),
  so eval-commons' `test_pin_matches_stamp` had been red since 2026-07-06 without anyone running
  the full suite. Convention restored and documented in the PIN itself; eval-commons 40/40
  (`14ac383`, pushed).

- **2026-07-07 — DOC-10 DONE (filed + completed same day).** The lesson from the ARCH-38
  catch-up became a rule: `websocket-api.md` is now the `ws-protocol-doc-canonical` invariant —
  the WS protocol's single source of truth, updated in the same change as any endpoint or frame
  shape, with design docs deferring to it. And eval-commons got its first CLAUDE.md, seeded with
  the mirror rule (its providers implement that document, never reverse-engineer the protocol)
  plus the contracts-pin ownership rule. The protocol now has one book, and both repos know it.

- **2026-07-07 — ARCH-38 doc/profile catch-up (user review).** Two gaps closed in the same
  breath: `configs/satellite.toml` gained its `[trace]` stanza (off by default, `--trace` flips
  it; segmenter level so satellite traces carry the VAD-tuning frames), and the hand-written
  WebSocket protocol document — `docs/guides/websocket-api.md`, the real protocol reference —
  now teaches `wants_trace`/the `trace` grant/the per-response trace frame, plus the mTLS
  certificate-identity rule on both `/ws/audio` and the reply channel.

- **2026-07-07 — ARCH-38 DONE — satellite tracing shipped, hours after its design.** `--trace` on
  a room node now means something real: one merged file per utterance with the device story (raw
  mic ring, VAD frames, wake-gate verdicts including the skips, the wire exchange with RTT, the
  reply exactly as played) and the controller's execution trace nested inside — delivered as an
  in-band trace frame after each response, granted explicitly at registration, gated by the new
  default-off `[trace] allow_remote_request`. A missing or declined controller half is recorded,
  not fatal. `irene-replay-trace --show-controller` prints the nested half; the captured
  utterance stays replayable for VAD tuning. Suite 1353, pyright 0, 11/11 contracts, config-ui
  clean. The board is back to ARCH-25 + the tag — now with the debugging kit bring-up wanted.

- **2026-07-07 — ARCH-37 DONE (filed + designed same day) → ARCH-38 filed [release].** Satellite
  tracing designed in session: one utterance, one trace, two machines. The satellite gets its
  device story back (`--trace` was silently inert on a room node — raw mic, VAD frames, wake-gate
  verdicts, uplink, reply as played), and the §3 wire contract grows `wants_trace` (default false,
  ESP32-honest) with the controller's execution trace returning as an in-band frame after each
  response — through the mTLS proxy unchanged, gated by a new default-off `[trace]
  allow_remote_request` on the controller. One merged self-contained file per utterance,
  satellite-side. eval-commons needs no change (additive default). Retagged nothing; the release
  gate grows by one deliberate task because bring-up debugging wants this in hand.

- **2026-07-06 — ARCH-36 DONE — the Python satellite, same day as its design.** `irene-satellite`
  turns any Python box into a room node: mic → VAD → wake word «Ирина» locally, the utterance to
  the controller over the same /ws/audio contract the ESP32 firmware will speak, replies played
  back in the room. The uplink core is the eval-commons client grown up (no test-framework dep);
  the wake gate uses an armed-window rule so the wake word's own audio never reaches ASR. The
  fleet TLS plane got its first real client AND its first regression test: a hermetic e2e renders
  the ansible nginx template into docker with a throwaway CA and runs the whole
  CSR→approve→mTLS-wss cycle in 4.3 s — including proof that a kitchen certificate cannot register
  as the bedroom (finding (b): the X-Client-Cert-DN binding is now enforced on both WS endpoints,
  where before nothing consumed the header). Suite 1349, pyright 0, 11/11 import contracts,
  config-ui clean. The release board is down to ARCH-25 — hardware bring-up — and the tag.

- **2026-07-06 — ARCH-34 DONE (retagged `[release]` and shipped hours after filing).** The morning's
  loud thinking became an evening feature: smart-home problem reports now carry the bridge's own
  evidence. When `[outputs.bridge]` is wired, filing a report pulls `GET /reports/evidence` (the
  B-11 seam the bridge shipped in VWB-28, pinned at v1.4 by QUAL-75) and folds the redacted
  envelope into the bundle under `bridge/` — dispatch ring, MQTT window, live device states,
  persisted-vs-live diffs. Every failure to fetch is filed verbatim as evidence in its own right
  («свет не включается» + unreachable bridge is a diagnosis, not a missing attachment). The triage
  lens learned to read the new members first — the point is fixing bridge-involved reports without
  a lens handover. Suite 1337 green, pyright 0; guide, diagram and CHANGELOG updated. With this,
  the whole ARCH-30 arc is closed end-to-end on both repos, same day the bridge finished its half.

- **2026-07-06 — QUAL-75 DONE (filed + completed same day) — contract v1.4 consumed; the bridge
  closed the whole reporting loop from its side in one afternoon.** VWB-28 landed end-to-end over
  there — the UI bug button, the dispatch/MQTT evidence rings, redaction, spool, rate limits — and
  our B-11 amendment came back delivered, not just accepted: `GET /reports/evidence` with the
  `EvidenceEnvelope` as an owned contract surface in openapi. Re-pinned @ fc8eb31 (catalog
  byte-unchanged, all 48 fixtures stand; guard 8/8). ARCH-34's dependency gate is lifted — it
  stays v1.1 by scope choice alone. They also ported our ledger guard triad (their DOC-12) and
  joined the /inbox loop (VWB-26) — both repos now run the same discipline, same day it was asked.


- **2026-07-06 — DOC-12 filed into the bridge (uncommitted) — the guard triad goes cross-repo.**
  The user wants both projects on one ledger discipline, so the evening's three machine-enforced
  conventions (stranded completions, misfiled sections, ID ordering — voice QUAL-72/73/74) are
  filed for the bridge to port into ITS check_scope.py + CLAUDE.md, adapted to its own header and
  done-file formats, with the voice implementation as reference and canary-verification required
  at acceptance. Left uncommitted for the bridge maintainer's intake, per the usual rule.


- **2026-07-06 — QUAL-74 DONE (filed + completed same day) — the ledger sorts itself, third guard
  of the evening.** The user's third catch: no ID ordering inside sections. The audit showed it
  was never a rule — the done-archive grew in completion order (56 violations, most predating
  today) — so this one is a convention SET rather than restored: ascending by ID within each
  section, both files, completions inserted at their sorted position. Both files mechanically
  resorted with a zero-loss assertion; check_scope gains its third new tripwire in two hours.
  The trilogy (QUAL-72 stranded completions, QUAL-73 misfiled sections, QUAL-74 ordering) shares
  one moral: every ledger convention a hurried maintainer can break now breaks the gate instead.


- **2026-07-06 — QUAL-73 DONE (filed + completed same day) — the gate learns sections too.** The
  user's second catch of the evening: BUILD-13 filed under the ARCH section (in-place filing at a
  design task's completion) and, found by the audit it triggered, BUG-29 sitting at the tail of
  QUAL in the done file (insert-before-next-header lands in the PRECEDING section — a subtle
  off-by-one-section bug in the filing pattern itself). Both moved. check_scope now enforces
  ID-prefix == enclosing section across both ledger files, and CLAUDE.md says the rule out loud.
  Direct answer to the user's question «do we need to strengthen the rules?»: the rule existed
  implicitly and prose didn't help — the strengthening that works is the machine check; the
  CLAUDE.md sentence just makes the convention citable.


- **2026-07-06 — QUAL-72 DONE (filed + completed same day) — the scope gate learns to catch the
  maintainer.** The user spotted three completions (BUILD-12, ARCH-33, REL-3) marked [x] in the
  ACTIVE plan instead of moved to the done-archive — a plain single-task-ledger violation that
  check_scope.py silently accepted through multiple green runs (it counts [x] across both files,
  so a stranded entry read as "done" rather than as drift). Entries moved; the gate now fails on
  any `- [x] **ID**` in the active file, canary-verified. The uncomfortable truth worth recording:
  the drift guard existed precisely for contradictory status markers and did not treat the most
  literal contradiction — a completed task in the active file — as one.


- **2026-07-06 — ARCH-35 DONE (same-day design session) — the satellite without firmware.** The
  question «how do I test ARCH-25?» answered itself once the inventory was honest: the voice
  runner already composes every satellite-side piece, and eval-commons' WS provider already
  speaks the complete /ws/audio protocol against the WB7. So `irene-satellite` is thin glue with
  two real inventions (the reply-audio leg and the lifecycle) — plus the scope the user added
  that makes it strategic: it becomes the FIRST client of the fleet TLS plane, walking the
  CSR-approval dance and connecting mTLS-wss through nginx before any ESP32 exists, with a
  hermetic docker-nginx e2e so the security plane gets CI regression coverage. First-class
  product mode too: a Pi with a mic is a supported room node. ARCH-36 files the build; ARCH-25
  items (3)/(4) stop being unverifiable. The session closed with a user-requested audit of the
  Plane-B nginx implementation against its documentation: CONFORMANT on every major claim (two
  zones, EC-only, untrusted-CSR handling, double-guarded CA, GET-only mTLS statics, idempotent
  playbook) — four findings: a stale "Irene runs elsewhere" premise (it deploys ON the WB7 now;
  README corrected, vars at ARCH-25), an unconsumed X-Client-Cert-CN header (identity binding →
  ARCH-36 scope), and two one-liners fixed on the spot.


- **2026-07-06 — REL-3 DONE (bar the tag) — 15.0.0 confirmed, changelog written, config-ui pass
  green.** Version holds at 15.0.0 for the whole release (bump rides the next one, user), so the
  "version bump" was a no-op confirmation. CHANGELOG.md authored for the revival release; README
  linked. The config-ui manual functional pass — the one exit-criterion check no CI can do —
  PASSED against the live backend across every page, after it flushed out BUG-29 (the 6000/X11
  browser block). The `git tag v15.0.0` is deliberately held as the final release act: the
  artifact needs ARM boot validation (ARCH-25) and a clean scope gate first. With this, the
  software release gate is down to ONE task — ARCH-25, the WB7/WB8.5 hardware bring-up — plus the
  deferred v1.1 tail. Everything that can be done from a desk is done.


- **2026-07-06 — BUG-29 DONE — the config-ui never worked from a browser on the default port, and
  only a human clicking found it.** REL-3's manual functional pass did exactly its job: port 6000
  (the shipped default everywhere) is X11, hard-blocked by Chrome/Firefox as ERR_UNSAFE_PORT, so
  the config-ui — a first-class contract consumer — failed every request before it left the
  browser, in a 35k-request retry storm. curl never cared; no gate could have. Swept 6000→8080
  across configs, the model default, the UI's own default, docker, ops, and docs. Honest process
  note: I burned several turns on an IPv4/IPv6-localhost theory built on a false premise (the "no
  request reached the app" test was on the blocked port, so it proved nothing) before the user's
  DevTools screenshot showed the real error in three words. Ask for the browser's actual error
  first, next time.


- **2026-07-06 — BUG-28 DONE — the reporting system catches its first real bug, hours after
  going live.** The smoke test's "тестовый отчёт" turned out not to be a test at all: the cloud
  triage read the bundle's logs, spotted durable timers dying silently across restarts, opened a
  fix PR — and the `/inbox` review CONFIRMED both root causes by reading today's main, no bundle
  trust needed. The done-callback deleted persisted records on teardown-cancel (so durability
  only worked across SIGKILL, backwards from the design's own D-2 line), and the reconciler's
  finally-delete destroyed the very record a successful re-arm had just refreshed under the same
  key. The reviewer's initial skepticism (dev-session kills ≠ real restarts) died on the facts:
  SIGTERM teardown is exactly the production restart path. Fix merged as authored — the marker
  pattern mirrors BUG-19, anti-resurrection preserved, spurious shutdown failure-notifications
  gone, flagship double-restart regression added. Full circle: user speech → private ticket →
  triage → PR → owner review → merge, all in one afternoon, all on the rails built today.


- **2026-07-06 — ARCH-33 DONE — `/inbox`, and the workstream closes.** The owner's review loop:
  a skill that pulls the report queue from the reports repo (the source of truth, not this repo's
  PRs), then walks fix-PRs and escalations one at a time. Its spine is a deliberate distrust — the
  fix-PR path tells the reviewer to verify the finding independently and expect false positives,
  because the cloud triage reasons from a bundle it can't re-run and reports are often transients
  or dev-session artifacts (PR #1, opened by the smoke, is precisely that case — plausible bug or
  my own process kills, TBD at review). A CLAUDE.md invariant does the non-blocking session-start
  nudge. Verified against the live queue. With this, ARCH-30's design is fully built: the
  intent+capture (ARCH-31), the bundle+durable delivery (ARCH-32), the live triage repo (BUILD-12),
  and now the review loop — only ARCH-34 (bridge-evidence enrichment, deferred v1.1) remains of the
  whole idea. The release tail is back to REL-3 + ARCH-25.


- **2026-07-06 — ARCH-34 filed [deferred] (user loud-thinking) — bridge-evidence enrichment for
  smart-home reports.** When a report is filed and the request ring shows smart-home involvement,
  the voice collector pulls bridge-side evidence (dispatch ring, MQTT window, persisted-vs-live
  diff) from a bridge READ endpoint and folds it into the bundle. The discriminator already exists
  (ARCH-32's ring carries intent names), so the voice cost is small; the ask to the bridge is small
  and self-serving (its own UI wants the same collector-as-read-endpoint seam). Closes the gap the
  bridge design already names — a voice→bridge handover with no house access — automatically and at
  filing time, superseding their deferred manual CLI. v1.1: gated on the bridge exposing the endpoint;
  paired amendment dropped uncommitted into VWB-28.


- **2026-07-06 — BUILD-12 DONE — the reporting loop closed, live, and immediately did its job.**
  Bootstrapped `../wb-user-reports` (repo, labels, workflows, lens files, secrets, app install,
  PATs) and ran the real smoke: «сообщи о проблеме» through the web API produced a ticket + a
  committed bundle, and the triage workflow — one Claude, voice lens — analyzed it, labelled
  `fix-pr-open`, and OPENED a fix PR on wb-mqtt-voice. Every leg of device→ticket→triage→PR
  worked. The smoke earned its keep by flushing three CI-config gaps the authored workflow
  couldn't reveal without running (`id-token: write`, `GH_TOKEN`, and the decisive one:
  `--allowedTools`, whose absence silently denied all 26 of Claude's tool calls across two
  confusing green-but-inert runs). Loop safety proved itself too — the bot's own edits
  re-fired the workflow and were correctly skipped. The opened PR #1 claims a durable-action
  restart bug: plausible, touches the right files, but read from a bundle full of MY dev-session
  process kills — so it is a PROPOSAL for owner review, exactly what the design intends. That
  the bot can safely open a PR at all is the whole point of the leak-fence + human-review model.
  The workstream now needs only ARCH-33 (`/inbox`) to give that review its interactive home —
  PR #1 is its first customer.


- **2026-07-06 — BUILD-12 authored + ready (awaiting owner actions) — the reports repo in a
  box.** Everything `wb-user-reports` needs, authored as the SIBLING working copy
  `../wb-user-reports/` (git-initialized, content committed — the user corrected the first
  placement under `ops/`: repos in this constellation are siblings owning their own files;
  a mirror here would drift) and validated:
  the triage workflow (loop-safe, per-ticket concurrency, both codebases checked out, the
  D-11 model pinned in exactly one env var), the two lens process files (dedup-first, repro
  recipes, four outcomes, the §7.3 handover schema verbatim, ping-pong guard, replies drafted
  in the reporter's language), the 30-day retention pruner (stamp-parsed, logic unit-tested),
  and an idempotent `bootstrap.sh` that does repo+labels+push+checklist-issue in one run. A
  worthy note: the permission fence BLOCKED the agent from `gh repo create` on the owner's
  account — which is exactly where the design put the owner boundary anyway; the script now
  IS the owner's one-command step, followed by the app-install/secrets/PAT clicks no script
  can do. Completion criterion: the live smoke — «сообщи о проблеме» → ticket → triage run.


- **2026-07-06 — ARCH-32 DONE — the bundle, the sink, and a promise that survives reboots.**
  The delivery half of problem reporting: an always-on ring of request synopses (the diagnosis
  material trace persistence would carry if it were on — added as a deliberately DEFENSIVE tap
  after the coverage suite instantly proved that a diagnostics buffer can crash a pipeline),
  a bundle collector whose redaction strips every secret-shaped value while keeping household
  context (the repo is private — that's the design's whole point), the two-call GitHub client,
  and a service that spools to durable state BEFORE touching the network. The nicest part is
  the offline story: «отправлю, как только появится связь» is exactly the kind of promise the
  durable-actions invariant exists for, so it IS one — a durable `report_retry` action with a
  48-hour window, re-armed across restarts, completing in the reporter's language. User guide
  + diagram shipped; README Highlights gained the bullet (user) and lost a stale «planned» on
  smart-home. Suite 1327, device gate 48/48. BUILD-12 (repo bootstrap + owner checklist) is the
  remaining gap between this code and a real filed ticket.


- **2026-07-06 — ARCH-31 DONE — the problem-report dialog, and the capture that must not obey.**
  The heart of the build is a single inversion: for one turn, Irene deliberately does NOT
  understand you. Verbatim mode on the pending-clarification state makes the workflow consume
  the next utterance raw — no text processing, no NLU, no QUAL-44 arbitration — because a
  problem description («свет в спальне не включается») IS a confident smart-home command to the
  matcher, and executing it instead of recording it would be the feature disproving itself. The
  test suite pins exactly that. Expiry per D-5 (90 s, configurable) dies silently; cancel words
  end it politely; with `[reports]` disabled the intent answers «Отправка отчётов не настроена»
  at turn one and never arms. One discovery the smoke net caught: handlers register via
  pyproject ENTRY-POINTS, not by existing as files — the report handler booted only after the
  registration (+ a lesson relearned: bare `uv sync` strips extras AND the editable eval-commons;
  full-extras + `make setup` restore). All 8 configs updated (master + example + 6 docker:
  handler lists; [reports] section in master/example), config-ui type parity green. Suite 1318,
  device gate 48/48, donation gate 15/0/0. Next: ARCH-32 (bundle + delivery).

- **2026-07-06 — ARCH-30 DONE (same-day interactive design session) — problem reporting
  end-to-end, design AGREED.** «Сообщи о проблеме» → verbatim-captured description → support
  bundle → private ticket → GitHub-Claude triage → fix PRs / handovers / owner escalations.
  The session's pivotal finding: both code repos are PUBLIC, so the naive "file an issue in the
  voice repo" would publish the household's logs and rooms — the design landed on a private
  triage home (`wb-user-reports`, shared intake with the future bridge UI button) which then
  SIMPLIFIED the original two-Claude choreography into one Claude with two lens process files,
  handover by label flip on the same ticket. Alternatives weighed at the user's request (Google
  Drive / Yandex Disk / Jira) — all lose to "the ticket must be a GitHub issue for the Claude
  action to trigger at all". Other decisions: verbatim capture checked BEFORE QUAL-44 (a problem
  description must never execute as a command), bundle carries the last-10 turns + action records
  + a new always-on 5-trace ring (Q2 "is it the previous utterance?" — no, measurably), ARCH-27
  durable spool for offline, 30-day bundle retention, leak fence, replies pre-drafted in the
  reporter's language, `claude-fable-5` pinned for the whole triage run (D-11 — volume is
  household-scale; capability dominates on unattended code work). Implementation filed:
  ARCH-31/32/33 + BUILD-12 here, VWB-25 to the bridge (uncommitted).

- **2026-07-06 — BUG-26 + BUG-27 + QUAL-71 DONE (one live-testing session, three fixes).**
  The user's config-example session kept paying out. **BUG-26:** «расскажи о себе» belonged to
  system.about all along (the literal phrase is authored there) but lost to conversation.reference
  on an EXACT raw-score tie — the hand-authored boosts cancelled the QUAL-64 specificity edge to
  the fourth decimal (1.4256 == 1.4256) and the sort fell to donation load order. The matcher now
  tie-breaks on matched-pattern token count then intent name (never load order), and about's boost
  went 1.1 → 1.2; the self-introduction now answers offline. **BUG-27:** "12:54 PM" in a Russian
  reply — the ru donation's default_value "12hour" preempted the handler's own natural-language
  default; ru default → verbose, and explicit ru 12-hour speaks the day period in words («1:11
  дня»). **QUAL-71:** seven hardcoded Russian strings swept from handlers into templates (ru+en),
  with a new `_template_or` base helper for error paths so a template problem can never mask the
  original failure being reported. Suite 1307, device gate 48/48, pyright 0.

- **2026-07-06 — BUG-25 DONE (filed + completed same day) — the CLI was eating every other
  command, and had been since ARCH-15.** The user's first real multi-turn CLI session exposed
  it: «привет» answered, «расскажи о себе» vanished — the log shows the second utterance never
  reached NLU at all. Two consumers were racing `CLIInput`'s single queue: the runner's
  interactive loop and `InputManager._listen_to_source`, which fed an internal queue nothing
  drains — the dataflow review's P0-8 dead pipe, still alive and STEALING alternate commands
  (PR-5b had fixed the double reader but missed the double consumer). The dead pipe is deleted,
  not repaired: the manager owns source lifecycle only. Second symptom, same session: the reply
  printed OVER the already-drawn next prompt, so the terminal looked hung until the next Enter —
  fixed with `prompt_async` + `patch_stdout`, which also means a timer firing minutes later now
  prints above a live prompt instead of through it. Interactive multi-turn was simply never
  exercised before — every prior session was single-command. Two regression tests pin both
  halves; suite 1302.

- **2026-07-06 — QUAL-70 DONE (filed + completed same day, user) — a clean REPL.** The CLI's
  console was a log firehose with an `irene>` prompt drowning in it. Two sources silenced:
  the root console handler (interactive runners now log to file + trace only — `--debug`
  brings the console back on purpose) and the embedded background uvicorn (its own handlers
  bypass root logging entirely; now built with `log_config=None` so it propagates to the
  file like everything else). The foreground webapi server is untouched — docker logs
  depend on its console output. The CLI now shows exactly: banners, prompt, replies.

- **2026-07-06 — REL-2 DONE — the first-run story, written by a live stumble.** The morning's
  bare-`irene-cli` transcript became the acceptance test, and everything followed from it.
  `configs/config-example.toml`: a curated text-first starter — hybrid NLU only, zero downloads,
  zero keys, web API alongside, smart_home enabled with the bridge off (so the first device
  command earns the honest «умный дом не подключён» instead of a mystery) — and every disabled
  capability comments which config-master section to lift. The silent default-config fall-back is
  gone from the CLI/WebAPI runners (it could NEVER work — the built-in default has an empty NLU
  provider list): bare and `--headless` runs now stop with directions naming the example config,
  `IRENE_CONFIG_FILE`, and the QUICKSTART. README lost its stale "smart-home not yet built /
  not packaged" status (both false since ARCH-8 and BUILD-11) and gained the first-run one-liner;
  QUICKSTART finalized around example-first flow with console-script invocations. Verified live:
  example boots, «который час» answers, «включи свет» degrades honestly; suite 1300; config gate
  13/13; pyright 0. The exit-criterion checkbox for docs/quickstart flipped — REL-3 + ARCH-25 are
  all that remain.

- **2026-07-06 — DOC-8 DONE — the data-models map, shipped where it belongs.** The task predates
  the `docs/architecture/` family, so the deliverable moved there (user: user-facing naming, family
  prose, diagrams): `docs/architecture/data-models.md` + `docs/images/data-models.dot/png`. The
  page reframes the request-vs-session confusion as **three lifetimes** — dies with the request
  (RequestContext as routing+identity-never-memory, Intent deliberately session-blind, IntentResult
  with the failure-carries-reason contract, the audio primitives), lives with the session (a session
  is a ROOM; windowed single-writer history; pending clarification; ~30 min expiry; one minting
  path), survives restarts (the registry, physical identity — why a timer still knows its room).
  Facts verified against today's code rather than transcribed from the defect-era QUAL-25 snapshot
  it distills. Linked from README's architecture list; cross-linked from dataflow.md.

- **2026-07-06 — BUG-5 DONE (pulled forward from deferred — an EN tester is waiting) — donation
  EN enrichment, smart_home included.** The BUG-4-era gap held almost exactly (27 alias params,
  10 choice params). EN aliases added everywhere; EN choice surfaces ONLY for concept choices
  (language, timer units, quality, component) — identifier choices (provider/voice names) got
  nothing on purpose: canonicals self-match in EN. smart_home was structurally at parity but
  phrase-thin on 9 methods (menu-nav had 2 EN phrases vs 9 RU) — enriched. The valuable catch
  came from A/B probing the work instead of trusting it: "set a timer for ten minutes" had NO
  exact pattern (the phrases were article-blind) and won at HEAD on a 0.01 fuzzy margin that
  the new keywords tipped over to timer.cancel — fixed at the root with article-tolerant
  phrases (exact match 1.00), the same fix-T1-not-the-fallback lesson QUAL-64/Slice-3 taught.
  Probing also surfaced four PRE-EXISTING EN misroutes (cancel-the-timer, switch-asr-to,
  translate-hello, bare pause) — untouched here, recorded as seed evidence for the EN
  system-test discussion. Validator 0/0, suite 1299, RU device gate 48/48.

- **2026-07-06 — QUAL-69 DONE (filed + completed same day) — wardrobe «свет» alias consumed,
  re-pin @ `acc1e18b`.** The bridge's open-questions resolution gave `wardrobe_spots` the ru
  alias «свет» — a device now carries the group noun as a NAME. Analysis before consuming:
  the depth doctrine is ordering-protected (group-noun check precedes device resolution on
  every path, including the fresh Slice-3 legs), so voice behavior is unchanged — bare «свет»
  stays a room-group command and the bridge's `group_default` picks the spots. Re-pinned all
  three artifacts from bridge commit `aa031d2` (the openapi also carried a committed schema
  rename we hadn't synced since the VWB-19 era). Fixture F17 pins the alias-vs-doctrine
  interaction; device tier-1 gate **48/48**.

- **2026-07-06 — BUILD-11 DONE — the first real GHCR publish, and the images are honest.**
  Dispatch `28774806674` (all targets × all languages + config-ui): every job green on the
  first attempt — six backend images + the UI image are the repo's first artifacts ever on
  GHCR. The D-6 guards fired for real on each: `/app/assets` empty by digest, size within
  budget. **Real uncompressed sizes: armv7 248 MB, aarch64 718 MB, standalone 2.86 GB** —
  the torch-free armv7 diet earned its keep (the placeholder budget had 14× slack). Budgets
  tightened to 500 MB / 1.5 GB / 4 GB. `standalone-x86_64` boot-validated locally through
  the real `ops/docker-compose.yml` contract (override: standalone image + scratch assets
  root seeded per `update.sh`): health on :6000 in ~15 s, «который час» answered end-to-end,
  and first-boot downloads landed in the mounted volume exactly as designed (whisper
  `small.pt`, the microwakeword `irina` v2 pack from HF, silero_v4, spaCy cache). Zero
  defects — no BUGs filed. One observation parked for ARCH-25/REL-2: the RU image logs
  harmless `en_core_web_md not installed` ERRORs (en in the spaCy preference list; degrades
  cleanly to ru). Local test artifacts fully cleaned after (containers, images, scratch).

- **2026-07-06 — QUAL-35 Slice 3 DONE → QUAL-35 CLOSED (evidence-first, interactive) — the
  hard-phrasing tier measured, and the scoreboard rewrote the plan.** Authored the tier-2
  fixtures (F90–F98 measurable + F100–F102 relative adjustments) and ran the two-leg
  measurement: baseline vs the QUAL-50 LLM tier flipped into the derived SUT config (new
  `make device-auto TIER=… NLU=llm` knobs). Baseline 1/12; the LLM leg exposed the real
  blockers — none of them a new NLU tier. Built instead: group-noun routing for raw LLM
  entities («свет» arrives in `target`, not the CHOICE param — was «Не нашла устройство
  "свет"»), power-verb → playback fallback (the tape-deck class), a resolver utterance scan
  for pre-verbal device words («на кухне вытяжку включи» — stem-grade only, no re-pull on
  miss), and two donation pattern fixes for confidently-wrong T1 (greedy «кондиционер на» at
  conf 1.00 — no fallback tier can EVER rescue a confident misroute; «звук на» vs the fuzzy
  volume coin-flip). Colloquial verbs («вруби»/«глуши») deliberately NOT enumerated in
  donations — the LLM tier covers them (found ALREADY enabled in all 6 deployment configs;
  the "disabled in deployments" note was stale) and the smart-home guide now teaches the
  add-a-word donation recipe instead. spaCy T2 leg dropped on evidence → QUAL-53 addendum
  owns any revival; relative adjustments deferred → QUAL-68 (fixtures already red in the
  suite). **Tier-1 gate 47/47 (F94/F96/F97/F98 graduated in), tier-2 `NLU=llm` 5/8 (red =
  the deferred trio), suite 1299, pyright 0.** Guide updated (stale «ютуб» limitation
  removed — Slice 1 shipped it; new limits stated honestly).

- **2026-07-05 — QUAL-67 DONE (filed + completed same day) — donation validation is a CI/build
  gate, warnings-as-errors.** The natural payoff of QUAL-66: with the wiring warnings at zero,
  `irene-donation-validate` fails the build on ANY new one — dead params and undeclared routing
  methods can no longer accumulate as ambient noise. The gate validates every donation directory
  that ships (module-aware discovery; handler module names are inconsistent about the `_handler`
  suffix), not just what some config enables, and sits in backend-health beside the
  config/dependency/build-analyzer gates, so it fences every image publish. Proven both
  directions: 14 handlers / 86 contract methods green, and an injected canary param turns it red.


- **2026-07-05 — QUAL-66 DONE (filed + completed same day) — contract-wiring warnings 21 → 0.**
  The user asked what the boot-time "Contract wiring" warnings were; the answer became a sweep.
  Dead `language` globals dropped from 9 donations (request language lives on the context since
  QUAL-36) + conversation's `session_id`; voice_synthesis's unread `provider` param dropped
  (parsed from raw text); two internal helpers renamed off the `_handle_` routing prefix. The
  near-misses were the lesson: `system` and `speech_recognition` ALSO declare `language` — but
  theirs is the TARGET language for switching, genuinely read, and the validator had correctly
  stayed silent about them (an over-eager first sweep removed them; the warning list itself
  caught the error). One test had relied on the drift existing as its live example and now
  exercises the check synthetically. With zero ambient warnings the validator is a tripwire
  again. Suite 1289 green, device suite 43/43 intact, pyright 0.


- **2026-07-05 — QUAL-64 DONE (interactive) — device suite 43/43 (100%) for the first time.**
  Diagnosis: not a weighting preference but a TIE broken by accident — identical per-tier
  constants + stable sort = donation load-order routing, and the per-method `boost` (authored
  since QUAL-29, docstring promising "pattern strength multiplier") was never read by the pattern
  stage. User picked the specificity+boost score; with the RIGHT winner chosen, the coverage
  factor lifts confidence to 0.98–1.00 on the exhibits. F70's workaround retired («переключи
  субтитры» now wins on merit; fixture restored as regression). 15-case routing test pins
  exhibits + bread-and-butter over all 14 donations. The stale-mock pkill needed the `[e]`
  bracket trick — it was killing its own recipe shell. Suite 1329, pyright 0, 11/11 contracts.
  QUAL-35 Slice 3 is now unblocked on a tuned first tier.


- **2026-07-05 — QUAL-35 Slice 2a DONE — VWB-24 consumed same-day; device suite 41/43.** The bridge
  typed the HVAC params (v1.3): full ru/en/de triplets, and for the first time wire ≠ canonical
  ("COOL"/"cool") — the fixture guard now validates the CANONICAL set, which is what Irene sends
  (§5a). `_hvac_choice` matches the spoken word against the device's OWN triplets (labels +
  canonicals through the shared option matcher, transliteration hints included) with an
  ACTION-aware device pick — only the HVACs carry set_mode, so «кондиционер на охлаждение» never
  clarifies against a plain heater; set_fan's param is named `fan`, not `speed`. F80
  («охлаждение»→cool) and F81 («скорость 2»→speed_2) green live. One ops gotcha burned an hour:
  a STALE mock bridge from earlier debugging still owned the port and served the pre-VWB-24
  golden — empty mode values, while every in-process repro passed; `device-auto` now kills any
  squatter first. The only red anywhere remains F40/F42 — the parked QUAL-64 pair.


- **2026-07-05 — QUAL-35 Slice 2 COMPLETE (Part B, code pushed with the guide; ledger line landed
  one commit later) — device suite 39/41; the only red anywhere is the parked QUAL-64 pair.**
  Part B: tracks audio/subtitles (subtitles got its own verb «смени» — «переключи» scores as
  input_select in the untuned matcher, one more QUAL-64 exhibit), screen aspects as CHOICE+target
  (two screen-capable devices in the living room), menu navigation as a 7-way CHOICE, presence
  «мы дома»/«мы уходим», cleaning start + «уборка на 30 минут», and the water alarm — device found
  by its alarm+leaks capability PAIR (never an id literal), keeping the heating alarm out per the
  user decision. Adjudications settled: no further units abstraction needed (one catalog-range
  path serves dB/%/°C); declarative room_context enforcement closed as satisfied-by-implementation.
  Suite 1314 green, pyright 0, 11/11 contracts. **Immediately after: bridge accepted + implemented
  VWB-24 (typed HVAC set_mode/set_fan) — folded in as Slice 2a** (re-pin + CHOICE wiring +
  fixtures), starting now.


- **2026-07-05 — QUAL-35 Slice 2 Part A DONE (`bedc867`) — device suite 33/35; all eight new
  fixtures green on the first live run.** Wired per the interactive decisions: volume
  up/down/set/mute_toggle (the processor's dB range −96..0 honestly enforced by the shared catalog
  range pre-validation), playback play/stop/next/previous + a seek CHOICE (ff/rewind) with
  `play_pause` fallback for split-action-less devices (the Zappiti), cover.set_position in both
  address forms («наполовину»→50; the room form rides VWB-23 `params`), and the power-verb
  fallback — «включи обогрев» → climate.on, «включи вытяжку» → fan.set(2) — closing the census gap
  where climate/fan devices ignored on/off verbs. The routing-risk fixture (F62 «выключи звук на
  телеке» vs the power_off phrase) routed correctly. +10 donation methods; one extractor trap
  re-learned: target regexes must keep a SINGLE capture group. Part B
  (tracks/screen/menu-nav/presence/cleaning/water-alarm) follows; scope already in the ledger.


- **2026-07-05 — QUAL-35 Slice 2 scope decided (interactive, capability-by-capability from the
  pinned-golden census).** Eleven decisions: volume all-four; playback everything incl. ff/rewind
  (play_pause only as the fallback for split-action-less devices); cover.set_position in both
  address forms with «наполовину»→50; climate on/off via power-verb fallback (the census showed
  «включи обогрев» silently fails today); hood fan with «включи»→speed 2; tracks audio/subtitles +
  screen aspects + a menu nav subset (user overrode the skip-lean: track dialogs need navigation on
  some devices; pointer stays out); presence home/away; cleaning start+delay; water_supply alarm
  only. Skipped with intent: power.toggle, seasonal_mode, heating_control alarm — and ALL FOUR
  VALVES as a permanent voice fence. One contract gap found while checking facts: HVAC
  set_mode/set_fan params are bare strings (no triplets/options_from — the G5 disease again) →
  **bridge VWB-24 filed uncommitted**; «кондиционер на охлаждение» waits for the typing re-pin.
  Implementation follows in this session; scope recorded first so the decisions survive it.

- **2026-07-05 — QUAL-35 restructured (3 slices; the local-LLM T3 concept retired) + Slice 1 DONE —
  device suite 25/27; every red is now QUAL-64's.** Reconciliation first (user): most of QUAL-35's
  historical scope was already satisfied by today's arc — typed donations, the Q7b swap, D-15,
  `options_from`, the units requirement, and the "compound numerals need T2" theory (dead — it was
  BUG-23/24). The T3 bullet's "dependency-parse / local-LLM, opt-in local-only" framing predated
  QUAL-50 and is retired: the third cascade tier EXISTS (the donation-grounded LLM NLU provider
  through LLMPort — DeepSeek with an API key, abstains offline) but is not enabled in any deployment
  config; Slice 3 measures it instead of building anything new. The plan: Slice 1 transliteration,
  Slice 2 capability breadth (volume, playback rest, cover positions, HVAC mode, fan + two
  adjudications; menu/pointer and the global valve/mode specials held for explicit user decision),
  Slice 3 hard-phrasing fixtures measured against spaCy patterns + the enabled QUAL-50 tier (after
  the QUAL-64 matcher tune, so fallback tiers aren't built against an untuned first tier).
  **Slice 1 landed the same session:** `latin_to_cyrillic_hint` reuses the in-house TTS transcription
  engine — "YouTube" renders as «ютуб» *exactly* — plus an acronym letter-name table (TV→«ти ви»,
  where the engine would say «тэлевижен»); option matching and scenario-label scoring now also
  compare against the hint, with «э»→«е» folding. One iteration bump: the hint transcriber must
  carry the FULL PrepareNormalizer option shape (a partial dict KeyError'd on the mixed-script
  label «Кино с LD-проигрывателя» — caught live by the suite, of course). F41 + F53 green;
  F41/F42/F53 retiered to 1. Suite 1269 green, pyright 0, 11/11 contracts.

- **2026-07-05 — QUAL-44 DONE (+ BUG-23/BUG-24 found & fixed under it) — device suite 23/27; every
  remaining red is deliberate.** The arbitration landed exactly as the entry scoped it: on a
  clarifying turn the pipeline now runs NLU on the BARE new utterance first — a confident,
  non-fallback recognition is a fresh command (pending dropped, logged, processed clean); fragments
  and low-confidence turns combine as before. One extra NLU pass, clarifying turns only; abandonment
  is silent. The regression fakes became text-aware — an everything-recognizes-at-0.9 fake would have
  defeated the arbitration invisibly. Chasing the residual F51 red through the live stack
  (`spoken: "hdmiодин"` in the new clarification metadata) unearthed two real input-corruption bugs:
  **BUG-23** — the `numbers` normalizer (digits→words, the SYNTHESIS direction) ran on `asr_output`,
  fighting BUG-1's pre-NLU words→digits and garbling «hdmi1»/«25» (the true cause of F06's range
  error, previously misread as a T2 compound-numeral limit); now `tts_input`-only in defaults +
  config-master + explicit normalizer blocks in all 6 docker configs (user request). **BUG-24** —
  ovos maps standalone «пол» to 0.5, so «тёплый пол» lost its device noun; now sentinel-guarded
  unless a measure word follows («пол часа» still converts). A user question caught a third latent
  one en route: the `-en` configs inherited `latin_to_cyrillic: true` — an English deployment would
  transliterate its whole TTS input; the `-en` blocks now pin `latin_to_cyrillic = false` +
  `language = "en"`. **Result: `make device-auto` 23/27** — F05/F06/F07 retiered to 1 in the fixtures
  (eval-commons `3b959e0`; the "T2 compound numerals" theory is dead, it was pipeline corruption);
  the 4 red are exactly F40/F42 (QUAL-64 matcher tune, user-parked) and F41/F53 (genuine T2
  transliteration). Suite 1266 green, pyright 0, 11/11 contracts.

- **2026-07-05 — QUAL-65 DONE — input switching + app launch by voice (bridge VWB-19 consumed);
  the options_from dance built; QUAL-44 un-deferred by what the suite caught.** Re-pinned @ bridge
  `3bed556` / catalog `dbfd2855` (select-form canonical routing, `canonical_first.md` §11): by_value
  inputs (mf_amplifier, upscaler) carry static value triplets with `labels: null` — technical
  identifiers, wire=canonical=table key — so the ru-labels pin guard learned the distinction (null
  legal, non-null still requires ru); parametric inputs + apps carry `options_from`. The QUAL-35
  resolver-note-(1) machinery arrived ahead of schedule: `read_options(device_id, kind)` on the read
  port, 30s TTL cache in CatalogService, fail-soft `BridgeClient.get_device_options`. Two handler
  methods share one option matcher built on the resolver's own normalization; an unmatched value
  clarifies by reading back what IS available. Four new fixtures (F50–F53) + mock-bridge options
  endpoint; the input-switching exclusion is lifted from fixtures, QUAL-35 note (3), and the user
  guide. **Live: F50 green end-to-end** («переключи усилитель на cd» — validated offline, zero
  round-trips); 20/27. **F51–F53's red turned out to be gold:** not routing at all (the matcher probe
  routes all three correctly, 0.75–0.79) but **QUAL-44 in the flesh** — F20's legitimately-armed
  clarification consumed the next same-room case as its "answer" («поставь на паузу переключи телек
  на hdmi1»), re-armed, and poisoned the cascade; the same bleed retroactively explains part of
  F42's earlier behavior. User decision: QUAL-44 un-deferred and implemented next; the device suite
  runs `-j 1` from now on (shared per-room sessions make parallel cases one interleaved
  conversation, not independent tests). Suite 1262 green, pyright 0, 11/11 contracts,
  eval-commons 40 (`cc1cba9`).

- **2026-07-05 — ARCH-8 PR-5 DONE → ARCH-8 CLOSES — the whole MQTT smart-home arc landed in one day;
  device suite 19/23.** The sensor-read flow: `read_state(device_id)` joined `DeviceCatalogPort` as a
  QUERY (reads never ride the OutputManager, §13.3), `CatalogService` carries a wired state-reader,
  `BridgeClient.get_device_state` GETs `/devices/{id}/state` fail-soft, and the handler's
  `_handle_read_state` (donation: quantity CHOICE temperature/humidity with RU surfaces, room via
  D-15) picks the reading source with two deliberate preferences the tests pin: a dedicated `sensor`
  capability beats a climate unit, and on climate devices the MEASURED `room_temperature` is read —
  the bare `temperature` field there is the thermostat SETPOINT («уставка» per the catalog's own
  labels), a silent wrong-value trap. Live: F30–F32 went green (`make device-auto` → **19/23**; the
  4 red are all owned: F40/F42 → QUAL-64, F41/F06 → QUAL-35 T2). Suite 1255 green, pyright 0, 11/11
  contracts. **The deferred user-facing promise is delivered with ARCH-8's completion:**
  `docs/guides/smart-home.md` — how voice control works (catalog-driven vocabulary, depth of
  phrasing, clarifications, sensor questions), how to enable `[outputs.bridge]`, current limits —
  linked from the README. Remaining in the MQTT lane: QUAL-35 T2/units + breadth (evidence now
  flowing from the suite), QUAL-64 matcher tune, then the hardware tiers (ARCH-25).

- **2026-07-05 — TEST-18 DONE (Slice B) — the producer contract suite is EXECUTABLE; first scoreboard
  16/23.** The capture side landed as a **mock bridge** (eval-commons `1bc7b03`), refining §14.3's
  in-process capture into something strictly more end-to-end: `eval_commons/mock_bridge.py` serves the
  PINNED golden catalog at `/system/catalog` and records every canonical POST fixture-shaped — so a run
  exercises the real BridgeClient wire serialization AND the real startup catalog pull, not just the
  handler. `device_command_provider` drives `/execute/command`; `device_command_assert` compares
  against the fixture `expect`; `fixtures_to_tests` GENERATES the promptfoo cases so the pinned
  fixtures stay the single source of truth. Voice side: `eval/device.promptfooconfig.yaml`,
  `make device / device-auto` (the auto target derives the SUT config from config-master because
  pydantic-settings init kwargs beat env for nested sections), target-profile URLs, eval README.
  **Scoreboard: 16/23** — every tier-1 actuation + clarify fixture green end-to-end (device forms,
  all six VWB-23 room-group forms incl. scope auto/all and room aliases, both clarifications). The
  7 red, each owned: F30–F32 reads → ARCH-8 PR-5; F41 transliteration + F06 compound numeral
  («двадцать пять» mis-extracted; «двадцать два» fine) → QUAL-35 T2's first suite-collected evidence;
  F40/F42 scenario routing → **QUAL-64** (filed): the keyword matcher — never tuned — scores short
  verb phrases over longer specific ones («выключи кино» → power_off despite scenario_stop carrying
  that exact phrase at boost 1.3), then dips under the 0.7 threshold live → LLM fallback. User
  decision: leave them red, tune the matcher deliberately (a drafted handler-level scenario fallback
  was reverted in favor of that). En route, **BUG-22** found + fixed: `/execute/command`'s room_alias
  validation NEVER worked — web_server built a web-templates-only asset loader, so localization
  consumers saw empty data; it now reuses the intent system's fully-loaded loader, and the rooms
  localization gained the house's rooms. TEST-18 moved active → done; next: ARCH-8 PR-5 (the reads
  go green).

- **2026-07-05 — ARCH-8 PR-4 DONE (+ QUAL-35 T1 donations & clarify policy) — «включи свет в
  детской» now travels the whole pipeline: NLU → resolver → handler → canonical command → spoken
  outcome.** The reference smart-home handler (`smart_home.py`, 9 donation-routed methods) closes
  the vertical slice. The T1 donation is the first with non-generic `entity_type` declarations
  (target=device, room=room) — the PR-3 Q7b swap now runs its declarative path in production. The
  noun lexicon landed as donation data, not code: the `group_noun` CHOICE param's canonical values
  ARE the catalog's semantic group names (light/cover) with the RU surfaces
  (свет/шторы/жалюзи/занавески) as choice_surfaces — bound to catalog truth at execution (the
  handler refuses a room-group command for a room with no such group members), guarded by a
  word-boundary check so a device NAMED «Подсветка потолка» never false-triggers the light group.
  «весь/все» flips `scope: auto → all`. Delivery goes through a new Any-typed domain port
  (`DeviceCommandDeliveryPort` — pure per the import contract) implemented by
  `DeviceCommandDispatcher` over the OutputManager with a 7-second bound; a timeout, a missing
  bridge, or a missing catalog each get their own honest spoken degradation. The §5b error enum
  maps to feminine-ru templates; `param_invalid`, same-room ambiguity (F20/F21 — the v1 clarify
  decision), out-of-range setpoints (pre-validated against the pinned catalog's min/max — most
  param_invalid never round-trips) and missing slots all arm the QUAL-30/31 one-shot
  clarification; a partial room-group aggregate names its failed members («…, но не ответили:
  Бра»). 22 fixture-mirroring tests drive the REAL resolver → handler → OutputManager → capturing
  bridge and assert byte-equal fixture `expect` shapes; a live webapi run confirmed the real NLU
  cascade routes «включи свет в детской»/«включи телек» to `smart_home.power_on` while greetings
  and timers stay untouched. Suite 1250 green, pyright 0, 11/11 contracts. Handler enabled in
  config-master + all 6 docker configs (domain priority 80). TEST-18's tier-1 fixtures are now
  green-able — Slice B makes them executable. Two side-fixes: the smoke-e2e 500 was a stale
  editable-install entry-point map (uv sync refreshes it), and the recurring dev-venv trap's root
  cause fell out — the untracked `.python-version` pinned the broken /usr/local 3.11.4; it now
  pins the uv-managed 3.11.12 (memory updated). Next: PR-5 (sensor read) closes ARCH-8.

- **2026-07-05 — ARCH-8 PR-3 DONE (with the QUAL-35 resolver half) — spoken references now resolve
  against the real device catalog.** Three moves in `entity_resolver.py`. **The Q7b atomic swap
  (QUAL-35 b):** dispatch is declarative-first — a donation-declared `entity_type` routes the param
  straight to the device/room resolver (map built from the loaded donations); the old
  `_is_device_entity`/`_is_location_entity` name-heuristics remain only as the fallback for
  generic/undeclared params, so every existing handler behaves identically until PR-4's smart-home
  donations declare real types. **Catalog-backed device resolution:** name+alias surfaces per locale,
  exact then RU-morphology-tolerant (a shared-stem heuristic — ≥4-char stem with ≤3-char endings —
  because plain fuzz.ratio scores «детской»/«детская» at 71, under any sane threshold), room-context
  disambiguation for shared aliases, name-level ambiguity surfaced as candidates for the clarify path
  («ночники» → both sconces, per the v1 decision), and the ARCH-26 lazy re-pull exactly once on a
  miss. **Room resolution + D-15:** catalog rooms by name/alias/id, then the ARCH-22 coverage policy —
  a mentioned room the client covers is the target, a real room it does not cover returns
  `uncovered_room` (spoken error, no actuation), and `global` is exempt so whole-house asks
  («выключи весь свет в квартире») work from any satellite; `resolve_default_room` implements
  rule 3 (no room → primary). The legacy client-context paths survive untouched for catalog-less
  deployments. Wiring rides `nlu_component` → `core.catalog_service`. 14 new tests; live
  spot-checks against the real pinned golden: 12/12, including the resolution leg of every
  device-form crossover fixture (телек/эппл/радиаторах/пол/розетки/тюль слева + room aliases
  зал/квартире/сынарник). Suite 1228 passed, pyright 0, 11/11 contracts. QUAL-35 keeps (a) T1
  donations and the handler-side room_context policy for PR-4, and the heavy tiers for after the
  suite runs. Next: PR-4 — the reference device handler end-to-end.

- **2026-07-05 — PR-2 placement amendment (user decision): one home for all OutputPorts + explicit
  bridge surface in the 6 deployment configs.** `BridgeClient` moved
  `providers/outputs/bridge.py` → `outputs/bridge.py`; the `irene.providers.outputs` entry-point
  group is retired (nothing discovered outputs via entry-points — the composition imports and
  registers directly from `[outputs.bridge]` config) and its ARCH-4 independence entry removed;
  `mqtt_integration.md` §4/§8/§10/§13.1 amended with dated notes so the design doc matches reality.
  The 6 docker-image configs (standalone-x86_64, embedded-aarch64, embedded-armv7 × ru/en) — which
  carried no `[outputs]` section at all (silent defaults) — now declare `[outputs]` +
  `[outputs.bridge]` explicitly (disabled; the flip-on belongs to the ARCH-25 hardware bring-up
  once the bridge's ops cutover lands); all 6 validate against `CoreConfig`. Suite 1214 green,
  11/11 contracts, pyright 0.

- **2026-07-05 — ARCH-8 PR-2 DONE — the real bridge adapter; Irene can now (config-gated) speak REST to
  wb-mqtt-bridge and pull the device catalog.** `BridgeClient` (`providers/outputs/bridge.py`, the only
  module that knows the bridge exists) implements the designated DEVICE_COMMAND OutputPort: device-form
  commands POST to `/devices/{id}/canonical`, room-group commands to `/rooms/{room_id}/canonical`
  (VWB-23), responses map to the rich DeliveryResult — post-action `state` / per-member `results` as
  the echo, the §5b error enum as `error_code` with `param_invalid`'s field+reason preserved for the
  clarify path, and a bridge that is down becomes a spoken `bridge_unreachable`, never an exception in
  the pipeline. Its `parse_catalog` builds the domain `DeviceCatalog` and was verified against the real
  pinned golden (79 devices / 11 rooms @ `91909b54`; children_room light default, global→all_lights
  membership, °C/% typed params, scenario ru labels, `options_from`, «зал»/«радиаторы» aliases all
  survive the round-trip). Wiring: new `[outputs.bridge]` config section (enabled/base_url/timeout;
  documented in config-master, config-ui `OutputConfig`/`BridgeOutputConfig` types co-changed — the
  section editor renders nested objects generically; `npm run check` + `build` clean),
  `CatalogService` now built by `build_core` and carried on the engine, and a runner-agnostic
  `setup_bridge_output()` hook in the composition (called by the base runner after `core.start()`)
  registers + designates the output, wires the catalog fetcher, and attempts one non-fatal startup
  pull — the ARCH-26 lazy refresh covers a bridge that boots later. Placement decision recorded (user
  question): BridgeClient sits under the `irene.providers.outputs` entry-point group per §13.1 —
  an external-system adapter (configured, designated), not a channel sink like `irene/outputs/`;
  the category joined the ARCH-4 independence contract. One test-harness fix along the way:
  the master-config completeness test's section-rename mutation now renames `[outputs.*]` sub-tables
  too (a surviving `[outputs.bridge]` implicitly recreates the parent — TOML super-table semantics).
  13 new tests; suite 1214 passed, pyright 0 errors, 11/11 import contracts, config-ui clean.
  Smart-home user-guide prose deliberately waits for PR-4/PR-5. Next: PR-3 — catalog into the
  resolver.

- **2026-07-05 — ARCH-8 PR-1 DONE — the canonical-command boundary exists in code; the MQTT arc's spine
  starts.** Adapter-free by design, built the same day as the fixtures it must eventually satisfy.
  Domain (`irene/intents/`): `device_commands.py` — `DeviceCommand` (device form; scenarios ride it) and
  `RoomGroupCommand` + `GroupScope` (VWB-23 room form), each with the fixture-shaped `to_dict()` (kinds
  `actuate`/`room-group`, matching `crossover_fixtures.json` vocabulary) and the wire-shaped
  `request_body()`; commands travel in `IntentResult.metadata["device_command"]` per §13.2.
  `device_catalog.py` — the typed catalog model mirroring the pinned contract (params
  values-XOR-`options_from` with units/ranges, capability `group` tags, room `group_defaults`, and the
  `group_members`/`group_default` queries the resolver will use). `DeviceCatalogPort` joined
  `intents/ports.py` (QUAL-24 pattern) carrying the ARCH-26 lazy-refresh seam as `async refresh()`.
  Application: `core/catalog_service.py` holds the snapshot, serializes concurrent refreshes, and never
  discards the last good catalog on a failed pull; PR-2 wires its fetcher. Delivery:
  `outputs/device_command.py` — `CapturingDeviceCommandOutput`, the fake bridge that IS the TEST-18
  capture point (records both address forms, returns the rich echo `DeliveryResult`, scriptable §5b
  error responder). No `ActuationPort` — the bridge is an OutputPort (§13.6). 15 new unit tests incl.
  end-to-end designated routing through the OutputManager; suite 1201 passed, pyright 0 errors.
  Follow-up hardening (user question, same session): a new import-linter contract — "Domain ports and
  boundary types stay pure" — pins `intents/{ports,models,device_commands,device_catalog}` against
  `irene.core`, closing a gap ARCH-1 cannot cover (intents as a whole carries sanctioned core edges:
  donations, trace, the durable seam — so only a module-scoped rule can forbid the port→application
  inversion, same shape as the SCC-2 input-port contract); 11/11 contracts kept.
  TEST-18 Slice B ungated. Next: PR-2 (BridgeClient adapter + catalog pull).

- **2026-07-05 — TEST-18 Slice A DONE — the crossover fixture set exists; the MQTT arc now builds against
  a failing suite.** Resumed the paused interactive session; the three open decisions closed (user):
  light-subset pair nouns («ночники»/«тумбочки»/«полки») dropped from v1 — bridge-side compound devices
  will come later and re-enter via a re-pin; same-room capability ambiguity clarifies in v1 with priority
  rules filed as QUAL-63 for a later release; sensor reads included. Authored
  `eval-commons/contracts/crossover_fixtures.json` (`941e245`): 23 `{utterance → canonical command}`
  fixtures against pinned catalog `91909b54` spanning all four expect kinds — device-form actuation via
  aliases and typed °C/% params, VWB-23 room-group commands (scope `auto` vs «весь»→`all`, room aliases
  «зал»/«квартира»), reads (with `any_of` for the two physically-equivalent bedroom temperature sources),
  clarifications (F20 playback, F21 climate), plus the scenario enum by RU label and a transliteration
  case. Each fixture carries a tier (1 = green-able with the QUAL-35 T1 donation baseline at ARCH-8 PR-4;
  2 = needs T2 units/transliteration). A new 8-test guard suite (`test_crossover_fixtures.py`) binds every
  fixture to catalog truth — device ids, actions, param ranges, enum wires, groups, sensor fields — and
  pins the fixtures' `catalog_version` to `PIN.json`, so the next re-pin points at exactly which fixtures
  go stale; 16/16 green with the pin guards. The bridge's VWB-16 consumer half can consume the file as-is.
  Next per the recorded sequence: ARCH-8 PR-1.

- **2026-07-05 — VWB-23 analyzed + contract RE-PINNED — «включи свет» became one REST call; the boundary
  is now address-form polymorphic.** The bridge shipped room-scoped group addressing (`canonical_first.md`
  §10, surfaced by this side's TEST-18 Slice A question "what does «включи свет в детской» resolve to?"):
  `POST /rooms/{room_id}/canonical {group, action, scope: auto|all|one}` — the depth doctrine (resolve only
  as deep as the utterance specifies; the device pick is bridge POLICY via `group_defaults`, not resolver
  heuristics), a `group` overlay on capabilities (37 illumination `power` caps tagged `light`; oven/plugs
  split to `power_switch` so «свет» can never reach them), all 10 rooms defaulting `light` → `<room>_spots`,
  fan-out allow-listed to `light`+`cover`, per-member aggregate responses. Verified against the committed
  artifacts and **re-pinned** into eval-commons (`e0d6b45`, catalog `91909b54`, all 8 pin guards green —
  the guard suite did its job on its first real re-pin). Ledger adjusted: ARCH-8 gained the
  three-address-form addendum (PR-1 models device + room-group commands; PR-4 noun lexicon bound to catalog
  `group` truth + singular/«весь»→scope mapping + aggregate-response speech); QUAL-35 gained the depth
  doctrine + the no-power-fan-out fence; TEST-18 Slice A: **Q1 (room lights) RESOLVED by VWB-23**, Q2
  narrowed to light-subset pairs only («ночники»/«тумбочки» — cover pairs dissolved into room-group
  fan-out), Q3/Q4 still open, fixture schema gains the `room-group` expect kind. Slice A stays paused on
  the three remaining user decisions.

- **2026-07-05 — TEST-17 DONE — the contract is pinned; both repos now test against the same committed
  boundary.** The bridge's v1.1 artifacts (bridge `59f4f46`, catalog `7a1149c7`) copied byte-identical into
  `eval-commons/contracts/` with a voice-side `PIN.json` and a consumer README (bridge generates, voice
  re-pins, both suites read this copy — no cross-repo writes, §14 publish boundary). The pin is load-bearing,
  not decorative: 8 new eval-commons tests validate the golden against the pinned `CatalogResponse` schema
  itself (the two halves of the pin cannot disagree), check STAMP↔PIN↔golden version agreement, and assert
  the v1.1 shape guarantees (authored aliases, ru enum labels, °C/% units, `values`-XOR-`options_from`, no
  empty capability husks) — so accidentally re-pinning a pre-patch artifact fails in seconds. Deliberately
  sequenced pin-after-patch: the first pin is the only pin. Carve-outs recorded in the ledger entry: the
  real WB7 dump rides the bridge's controller cutover; the crossover fixtures co-develop with ARCH-8
  PR-1/TEST-18. The MQTT arc's opening move is done — ARCH-8 PR-1 is next.

- **2026-07-05 — The bridge contract is voice-ready; ARCH-8's gate is met and the conclusions are in the
  ledger.** Closes the loop opened 2026-07-04, when the user asked how smart-home intents get their donations
  before starting ARCH-8. The analysis of the freshly committed bridge `contracts/` established the story —
  **donations are NEVER generated from the contract**: donations carry the static device-agnostic grammar
  (verbs, typed slots), the catalog supplies the entity/value vocabulary at runtime (lazy, ARCH-26), the
  resolver marries them — and found five gaps (schema-less `CatalogAction.params`, no aliases, EN-only enum
  labels, no units on params, enum-in-disguise `apps.launch`). Filed bridge-side; intake verified 4 of 5 and
  **refuted the G5 remedy** (the app set is runtime-dynamic — a static enum in the golden would drift on
  every app install, the exact disease QUAL-18 diagnosed; corrected to an `options_from` hint +
  `GET /devices/{id}/options/<kind>`, which adds a clean THIRD vocabulary tier: fully-dynamic per-device
  sets). Bridge landed **VWB-20 contract patch v1.1** (typed `CatalogParam` with unit/values/options_from,
  ru+en enum labels, aliases schema, husks suppressed) **and VWB-21** (household alias vocabulary: 34
  devices + 3 rooms) — all six items verified against the committed artifacts (catalog `7a1149c7`, bridge
  `59f4f46`). Ledger annotated so the conclusions survive this chat: ARCH-8 gate flipped to MET with the
  PR-2/PR-3 build notes; QUAL-35 gained the resolver-design notes (options_from as a second CHOICE source
  with lazy-miss + short-TTL cache; Cyrillic↔Latin transliteration-tolerant matching for device-reported
  proper nouns — «ютуб» vs "YouTube"; v1 command set excludes input switching until bridge VWB-19);
  TEST-17 un-deferred → `[release]` P2 with the pin target recorded. Next: TEST-17 pin → ARCH-8 PR-1.

- **2026-07-04 — QUAL-18 DONE (re-scoped) — the AsyncAPI subsystem is retired; the WebSocket protocols
  finally have accurate documentation.** The user asked for a deep dig before implementation, and the dig
  changed everything: the live `/asyncapi.json` emitted **zero channels** (verified against a running
  server) — all four documented endpoints had been deleted by ARCH-21/ARCH-10 while the four real ones
  (`/ws/audio`, `/ws/audio/reply`, `/ws/observe`, `/ws/output`) were never in the spec. ~1,400 LOC of
  bespoke generator+renderer were rendering an empty page, and the "code-first docs can't drift" premise
  had self-refuted (decorators document claims, not what `send_json` does). The 2026 ecosystem check found
  the renderer side solved (`@asyncapi/react-component` v3.1.3, offline-vendorable) but still no maintained
  FastAPI-WS→AsyncAPI introspector (fastws dead since 2023; FastStream still broker-shaped). Presented
  spec-as-artifact / code-first-rebuild / retire; **user chose retire + a user-facing guide.** Deleted
  ~2,000 LOC (generator, renderer, `irene/web_api/`, 7 dead WS message models, the interface method, 4
  routes, contract refs); wrote `docs/guides/websocket-api.md` — all four protocols frame-by-frame, the
  QUAL-55 canonical response frame, the reply channel's `speak_begin/PCM/speak_end` brackets,
  missed-announcement redelivery, a runnable Python example — plus a house-style diagram
  (`ws-protocols.dot/png`) and links from dataflow/esp32/howto-new-test. The web index page was also lying
  (linked `/asyncapi` and listed the deleted `/asr/stream|binary`) — repointed. Verified live: `/asyncapi*`
  404, index shows the guide pointer. Suite 1180 + smoke + 10 contracts green.

- **2026-07-04 — QUAL-55 DONE — the five execution surfaces speak one result shape.** The review's root
  cause (`api_result_contract_review.md`: no shared serializer, five hand-built dicts drifting apart) is
  closed with `irene/api/serializers.py::serialize_intent_result` — canonical
  `text`/`success`/`error`/`confidence`/`intent_name`/`timestamp`/`metadata`, with `intent_name` lifted from
  the orchestrator's `original_intent` and endpoint extras merged INTO the raw metadata rather than replacing
  it. REST `/execute/*` renamed `response`→`text` (the planned breaking change; `CommandResponse` reshaped),
  `/trace/*` `final_result` and both WS `response` frames now emit the same payload (superseding QUAL-54's
  metadata-injection stopgap). The "executed successfully" invented-prose fallbacks died with it (fail-loud).
  Cross-repo co-changes: config-ui types regenerated from the re-dumped OpenAPI (check+build green; no
  runtime consumer of the old field existed), eval-commons `ws_audio_provider` reads top-level `intent_name`
  with a metadata fallback so it spans SUT versions. The WS test fakes were replaced with the real
  `IntentResult` — hand-rolled fakes lacking `error` broke immediately, re-proving the review's F5 lesson
  that wrong-shaped fakes hide live bugs. Suite 1180 + smoke (live server asserts the canonical keys) +
  hexagon gate green.

- **2026-07-04 — REL-1 DONE — the Definition of Release is signed off; the road to release is now a closed,
  explicit list.** Interactive session. The checklist was reconciled criterion-by-criterion against current
  reality first: 6 of 8 exit criteria are already met with evidence (clean `uv sync` + CLI/WebAPI boots via the
  hermetic smoke suite; CI green since BUILD-9; pyright standard mode at 0 errors with an empty suppression
  list; 10 import-linter contracts; the test nets green; live model URLs re-verified this week by ASSET-4/5).
  The reconciliation surfaced one real gap: **no publish dispatch has ever run — no Docker image has ever been
  built for real**, so the Docker-boot clause was unproven → filed **BUILD-11** (first GHCR publish + boot
  validation + replace placeholder size budgets with real-size-derived ones). User decisions: the release
  artifact is a tag + published GHCR images (RU backends + config-ui); QUAL-18 and DOC-8 both STAY in release
  scope (all previously untagged tasks now carry explicit tags — the implicit-default ambiguity is gone);
  the vague "coverage understood" criterion replaced by the three named nets (unit + smoke e2e + eval CLI), no
  coverage-%; the target is the "scope-complete" milestone, not a calendar date. Remaining to release, in
  full: ARCH-8 (5 PRs) + QUAL-35 + QUAL-55 + QUAL-18 + DOC-8 (code/docs), ARCH-25 (hardware validation),
  BUILD-11 + REL-2 + REL-3 (release mechanics).

- **2026-07-04 — ARCH-29 + ASSET-5 DONE — «Ирина» lives in the server: wake-word model acquisition designed
  (interactive) and implemented; the training factory's first handoff consumed.** The user announced the first
  validated RU microWakeWord model (HF `droman42/microwakeword-irina-ru`, trained in
  `~/development/wakeword-training`) and asked for the model-sourcing architecture discussion. Design
  (`docs/design/wakeword_models.md`): a wake-word model is a v2 two-file pack (manifest + sibling `.tflite`);
  resolution is a 4-rung chain — local manifest path (pre-release testing) → wheel built-ins (the 4 stock EN
  packs ship inside pymicro-wakeword byte-identical to the esphome v2 repo, so «Alexa» as «Ирина»'s EN
  counterpart costs zero downloads) → v2 manifest URL (the escape hatch for microwakeword.com and
  not-yet-released HF models, per the user's "what if I train more?" question) → the released catalog on the
  provider class (piper-voices pattern; one line per validated word). Trigger layer stays semantics-free —
  word→room mapping waits for multi-room (ARCH-22/QUAL-35). Implementation: AssetManager multi-file packs
  (`files:` entries, staging + atomic rename) + `download_model_files()`; the provider's broken QUAL-20
  asset stub replaced by the real chain; both standalone configs switched to microwakeword («Ирина» RU /
  Alexa EN, per user request); voice-trigger guide rewritten; roster fixed everywhere («Борис» dropped — 2
  syllables; next: «Валера», «Наташа»; diagram regenerated). Live verification through the real provider:
  pack fetched from HF via the AssetManager, silence stays negative, and **16/16 synthetic + 6/6 real
  household «Ирина» recordings detect at the manifest's 0.97 cutoff** — an initial 0/16 scare was the harness
  truncating clips at the word's last sample (the sliding window needs trailing audio; a live mic always
  provides it). Suite 1173 green; both config validators green; smoke e2e green.

- **2026-07-04 — ASSET-4 DONE — silero VAD model download re-homed into the AssetManager; VAD warmup moved
  off the audio hot path.** A user-requested deep review of the VAD code ("where does the microVAD model come
  from?") answered the question two ways: **microVAD's model is compiled into the `pymicro-vad` wheel**
  (`micro_vad_cpp.abi3.so` — nothing to download, correctly outside asset management), but **silero VAD was
  self-downloading** — a synchronous, timeout-less `urllib.urlretrieve` fired on the *first audio frame*,
  blocking the event loop, retrying every frame when offline, and able to strand a truncated model file that
  its `size > 0` guard would trust forever. Root cause of the bypass: the AssetManager had no identity for the
  VAD family (`silero` is claimed by silero TTS in `provider_namespace_map`). Fixed by introducing the
  `silero_vad` asset name via a `(namespace, entry-point)` tuple mapping, declaring the model URL on
  `SileroVADProvider`, downloading in the provider's async `_do_initialize` through
  `download_model(..., url_override=)` (TOML `model_url` override kept), and adding a
  `VoiceSegmenter.initialize()` warmup seam that falls back to `energy` when the configured provider can't
  come up — so a fresh offline install degrades to working energy VAD instead of going silently deaf. On-disk
  path unchanged (`models/vad/silero_vad.onnx` — deployed volumes unaffected). Dead
  `create_audio_processor`/`process_audio_with_vad` deleted; stale VADEngine/vad_silero docstrings and
  `docs/guides/vad.md` updated. Suite 1162 green + `test_vad_assets.py` (10 new); verified live both ways
  (real download through the AssetManager; dead URL → energy fallback with the reason logged).

