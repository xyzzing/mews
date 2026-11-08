# The mews - PRD amendment 2026-11-09: RSI phases M4-M6

Tracking issue: xyzzing/mews#11. Program map: docs/RSI.md. This amendment
adds the certification requirements for the RSI loop (recursive
self-improvement per Terminal-RSI, arXiv 2610.22192, mapped in RSI.md).
The v1.0 requirements stay sovereign; nothing here changes the rig law
(no runtime code, imports no bird, is imported by no bird, owns no shape
any bird owns - PRD SS2/SS5).

## 1. New requirements

- FR-M7. RSI data-plane tripwires: for each new cross-repo shape on the
  learning path, one test that runs the producer's current output against
  the consumer's current validator, exactly as FR-M1 does for the founding
  pairs. Founding pairs of this phase: windroos contrast-pair export vs
  the valkenier ingestion validator; the valkenier training manifest vs
  the cupola incoming-inspection validator. A rename or field drift on
  either side fails here first, with provenance per FR-M6.
- FR-M8. RSI round certification: when a trained candidate exists, the
  nightly report gains a round section: pinned baseline vs candidate
  (consuming the windtunnel round report), per-family verdicts, and
  candidate provenance (round id, training-manifest digest, adapter
  digest, engine identity string). Re-pin gate: the report goes red when
  the serving engine identity differs from the pinned identity and no
  owner decision record references the change. This extends the existing
  model-drift mechanics (scripts/model_drift.py: changed identity is a
  reported re-pin signal, not a red; the round gate adds the red for a
  re-pin without a decision).
- FR-M9. RSI loop shakedown in stub mode: the FR-M2 comic story extends
  through the learning path with stubs - evidence growth -> windtunnel
  replay -> rewrite stub (a planted failure yields one verified-rewrite
  row, one rejected attempt with reason) -> training-set export stub ->
  candidate manifest stub -> round report stub with a pin decision.
  Deterministic, no GPU, same laws as FR-M2 (green in CI without any live
  engine, under two minutes).

## 2. Phases

- M3 stays next and unchanged (security tripwires + provenance, FR-M3 +
  FR-M6). The RSI phases may interleave after M3; M4's founding pairs go
  red-until-landed by design, the same founding-red discipline as M0.
- M4: RSI data-plane tripwires (FR-M7). Acceptance: both founding pairs
  exist and are exercised producer-against-consumer; each pair has
  demonstrated red on real or planted drift before it counts as green;
  red names the drifted side per FR-M6.
- M5: RSI round certification (FR-M8). Acceptance: the round section
  renders from fixture inputs (a stub candidate) with all provenance
  fields; the re-pin gate is red on identity mismatch without a decision
  reference, green with one.
- M6: RSI loop shakedown (FR-M9). Acceptance: the extended comic story
  passes deterministically in CI with no live engine; the rewrite stub
  proves both acceptance paths (verified rewrite kept, unverified attempt
  rejected with reason).

## 3. Dependencies (from docs/RSI.md build order)

M4 needs windroos-internal#38 plus the valkenier ingestion side, and
valkenier#82 plus the cupola inspection side. M5 and M6 can build earlier
on stubs: M5's fixture inputs and M6's stubs are self-contained in the
rig. The sibling law is unchanged: missing or unlanded siblings skip with
reason; landed pairs must be green.

## 4. Non-goals (unchanged, restated for the loop)

No training, no model hosting, no candidate storage at the mews; no
auto-pinning - the re-pin gate reports, the owner decides; no scheduling
or orchestration of birds; no new schema ownership (every shape FR-M7
exercises belongs to its bird).
