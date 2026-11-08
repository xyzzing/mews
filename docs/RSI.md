# The RSI loop - program map

Version: 2026-11-09. Tracking issue: xyzzing/mews#11. The method being
mapped: Terminal-RSI (arXiv 2610.22192), which improves a terminal agent by
alternating two phases - RSR (recursive self-rewrite: rewrite verified
failed/partial trajectories into corrected ones) and RPR (recursive
policy-refine: train on those rewrites). This document maps that loop onto
the six repos, states where the stack diverges from the paper and why, and
carves the work into issues. It is a plan, not a claim: nothing below is
built unless its issue says so.

## 1. Where the loop stands

The stack runs a governed agent loop today, but it is open-loop: failures
leave lessons (windroos memory, minder episodes), and nothing feeds back
into the model. Stage by stage:

| RSI stage | What exists | Where | State |
|---|---|---|---|
| Task families | rooms with code oracles; coding harness; 8D suites | windtunnel `benchmarks/*-core-v1`, cupola `benchmarks/coding-core-v2`, minder `benchmarks/*` | exists (static, hand-authored) |
| Agent execution | dsh headless under packets, supervised | windroos `taskrun.py` + `adapters/dsh.py`, minder proxy 8390 | exists |
| Verification | frozen-digest verifier; pytest oracles; strict grading | windroos `verifier.py`, minder `minder_op/runner.py`, windtunnel `evals/score.py` | exists (strongest stage) |
| Trajectory corpus | turns in dsh `session.v3.jsonl`, verdict in `handoff.json`, episode in minder - never joined | windroos `taskrun.py`, cupola `transcript.py`, minder `minder_memory/from_hook.py` | fragmented -> windroos-internal#38 |
| Rewriting (RSR) | nothing; nearest analogues are verify-repair and lessons | minder #49, windroos memory | absent -> windroos-internal#39 |
| Training (RPR) | export-only dataset builder; P2 designed, stubs | minder `minder_memory/train_export.py`, valkenier `src/valkenier/jobs/` | absent -> valkenier#80/#81 |
| Candidate serving | one pinned engine; no candidate lane | cupola `supervisor.py`, strata-8081 | absent -> cupola#10, minder#92 |
| Certification | nightly tripwires + drift probe with identity pin | mews `mews-certification.sh`, `scripts/model_drift.py` | exists for drift; rounds -> windtunnel#17, mews#13 |

## 2. The RSI round

One round (RSI-n), overnight cadence, an owner decision between every
round. The recursion lives in the loop, not in autonomy: each round is
proposed, measured, and pinned or rejected by the owner (promotion law,
STACK.md SS13).

```
            ┌────────────────────────── the supervised loop (today) ─────────┐
            │ minder proxy 8390 -> cupola engine :8081 -> dsh -> windroos    │
            └──────┬─────────────────────────────────────────────────┬───────┘
                   │ verdicts + episodes                             │ failures
                   ▼                                                 ▼
  1 CAPTURE   windroos joins session turns + handoff verdict + minder episode
              into one trajectory record per run            (windroos#38)
  2 SELECT    group failures by failure_key, balance families via room_tier
              labels (windtunnel labels.py)
  3 RSR-n     rewrite wave: local engine (qwen-think + retrieved lessons)
              corrects its own trajectories; stubborn failures escalate to a
              governed frontier consult. A rewrite counts only if it
              re-executes to a verified pass            (windroos#39)
  4 RPR-n     governed SFT-LoRA round on verified rewrites + contrast pairs,
              overnight job under recorded decisions    (valkenier#80, #81)
  5 CONVERT   adapter merge -> GGUF -> quantize -> weights digest + training
              manifest                                       (valkenier#82)
  6 SERVE     candidate on cupola's second profile, admitted only with a
              manifest; minder routes by candidate alias (cupola#10, minder#92)
  7 CERTIFY   control-vs-treatment: eval-pair, windtunnel round report
              (McNemar, per-family, holdout law), coding-core-v2, 8D
              comparator                                        (windtunnel#17)
  8 DECIDE    mews round certification section + re-pin gate; owner pins or
              rejects. Round n+1 runs on the winner    (mews#13, mews#14)
```

Self-improvement metrics carried per round: the self-rewrite share (how much
of the wave the local engine fixed without frontier help), round-over-round
per-family deltas, corpus growth by failure_key, and cost-per-correct at
the fixed quality floor (the program objective, STACK.md SS13).

## 3. Paper-to-stack mapping, divergences stated

