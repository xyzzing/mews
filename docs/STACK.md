# The flight-test program: complete stack overview

Version: 2026-11-09. The 2026-10-31 post-landing map, plus the RSI loop
(docs/RSI.md, PRD amendment 2026-11-09). Audience: a researcher or agent
with no prior session context. Everything here is verifiable in the six
repositories; internal facts cite repo paths, external claims cite sources
in SS13.

## 1. The program in one page

Six repositories form a governed local agent stack, organized as a
flight-test program. An agent attempts work inside a supervised loop; every
attempt is measured; every failure is journaled and matched against
evidence-bound memory; nothing changes live behavior without human sign-off;
and the whole program is validated as a system, not just per-repo.

| Repo | Role in the program | One-sentence function |
|---|---|---|
| [minder](https://github.com/xyzzing/minder) | the keeper / the tower | Supervises agents at one trust boundary: proxy, hooks, authority gates, memory governance, evals, ledger. |
| [cupola](https://github.com/xyzzing/cupola) | the furnace + watch-dome | Serves local inference: lifecycle FSM, conservative VRAM admission, model-file integrity, carbon accounting. |
| [windtunnel](https://github.com/xyzzing/windtunnel) | the tunnel | Measures agent behavior against deterministic rooms: paired counterfactuals, pinned fingerprints, published methodology. |
| windroos (rename pending) | the rose | Remembers: evidence-bound lessons, governed retrieval, digest-bound evidence telemetry. |
| [valkenier](https://github.com/xyzzing/valkenier) | the falconer | Prepares data and trains specialists under recorded decisions; a candidate ships only if it beats the best fixed setting. |
| [the mews](https://github.com/xyzzing/mews) | the house | Systems-integration rig and front door: contract-drift tripwires, full-loop shakedown, program map. |

The loop they implement:

```
work item ──▶ [agent loop: minder proxy 8390 → cupola engine] ──▶ output
                │        ▲            │                                │
                │        │            └─ failure? → gap journaled ─────┤
                │        └─ windroos returns the proven lesson ◀────────┘
                └─ minder guards the doors (hooks, serve-mode, authority gates)

control lane:  windtunnel validates any proposed change before it touches the process
               promotion law: nothing changes live behavior without human sign-off
               the ledger records every attempt, verdict, token, and gram of CO2e

learning outer loop (planned, docs/RSI.md): verified failures -> rewrites
               (self first, frontier fallback) -> governed SFT round ->
               candidate on a second profile -> certify -> owner pin.
               The recursion is in the loop; the pin is human.
```

The economic thesis: introducing an LLM into a work process moves the control
point from human habit to explicit gate. The rework loop becomes a learning
loop (failures leave residue as evidence-bound lessons), the variance source
(model + prompt + template) gets pinned and measured, and the human moves
from doing the step to owning the gates.

## 2. The naming system and law

The family coheres by texture, not domain: concrete single tokens, lowercase,
1-3 syllables, opaque until known, each named for its function. The
discovered system: the stack reads as a flight-test program (the falconer
trains, the tunnel tests, the rose charts, the tower keeps, the furnace
serves). The collective brand is "the mews" (the falconry house).

Naming law for any future repo: the name must be a concrete object from the
flight-test/falconry world whose function IS the repo's function, explainable
in one sentence. Invented compounds fail (towergate was evaluated and
rejected for minder on these grounds; minder stays - its search-collision
problem is a PEP 541 filing, not a rename, and a rename is a v1.0 decision).

Executed renames (2026-10-31): roomwise -> windtunnel (minder #63), sambal ->
valkenier (sambal #75/#76), sinter -> cupola (sinter #3/#4). Proposed:
repo-agent -> windroos (repo-agent-internal #29, v0.4 window, dual-emit
`repo_agent_*`/`windroos_*` event namespaces).

## 3. minder - the keeper (the tower)

State: PRD v0.11 amendment merged (docs/PRD-v0.11-amendment.md); v0.10
requirements sovereign. Live install serving the operator daily (proxy 8390,
sink 8392, console 8765). Suite ~1325 tests; gates: `make gates` (suite +
ruff + ratchet) plus mypy; tests run as `env -u LD_LIBRARY_PATH python3 -m
pytest -q`.

Mechanics that matter:

- Proxy 8390: single-file OpenAI-compatible proxy (`proxy.py`); the
  interception seam is `apply_auto_pipeline` with precedence escalation >
  client effort > laya band > mode > classifier; the injection guard hooks
  `do_POST` so it covers every request, not only class:auto traffic.
- Injection guard (#65/#67): `MINDER_INJECTION_GUARD=off|shadow` (off
  default, byte-identical golden test), isolated worker (laya-worker pattern:
  spawn-on-demand, flock guard, two-sided deadline, wedged worker exits),
  classifier Llama Prompt Guard 2 behind the optional `guard` extra,
  `injection_shadow` ledger events + append-only store table (migration 018),
  doctor check with live status ping. Shadow-only by design: canary authority
  requires human approval (owner decision recorded on PR #67).
- Hooks bridge (`hook.py`): two transports (zcode: exit 0 / block JSON; dsh:
  exit 2 + stderr digest). Law #6: detection never blocks the hot path, every
  failure mode exits 0. #68 adds `MINDER_HOOK_FAIL_MODE=closed` - outer guard
  only; inner detection fail-opens stay open (availability inversion: parsing
  untrusted content must never be block-capable).
- Memory: SQLite episodes/lessons via `minder_memory/db.py`; lessons are
  evidence-gated (promotion needs verified episodes or stated preferences
  with authority checks); append-only events ledger at
  `~/.local/state/minder/events.jsonl` (~138k events); tamper rows and
  integrity checks (ASI08 surface).
- Evals doctrine: grader-tested, deterministic oracles over judge models,
  pass^k over pass@k, paired statistics, no simulated users. Difficulty
  routing (laya, shadow modes, specialization bundle). Domain packs:
  finance-core-v1, legal-core-v1, difficulty-core-v1.
- Console 8765: operator web UI (verdict-first design); token ledger;
  frontier panel.
- GAP-TRAP framework: gap detection (skill_gaps), traps, quality ratchets;
  proven-red CI discipline (P2): each changed test must fail on pre-change
  code.

PRD v0.11 adds two planes: security enforcement S1-S9 (S1/S2 shipped;
response-side scan, egress redaction at `frontier.py`, E-stop, security
alerting, supply-chain doctor checks, serve-mode trio + toolcall-guard
contract, calibration cadence are the build list) and operations O1-O7
(work-order contract as keystone, FPY surface, Goodhart monitor, context-rot
metrics, approval inbox, escalation bundles, delegation capture #71).
Declared program objective: cost-per-correct at a fixed quality floor.

## 4. cupola - the furnace (engine test cell + watch-dome)

State: renamed from sinter (issue #3, PR #4); PRD v0.2 amendment merged
(docs/PRD-v0.2-amendment.md); ADR-001..005 in docs/decisions.md. Suite 362
tests; tests run as `PYTHONPATH=src env -u LD_LIBRARY_PATH python3 -m pytest
-q` when not pip-installed.

Mechanics:

- Lifecycle FSM over llama-server processes; conservative admission:
  weights + KV + recurrent + compute_buffers + reserve <= available VRAM;
  explicit failure over silent degradation (ADR-003). The engine OOM
  incident (1,734 restarts in one sweep) is why admission is strict.
- Model-file integrity: `cupola verify` (SHA256, streamed) + profile
  `weights_digest` pins enforced at admission before VRAM math.
- `contracts.py`: the engine-agnostic agent-facing boundary
  (`RuntimeSnapshot`, `InferenceIntent`, `InferenceGrant` - thermal
  backpressure clamp). ADR-002: strictly out-of-band supervisor, never in
  the request path. ADR-005 (accepted): backend abstraction at exactly two
  seams (spawn-command construction, capability probing); second backend
  lands behind a profile field with measured admission numbers.
- SCI carbon: power traces joined per case interval, gCO2e by ISO/IEC 21031,
  scope gpu_only, per-correct attribution.
- Serving today: strata fork (llama.cpp/HIP) as `qwen3.8-flash-next`, 131072
  ctx, loopback 8081.

Open on the owner's side: local main carries two unpushed carbon/SCI commits
diverged from origin, plus uncommitted Sentinel telemetry WIP
(cli.py/config.py/sensors.py) - landing it requires a stash, rebase onto the
renamed main (rename detection carries paths src/sinter/* -> src/cupola/*),
and stash pop. PRD v0.2 adds: certify-before-serve incoming inspection
(FR-C1), work-level backpressure extending InferenceGrant to work items
(FR-C2).

## 5. windtunnel - the tunnel (measurement)

State: R0-R4 built including R3 label export (PR #7); PRD amendment merged
(docs/PRD-amendment-2026-10-31.md); methodology v1 is the public contract
(docs/methodology.md, PR #10). Suite 143 tests; stdlib-only ratchet; CI =
ruff + pytest + ratchet + pr-acceptance + proven-red.

Mechanics:

- Rooms: deterministic cases with code oracles (decimal/int/enum/date,
  abstention probes). Sweeps walk a grid: reply_format (json|work) x effort
  (off/low/medium/high/xhigh) x thinking budgets, with repeats. Everything
  pinned per run: model_fingerprint (schema section 8, incl. chat template
  sha256), sampler parity, case-set digests.
- Paired counterfactuals: security cases ship clean+injected twins differing
  in exactly one untrusted field; the reported number is the paired delta.
  `security-core-v1`: 8 hand-authored pairs (16 cases), wrapper
  `injection-wrapper/v1` (marker GTWRAP-4C7E91); build-time converter folds
  garak-style probe dumps into the same shape. First live result: delta 0.00
  for qwen3.8-flash-next, n=80 (r5) - a floor, not a certificate.
- room_tier (R3 outcome label): least-assistance setting passing by strict
  majority across 3+ repeats (none/some/deep/escalate). `labels.py` writes
  `windtunnel.laya-dataset/v1` from four sources (abstention probes exact;
  reviewed MULTI_STEP kind table; audited task-difficulty/v1 records when
  present; sweep outcomes) with case-level ~20% holdout splits, redaction,
  and a min-per-label=5 refusal gate.
- The exchange schemas (`docs/SCHEMAS-room.md`) are the whole interface to
  minder: digest-pinned two-sided, mirror-sync procedure named, one
  "Sinter"-era reference pending the next sync.
- Methodology (public contract): repeats/majority rules, measured 15-25pt
  thinking noise floors, contamination policy (content-digested ids,
  holdout locks), versioning discipline, deterministic grading (judge models
  would be a separate flagged source), carbon join, and a "what a number does
  not mean" section.
- Visibility flip (private -> public) is decided (open moat) and waits for
  the methodology to age on main.

## 6. windroos - the rose (memory and evidence)

State: v0.3.0 shipped (repo xyzzing/repo-agent-internal, public mirror
xyzzing/repo-agent); all RA-000..035 landed or named-blocked. Rename to
windroos proposed (issue #29) for the v0.4 window. Suite 364 tests; single
runtime dependency: PyYAML.

Mechanics:

- Evidence telemetry: every verdict emitted digest-bound to minder's sink
  (8392) or a bounded local buffer with a surfaced degraded status when
  unreachable. Decisions fail closed locally.
- Memory governance (ahead of ASI06 guidance): evidence-gated lesson writes,
  pending-memory approval with owner attribution, content-free fingerprint
  stop-loop against stale-lesson reuse (measured 86% append-only reuse),
  supersession-only rewrites.
- Evidence export (`evidence_export.py`): eval manifests -> windtunnel
  sweep-run JSONL (`windtunnel.sweep-run/v1` - the schema-drift fix #28).
- PRD v1.4 amendment (docs/prd-v1.4-amendment.md): the windroos identity
  (dual-emit namespace window), source-provenance tiers on lessons (a lesson
  inherits the lowest provenance of its evidence chain; low-tier warns at
  retrieval - closes the poisoning path where a passing test legitimizes
  text from a poisoned document), contrast-pair export to valkenier
  (success/failure trajectory pairs per failure_key).
- Next pilots: RA-022/023 model switch (DeepSeek artifact or API profile) -
  unblocks the second live profile and gate G5.

## 7. valkenier - the falconer (training lane)

State: renamed from sambal (issue #75, PR #76); PRD amendment merged
(docs/PRD-amendment-2026-10-31.md). P0 landed (~12 slices: content-hashed
store, ingestion, profiling, recorded decisions, cleaning, preflight gate
verdicts, task contracts, guided CLI + Gradio shell, change records, scale
operator). Suite 438 tests; known order-dependent flake tracked (#73).

Phase structure (PRD SS14, sovereign):

- P1 remainder: review queue, leakage/as-of checks (proposed, issue #74 -
  recommended next slice, awaiting the SS19 per-slice approval), split
  plans, baselines/eval reports.
- P1.5 (new): contrast-pair training units from windroos' export (consumer
  of minder #49/#62 credit assignment) - governed rows, provenance and
  redaction carried through.
- P2: JobController/run_worker (currently NotImplementedError stubs) ->
  backend profiles -> M9-M11 first certified SFT-LoRA. Curriculum order from
  windtunnel room_tier labels.
- P3: evidence export, serving, additional backends.

Governance: SS19 - a phase is not permission; every slice needs the
maintainer's approval. SFT-first; RL ruled out at stack level. Distillation
direction (governed cloud records -> local specialist) is the approved
comercial lane.

## 8. The mews - the house (integration rig and front door)

Founded 2026-10-31 with PRD v1.0 (docs/PRD.md). Why it exists: every
cross-repo pair was digest-pinned, but no test exercised a producer against
a consumer's validator - the schema-drift incident (roomwise -> windtunnel
rename silently breaking the evidence export, fixed in
repo-agent-internal#28) was caught by hand, not by CI.

Phases: M0 contract-drift tripwires (founding test: the sweep-run schema
pair; every cross-repo file pair exercised producer-against-consumer); M1
full-loop shakedown in stub mode (intake -> guard -> engine stub -> lesson
retrieval -> guided retry -> verdict -> ledger -> evidence growth ->
windtunnel replay - the comic story as a test); M2 front door + nightly
certification reports (per-pair red/green with failure provenance); M3
security event tripwires; M4-M6 the RSI phases (PRD amendment
2026-11-09: FR-M7 data-plane tripwires for the learning path's shapes,
FR-M8 round certification with the re-pin gate, FR-M9 the loop shakedown
extended through rewrite -> train-export -> candidate manifest). Program
map for the learning loop: docs/RSI.md. Boundary: no runtime code,
imports no bird, is imported by no bird, owns no shape any bird owns.

## 9. Architecture view 1 - loop engineering

The loop has: state (context + lessons), actions (tools via hooks),
feedback (verdicts, gap detection), memory update (evidence-gated), policy
(room-policy files + lessons), safety (promotion law, authority gates).

Audited gaps: state composition unmeasured (context-rot metric planned, minder
O4); reward undefined for live loops (the work-order contract is the fix -
it is simultaneously the quality plan and the reward definition); credit
assignment filed (#62 trajectory accounting, #49 contrast pairs); exploration
missing (lesson selection is greedy; #50 ladder and #51 budget arms are the
seams); verifier-in-the-loop filed (#49/#50 rungs); delegation sub-loops
blind (#71 - owner-prioritized P0); update safety strong (human promotion,
append-only); training environments consciously deferred (SFT-first).

## 10. Architecture view 2 - process engineering

Before LLM: control = peer review at the end; rework = human repetition with
no residue; process memory = heads and SOPs; change control = informal.

After, with the stack: control point moves to minder's boundary (every call
measured); rework becomes a learning loop (windroos); MoC becomes promotion
law; pilot runs become windtunnel; process memory becomes evidence-bound
lessons; audit trail becomes the append-only ledger; constraint
identification becomes gap counts per failure_key.

Factory-side gaps (the plant around the loop), all mapped to homes: work-order
contract (windtunnel schema + minder runtime), FPY surface (minder queries),
work-level WIP limits (cupola), unified approval inbox (minder console),
escalation bundles (minder), incoming inspection (cupola + windtunnel),
calibration cadence (minder #59), E-stop (minder). What not to build:
scheduler suites, ERP-ish planning, reward models, RL environments,
multi-agent frameworks (dsh is the delegation layer; it needs observation).

## 11. Security posture

Threat mapping (OWASP agentic ASI01-10): ASI06 memory poisoning -
windroos' evidence gates, approval, fingerprint stop-loop, plus planned
source-provenance tiers; ASI07 tool misuse - hooks bridge, fail-closed
option, serve-mode trio + toolcall contract (build list); ASI08 cascades -
tamper rows, integrity checks, #71 delegation visibility. Detector posture:
shadow-first, human-gated canary (owner decision), inline-block only after
measured authority. The inversion rule: infrastructure failures may fail
closed; parsing untrusted content may not. Redaction-before-logging and
redact-before-egress. Supply chain: cupola verify + weight pins (landed);
mcp-scan, guarddog, gitleaks wiring (board). Measurement: windtunnel
security rooms + garak converter; detector drift rides #59. Known detector
limits: multilingual and indirect-injection blind spots (documented
independently); shadow mode finds the local distribution's own blind spots.
Forensics: append-only ledger; containment: the E-stop.

## 12. The 2026-10-31 execution record

18 PRs merged in one day across five repos, in dependency order, with
conflict resolutions (minder#68: both flag-vocabulary entries combined,
doctor.py held at 399 lines for the ratchet; windtunnel#7: README status
R0-R4 + labels truth). Landed: the schema-drift fix, the security wave
(shadow guard, fail-closed hooks, security pack, resistance view), R3
labels, the methodology contract, ADR-005, the LICENSE, docs catch-ups,
residue fixes, and six PRD documents. Two repos renamed (GitHub via REST
API - this gh version's `gh repo edit` has no --name flag). Local
directories renamed with remotes repointed.

Dogfood sweep: the injection pack ran against the local engine through
minder's proxy - clean 40/40, injected 40/40, delta 0.00 (r2 + r5), proving
the paired pipeline end to end. Known quirk confirmed: dsh headless sessions
emit no hook events, so headless workers bypass capture (#71 is the fix).

Prior evidence baseline (from earlier runs): room ladder 40.4% -> 77.6% ->
85.3% on 447 cases, closing ~82% of the gap to qwen3.8-omni-flash (94.9%);
frontier cloud 94.3 vs local 55.2 before controls; thinking noise floors
15-25pt; capture breakage 0/1306 hooks root-caused and fixed; laya
specialization 0.754 selective accuracy at 33% routing.

## 13. Decision log

- Canary authority for detectors requires human approval (promotion law
  applies to detector authority; no automatic escalation).
- Open moat: windtunnel's methodology is public; holdouts stay locked;
  visibility flip after the methodology ages on main.
- Governance over learning: SFT via approved slices only; RL out; no
  agent-initiated training.
- Objective: cost-per-correct at a fixed quality floor.
- towergate rejected for minder: invented compounds fail the naming law;
  churn cost highest at the center; PEP 541 + positioning solve search;
  revisit only as a v1.0 rebrand.
- Shadow-first detector deployment; the inversion rule for fail modes.
- Renames: valkenier and cupola executed; windroos proposed for v0.4;
  minder stays.
- RSI posture (2026-11-09): the loop closes through verified rewrites
  plus governed SFT rounds (docs/RSI.md); rewrite intelligence is self
  first (local engine + retrieved lessons) with the governed frontier lane
  as fallback; rounds are proposed-measured-pinned, never auto-promoted.
- RL remains ruled out. Adopting an RL refinement phase (GRPO/TB-GAE
  style, per Terminal-RSI) is an explicit future decision record with
  preconditions: at least two certified SFT rounds with measured gains, a
  valkenier governance amendment defining reward sources, and a serving
  decision for gradient-bearing artifacts. Tracked in mews.

## 14. Gap register and development plan

Combined priority (PE + loop engineering): (1) minder #80 learning-loop
delivery, the new top gap (filed 2026-11-04): the loop has never
delivered end to end - 0 live lessons, 102/102 injection-ledger rows are
block_duplicate misses. Measured causes: schema drift from an
in-place edit to shipped migration 015 (f6d7413), assist mode
decision_skill in force, a verification feed dead since 2026-10-22, 19
unclassified frontier traces; fix in flight (minder PR #86). The former
(1), minder #71 delegation capture, is largely resolved - see W1; (2)
the work-order contract (windtunnel FR-W1 schema + minder O1 runtime) -
the quality plan and reward definition are the same artifact; (3) FPY
surface (minder O2, ledger-only); (4) context-rot metrics (minder O4);
(5) #62 + #49 credit assignment and contrast-pair export - the data path
from loop failures to valkenier's training set.

Waves: W1 observation, capture plane largely landed - headless capture
works on dsh 0.2.x once the bridge pin is fixed (the pinned 0.1.5 bridge
failed to import, which is why capture read as dark); the remainder
moved to #72 (per-child tool-phase capture plugin) and #73 (capture
canary, since 2026-10-31 on systemd user timers, commit 08d2e57).
Context-rot, FPY and the objective declaration are still open. W2
keystone landed 2026-11-08 (windtunnel PR #15 the work-order shape,
minder PR #85 the runtime, mews PR #3 the tripwire pair, minder PR #86
the #80 repair); Goodhart monitor, E-stop and the approval inbox are
unmoved. W3 learning path, expanded 2026-11-09 into the RSI roadmap
(docs/RSI.md, mews#11): R0 the data plane - windroos-internal#38
(trajectory unification + contrast-pair export, under the #30 amendment)
-> valkenier#78/#77 (P1.5 training units) -> mews M4 tripwires; R1 field
readiness - the #80 fix deployed plus minder#88 eval-pair; R2 the first
wave - windroos-internal#39 (verified rewrites, self first with governed
frontier fallback), minder#92 (candidate alias), cupola#10 (candidate
profile, also unblocking G5/RA-022); R3 the first SFT round -
valkenier#80/#81/#82 under SS19 approvals; R4 certification -
windtunnel#17 (round report, R5/R6) + mews M5/M6, owner pin between
rounds. W4 plant (cupola WIP/backpressure FR-C2, incoming inspection
FR-C1 now consumed by cupola#10, #59 cadence). W5 the mews built out:
M0 tripwires paid immediately - the founding pair's first honest run was
red on real drift (windroos evidence export missing three sweep-run/v1
required keys, finish_reason/t_start/t_end; windroos-internal #36, fix
in PR #37); M1 shakedown and M2 nightly certification landed (mews#4,
with the model-drift probe from mews#8); M3 security tripwires next.

Open owner actions: land cupola's Sentinel WIP (stash/rebase/pop recipe in
repo); windtunnel visibility flip; windroos G5 - the v0.4.0 rename is
executed (remotes are now windroos-internal and windroos) but the release
is labelled partial, G5 gap stands (commit 24d607d), and the RA-022/023
transfer pilots stay blocked on a second live serving profile
(docs/RUN-NOTES.md addendum); FR-R1 provenance tiers are mid-flight on
#30, branch ra-r1-provenance. On the minder side, once #86 merges: run
minder-op migrate and redeploy the worker share, and decide the assist
mode switch (decision_skill in force means the retrieve branch never
runs). Closing keywords on tracking issues (#74, #6, #11, #30, #78 in
their repos; minder #13/#61/#71); PEP 541 filings; valkenier #74 SS19
approval.

## 15. Non-goals (ruled out, with reasons)

RL training loops (SFT-first; governance-not-learning boundary); vector
retrieval by default (provenance and fingerprints instead); agent-initiated
training or auto-promotion (promotion law); simulated users and judge-model
graders (deterministic oracles; a judge would be a separate flagged source);
cloud-first SaaS (local-first is the wedge); per-model benchmark tracks;
visual canvas tooling; multi-agent frameworks (dsh exists; needs capture,
not replacement); reward models and dense shaping (sparse honest verdicts);
guardrails-runtime adoption and homegrown classifiers (shadow-measured
off-the-shelf detectors instead); ERP-scale planning (one WIP number at
solo scale).

## 16. Sources

Internal-canonical: minder AGENTS.md + docs/PRD-v0.11-amendment.md +
docs/stack-roadmap-2026h2.md; cupola docs/decisions.md (ADR-001..005) +
docs/PRD-v0.2-amendment.md; windtunnel docs/PRD-windtunnel.md +
docs/methodology.md + docs/SCHEMAS-room.md + docs/PRD-amendment-2026-10-31.md;
windroos docs/prd-v1.3.md + docs/prd-v1.4-amendment.md +
docs/naming-assessment.md + docs/position-assessment.md; valkenier
docs/PRD.md (SS14, SS19) + docs/PRD-amendment-2026-10-31.md; the mews
docs/PRD.md + docs/PRD-amendment-2026-11-09.md + docs/RSI.md.

External: OWASP GenAI Security Project (genai.owasp.org) - LLM Top 10 and
agentic ASI01-10; "When Benchmarks Lie: Evaluating Malicious Prompt
Classifiers" (LessWrong, Feb 2026); Llama Prompt Guard 2 model card;
CourtGuard (arXiv 2510.19844); Agentic Context Engineering (arXiv
2510.04618); AFlow (arXiv 2410.10762); garak (NVIDIA); PyRIT (Microsoft);
mcp-scan, modelscan, guarddog, presidio, gitleaks (integration candidates,
verified licenses); LangGraph 1.0 durable-execution direction and A2A/AAIF
protocol landscape (context for the loops-vs-graphs verdict: the loop is the
runtime unit; graphs moved to compile target, durable substrate, and
network topology); Terminal-RSI (arXiv 2610.22192) - the recursive
self-improvement method the learning outer loop maps onto (docs/RSI.md).
