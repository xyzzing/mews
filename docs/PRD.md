# The mews — PRD v1.0

The systems-integration rig and front door of the flight-test program.
Repository: xyzzing/mews (name free, verified 2026-10-31). No PyPI package -
it is a rig, not a library.

## 1. Purpose

Five repos ship and version independently: minder (the keeper/tower),
cupola (the furnace + watch-dome), windtunnel (the tunnel), windroos (the
rose), valkenier (the falconer). Each repo's CI proves itself. Nothing
proves them *together*. The founding incident: the roomwise -> windtunnel
schema rename broke repo-agent's evidence export silently - every cross-repo
pair was digest-pinned, and no test anywhere exercised a producer against a
consumer's validator. The mews exists so the program's integration failures
are caught by a gate, not by an operator reading a diff.

The name: the mews is the falconry house where all the birds live. minder
keeps it.

## 2. Product boundaries

- The mews runs tests and publishes documents. It contains no runtime code,
  imports no bird, and is imported by no bird.
- It consumes only published exchange schemas (windtunnel.*/vN, minder event
  kinds, windroos telemetry contracts, cupola contracts.py shapes) - it owns
  no shape any bird owns.
- Each bird's gates remain sovereign: the mews adds system-level acceptance
  on top; it never replaces a repo's own CI.
- Wireable to live endpoints when present, stub endpoints when not; every
  shakedown must pass in stub mode so the rig never depends on a GPU being
  free.

## 3. Requirements

- FR-M1. Contract-drift tripwires: for every cross-repo file pair (schemas,
  event kinds, telemetry contracts), one test that runs the producer's
  current output against the consumer's current validator. Founding test:
  the sweep-run schema pair that issue repo-agent-internal#28 fixed. A
  rename anywhere fails here first, loudly.
- FR-M2. Full-loop shakedown: an end-to-end pass of one work item through
  the program with stubs - intake contract -> minder guard -> cupola stub ->
  windroos lesson retrieval -> guided retry -> verdict -> ledger row ->
  windroos evidence growth -> windtunnel replay. The comic story, as a test.
- FR-M3. Security event tripwires: guard-event shapes vs ledger consumer;
  injection_shadow verdict fields vs digest/alert consumers.
- FR-M4. Certification runs: a nightly integration pass over all tripwires +
  shakedown, with a report page and a red/green verdict per pair. Red = a
  bird drifted.
- FR-M5. Front door: the family map (the flight-test program), the naming
  law, links to each methodology (windtunnel's, minder's security posture as
  it lands), the glossary. This is the open-moat surface for the program.
- FR-M6. Failure provenance: every red tripwire names the producing commit
  and consuming validator version, so the fix lands in the right bird.

## 4. Phases

- M0: contract-drift tripwires (FR-M1) - the founding test first. Acceptance:
  the suite fails if any bird renames a shared schema without a matching
  consumer update; passes today on all landed pairs.
- M1: full-loop shakedown with stubs (FR-M2). Acceptance: green in CI
  without any live engine; deterministic; under two minutes.
- M2: front door (FR-M5) + nightly certification (FR-M4). Acceptance: the
  program map renders; the nightly report exists with per-pair verdicts.
- M3: security tripwires (FR-M3) + provenance in reports (FR-M6).

## 5. Non-goals

No runtime code; no scheduling or orchestration of the birds; no test
frameworks beyond the repos' own conventions; no collective PyPI package;
no duplicate coverage of what a bird's own CI already proves.