| Terminal-RSI component | This stack | Divergence |
|---|---|---|
| RSR: rewrite verified trajectories | windroos#39 rewrite wave; acceptance = re-executed verified pass | none in spirit; rewrites are offline data production, not replayed experience |
| RPR: RL policy refinement | valkenier P2 SFT-LoRA rounds | deliberate: RL ruled out at stack level (SS15); see the RL decision record below |
| Critic-inheriting across stages | pinned baseline + protected comparator thresholds carried across rounds (minder comparator: completion drop >5pp fails; n>=20) | the critic is external and adversarial, not a trained value model |
| TB-GAE (turn-boundary advantage decay) | not mapped | RL-internal; applies only if the RL decision record ever passes |
| Family Dense Reward (FDR) | family-stratified sparse reporting + room_tier curriculum ordering | deliberate: no reward models or dense shaping (SS15); families gate curriculum and reporting, not reward |
| Success-Prioritized Reward (SPR) | strict binary grading unchanged (windtunnel `evals/score.py`); per-field fractions reported as context, never the gate | already the stack's law (sparse honest verdicts) |
| Verifier-gated benchmarks (Terminal-Bench, LHTB, SWR100) | windtunnel rooms + cupola coding-core-v2 + minder 8D suites | same role: deterministic oracles, no judge models |
| 5-stage pipeline (RSR-1 -> RPR-1 -> RSR-2 -> RPR-2) | overnight rounds with an owner pin between each | the human is inside the loop by design |
| Rewrite source | self first (qwen-think + retrieved lessons), governed frontier fallback (minder frontier lane; valkenier#48 cloud-records lane) | owner decision 2026-11-09; keeps self-improvement measurable while the corpus can still grow |

Honest scale note: the paper's numbers (Terminal-Bench 2.1 86.52%, LHTB
strict 5/46 from 0/46, SWR100 3% -> 6%) come from a full RL pipeline on a
27B base with task-family training infrastructure. Local rounds are SFT on
a smaller corpus from one engine's failures. First rounds may ship no
candidate at all - rejection is a valid, protected outcome; the comparator
holds the floor.

## 4. GPU and cadence law

Single slot, one GPU (mews docs/agents.md; engine total_slots 1):

- Rewrite waves are inference: run on the served engine, daytime legal.
- Training is overnight, when the served slot is idle. Valkenier's job
  window, not a scheduler.
- Candidate admission is cupola's VRAM math, not an orchestrator:
  baseline + candidate coexist only if weights + KV + reserve fit
  (ADR-003); otherwise the baseline stops for the measurement window and
  restarts after (explicit, ledgered).
- No central scheduler anywhere: each bird keeps its own timers (the
  minder capture-canary pattern); the mews stays a rig (PRD SS5).

## 5. Governance invariants the loop must not bend

- Promotion law: nothing pins itself. Round certification proposes; the
  owner's decision record disposes (STACK.md SS13).
- minder never trains (docs/lora-offline.md); valkenier owns training
  under recorded decisions (SS19: a phase is not permission - every slice
  needs maintainer approval).
- The mews owns no shape: the contrast-pair schema is windroos's, the
  round report input shape is windtunnel's, the training manifest is
  valkenier's, the candidate identity is cupola's. mews tripwires consume
  them producer-against-consumer (FR-M7).
- Sparse honest verdicts: strict gates stay binary; partial credit is
  reported context.
- The frontier fallback is the governed distillation lane (approved,
  STACK.md SS7), recorded per consult - never an open egress path.
- Everything is ledgered: rounds, waves, jobs, admissions, aliases, pins.

## 6. Build order and issue map

R0 data plane (starts now, no approvals blocking the windroos side):
windroos-internal#38 (trajectory unification + contrast-pair export, under
the #30 amendment) -> valkenier P1.5 contrast-pair training units
(valkenier#78/#77, already open) -> mews#12 tripwires once both sides
exist.

R1 field readiness (owner actions already listed in STACK.md SS14):
minder#80's fix (#86) deployed - `minder-op migrate`, worker-share refresh,
the assist-mode decision - so the learning loop actually delivers live
lessons; minder#88 eval-pair as the paired-measurement substrate.

R2 first wave: windroos-internal#39 (needs R0 + R1), minder#92
candidate-alias routing, cupola#10 candidate profile (which also unblocks
windroos G5 / RA-022 pilots).

R3 first training round: valkenier#80 (job surface) -> #81 (SFT-LoRA
profile + short certified run) -> #82 (adapter -> GGUF -> digest export).
Each slice needs SS19 approval.

R4 first certification: windtunnel#17 round report + mews#13 round
certification and re-pin gate -> owner decision -> cadence (weekly rounds
unless the data says otherwise).

## 7. The RL decision record (future, gated)

RL remains ruled out (SS15, decision log). The paper's RPR shows what an
RL phase would add; adopting one is an explicit owner decision record with
preconditions, not a drift:

1. At least two certified SFT rounds delivering measured gains on the
   round report (else there is no evidence the corpus supports policy
   optimization at all).
2. A valkenier governance amendment (SS19) defining reward sources - the
   stack's sparse verdicts are not a dense reward; building one contradicts
   SS15 and must be decided, not improvised.
3. A minder/cupola serving decision for gradient-bearing artifacts.

Tracked in mews#15 (the decision record lands in STACK.md SS13 when made;
the tracking issue holds the preconditions above).

## 8. Sources

Internal: mews docs/STACK.md (loop, waves, decision log, gap register) and
docs/PRD-amendment-2026-11-09.md (FR-M7..FR-M9); windroos
docs/prd-v1.4-amendment.md (contrast-pair bridge, FR-R2); valkenier
docs/PRD.md (SS14 phases, SS19 slice approval, FR-11.1 SFT-first); cupola
docs/PRD-v0.2-amendment.md (FR-C1 incoming inspection) and docs/decisions.md
(ADR-003 admission, ADR-005 seams); windtunnel docs/methodology.md
(contamination policy, holdout locks); minder docs/lora-offline.md (the
training ban). External: Terminal-RSI, arXiv 2610.22192 (abstract-level
claims only in this document).
