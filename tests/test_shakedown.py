"""M1 full-loop shakedown (mews#4, FR-M2): the comic story, as a test.

One work item through the whole loop, hop by hop, against each bird's
LANDED code in stub mode - no GPU, no network (the seam-map pass proved
every hop inside `unshare -rn`). Seams come from the measured map at
.sweeps/heartbeat/seam-map.md; where minder's delivery tests live only
on unmerged branches, the pattern is inlined from main's
tests/test_learning_injections.py.

Data dependencies, not temporal ones: the ledger row (hop 7) is written
during the guard evaluate (hop 2), and windroos's promote (hop 8) runs
before its retrieve (hop 4) in the seed phase. Assertions pin stable
fields - statuses, tiers, flags - never generated ids or timestamps.

Mechanics: each hop is a script file run as `python3 -I <script>` with
the script importing the bird from its landed snapshot by absolute path
(`-I` drops cwd and PYTHONPATH, so nothing else survives); every mutable
path (stores, exports) is handed over via MEWS_TMP and lands in the
test's tmp dir. Snapshots are the siblings' local `main` (the same
landed-state rule as the tripwires).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

FAIL_EVENT = {
    "session_id": "shakedown-s1",
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "repo": "/repo",
    "tool_input": {"command": "pnpm install"},
    "tool_response": "Error: pnpm: command not found (exit 127)",
}
WARDEN = {"action": "think", "level": 1, "digest": "[minder] warden"}
LESSON_TEXT = "install pnpm before the workspace build"

MINDER_SEED_AND_GUARD = r'''
import json, os, sys
sys.path.insert(0, os.environ["MEWS_SNAP"])
from minder_memory import db, from_hook, policy, store
from minder_memory.canonicalise import failure_key
from minder_memory.lessons import promote_lesson

dbp = os.environ["MEWS_STORE"]
ev = json.loads(os.environ["MEWS_FAIL_EVENT"])
hook = from_hook.to_event(ev)
fkey = failure_key(hook, ev["repo"])

# the lesson's source episode: failure, then a verification event and a
# verified close (the field's clean-run evidence), then the operator lift
ep_id, _ = store.open_episode(dict(hook, failure_key=fkey), db_path=dbp)
conn = db.connect(dbp)
conn.execute(
    "INSERT INTO events (event_id, ts, event_type, session_id, task_id,"
    " repo, repo_version, tool, failure_key, action_fingerprint,"
    " payload_json, redaction_status) VALUES"
    " ('ev-verify', '2026-11-07T00:00:00+00:00', 'verification',"
    " 's-verify', 's-verify', ?, '', 'bash', ?, 'fp',"
    " '{\"tests_passed\": 1}', 'redacted')", (ev["repo"], fkey))
conn.execute(
    "INSERT INTO episode_events (episode_id, event_id, seq)"
    " VALUES (?, 'ev-verify', 1)", (ep_id,))
conn.execute(
    "UPDATE episodes SET status = 'verified', closed_at ="
    " '2026-11-07T00:00:00+00:00' WHERE episode_id = ?", (ep_id,))
conn.commit()
conn.close()
lesson, status = promote_lesson(
    ep_id, os.environ["MEWS_LESSON"],
    anti_pattern="do not re-run npm install to fix this",
    verification={"tests_passed": True}, db_path=dbp)
assert status == "ok", status

# hop 2 + 7: a new session repeats the failure; the guard injects the
# lesson and writes the ledger row during the evaluate
from_hook.record(dict(ev, session_id="shakedown-s2"), db_path=dbp)
from_hook.record(dict(ev, session_id="shakedown-s2"), db_path=dbp)
out = policy.evaluate(dict(hook, session_id="shakedown-s2"),
                      json.loads(os.environ["MEWS_WARDEN"]),
                      db_path=dbp, repo=ev["repo"])
conn = db.connect(dbp)
rows = [dict(r) for r in conn.execute(
    "SELECT tier, digest_injected, assist_mode FROM learning_injections"
    " WHERE lesson_id IS NOT NULL")]
conn.close()
print(json.dumps({"action": out["action"],
                  "lesson_in_digest":
                      os.environ["MEWS_LESSON"][:20] in out["digest"],
                  "rows": rows}))
'''

MINDER_INTAKE = r'''
import json, os, sys
sys.path.insert(0, os.environ["MEWS_SNAP"])
from minder_memory.db import connect
connect(os.environ["MEWS_STORE"]).close()
from minder_op.cli import main
rc = main(["task", "declare", "--domain", "coding",
           "--task", "mews-shakedown", "--note", "FR-M2 intake"])
print(json.dumps({"rc": rc}))
'''

MINDER_VERDICT = r'''
import json, os, sys
sys.path.insert(0, os.environ["MEWS_SNAP"])
from minder_memory import from_hook
ev = json.loads(os.environ["MEWS_FAIL_EVENT"])
# the guided retry applies the lesson, then runs the tests: the command
# must name a recognised runner and the output a clean passing count
# (from_hook._verification_evidence, structural not semantic)
retry = dict(ev, session_id="shakedown-s2",
             tool_input={"command": "pytest tests/test_supplier.py"},
             tool_response="2 passed in 0.31s")
out = from_hook.record(retry, db_path=os.environ["MEWS_STORE"])
print(json.dumps({"closed": out.get("closed")}))
'''

CUPOLA_STUB = r'''
import json, os, sys
sys.path.insert(0, os.path.join(os.environ["MEWS_SNAP"], "src"))
from cupola.contracts import (RuntimeSnapshot, InferenceIntent,
                              evaluate_intent)
snap = RuntimeSnapshot(ts=0.0)
intent = InferenceIntent(thinking_mode="deep", thinking_tokens=256)
grant = evaluate_intent(snap, intent)
print(json.dumps({"granted": grant.granted, "reason": grant.reason}))
'''

WINDROOS_GROWTH_RETRIEVE = r'''
import json, os, sys
sys.path.insert(0, os.environ["MEWS_SNAP"])
from pathlib import Path
from windroos.memory import MemoryStore
from windroos import retrieval
ms = MemoryStore(Path(os.path.join(os.environ["MEWS_TMP"], "w.sqlite")))
mid = ms.record(kind="failure_pattern",
                claim="install pnpm before the workspace build",
                scope={}, provenance={"source_event_ids": ["ev-1"]})
mid = mid["memory_id"] if isinstance(mid, dict) else mid
before = len(retrieval.retrieve(ms, "", ["pnpm", "install"], "qwen@r020"))
ms.promote(mid, "evidence_checked")
hits = retrieval.retrieve(ms, "", ["pnpm", "install"], "qwen@r020")
block, _reconstruction = retrieval.render_injection(hits)
print(json.dumps({"before": before, "after": len(hits),
                  "header_ok": "NOT instructions" in block}))
'''

WINDROOS_EXPORT = r'''
import json, os, sys
sys.path.insert(0, os.environ["MEWS_SNAP"])
from pathlib import Path
from windroos.evidence_export import export_windtunnel
manifest = json.loads(os.environ["MEWS_MANIFEST"])
mp = Path(os.path.join(os.environ["MEWS_TMP"], "manifest.json"))
mp.write_text(json.dumps(manifest), encoding="utf-8")
out = Path(os.path.join(os.environ["MEWS_TMP"], "run-a.jsonl"))
n = export_windtunnel(mp, out, model_profile="mews-shakedown")
print(json.dumps({"rows": n}))
'''

WINDTUNNEL_REPLAY = r'''
import hashlib, json, os, sys
tmp = os.environ["MEWS_TMP"]
sys.path.insert(0, os.environ["MEWS_WINDTUNNEL"])
from pathlib import Path
from windtunnel import schemas
from windtunnel.sweep_report import sweep_report
d = Path(tmp)
task = json.loads((d / "manifest.json").read_text(
    encoding="utf-8"))["tasks"][0]
case = {"id": task["task_id"], "family": task["family"],
        "kind": "tripwire", "group": "mews", "relation": "identity",
        "task": "prove the loop", "inputs": {"rate": "0.10"},
        "rules": [], "answer_types": {"value": "decimal"},
        "grading": {"value": {"type": "decimal", "tol": "0.01"}},
        "expected": {"value": "42"}}
(d / "cases.jsonl").write_text(json.dumps(case) + "\n",
                               encoding="utf-8")
cases_sha = hashlib.sha256((d / "cases.jsonl").read_bytes()).hexdigest()
manifest = {
    "schema": "windtunnel.sweep-manifest/v1",
    "windtunnel_version": "0.1.0",
    "git_sha": "mews-shakedown",
    "target": {"base_url": "stub://mews-shakedown", "kind": "engine",
               "model": "stub-agent"},
    "model_fingerprint": {"chat_template_sha256": "0" * 64,
                          "engine": "mews-shakedown-stub"},
    "preflight": {"server_default_thinking": False, "mechanism": "none",
                  "effort_levels_accepted": [], "thinking_budget_accepted":
                  False},
    "cases": {"path": "cases.jsonl", "sha256": cases_sha,
              "suite": "mews-shakedown", "seed": 0, "count": 1},
    "grid": [{"setting": "policy:none", "reply_format": "text",
              "effort": "off", "budget": 0}],
    "repeats": 1, "max_tokens": 256, "temperature": 0,
    "started_at": "2026-11-07T00:00:00Z",
    "finished_at": "2026-11-07T00:01:00Z",
}
(d / "sweep-manifest.json").write_text(json.dumps(manifest),
                                       encoding="utf-8")
report = sweep_report(d, d / "cases.jsonl")
print(json.dumps({"validated": schemas.validate(report),
                  "keys": sorted(report.keys())}))
'''


@pytest.fixture()
def run_py(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()

    def run(sibling, script_text, env_extra=None):
        script = scripts / f"hop-{len(list(scripts.iterdir()))}.py"
        script.write_text(script_text, encoding="utf-8")
        env = {**os.environ,
               "MEWS_TMP": str(tmp_path),
               "MEWS_SNAP": sibling["path"],
               "MEWS_STORE": str(tmp_path / "minder.sqlite"),
               "MEWS_FAIL_EVENT": json.dumps(FAIL_EVENT),
               "MEWS_WARDEN": json.dumps(WARDEN),
               "MEWS_LESSON": LESSON_TEXT,
               "MEWS_MANIFEST": json.dumps(_replay_manifest())}
        if env_extra:
            env.update(env_extra)
        result = subprocess.run(
            ("python3", "-I", str(script)), cwd=tmp_path,
            capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise AssertionError(
                f"hop script failed ({script.name}):\n"
                f"{result.stderr[-2000:]}")
        return json.loads(result.stdout.strip().splitlines()[-1])

    return run


def _replay_manifest():
    return {
        "command": "eval run",
        "eval_id": "mews-shakedown-0001",
        "policy": "none",
        "tasks": [
            {"task_id": "shakedown-a", "family": "tripwire",
             "split": "dev", "verdict": "PASS", "reason_code": "ok",
             "attempts": 1,
             "usage": {"inputTokens": 10, "outputTokens": 2},
             "wall_seconds": 1.0, "run_id": "run-shakedown"},
            {"task_id": "shakedown-b", "family": "tripwire",
             "split": "dev", "verdict": "FAIL",
             "reason_code": "check_failed", "attempts": 2,
             "usage": {"inputTokens": 5, "outputTokens": 1},
             "wall_seconds": 2.0, "run_id": "run-shakedown"},
        ],
        "aggregate": {"total": 2, "passed": 1, "failed": 1, "blocked": 0},
    }


def test_shakedown_full_loop(run_py, landed_minder, landed_cupola,
                             landed_windroos, landed_windtunnel,
                             tmp_path):
    # Hop 1: intake contract - the CLI declares the task on its scratch store.
    intake = run_py(landed_minder, MINDER_INTAKE)
    assert intake["rc"] == 0, "minder-op task declare failed"

    # Hop 8 first (seed phase): windroos growth - provenance promotes the
    # candidate past the retrieval floor; hop 4's retrieve then surfaces it.
    growth = run_py(landed_windroos, WINDROOS_GROWTH_RETRIEVE)
    assert growth == {"before": 0, "after": 1, "header_ok": True}

    # Hop 2 (guard) + Hop 7 (ledger row): the verified lesson is delivered
    # into the digest on a repeated failure; the row lands during the
    # evaluate with tier exact and digest_injected 1.
    guard = run_py(landed_minder, MINDER_SEED_AND_GUARD)
    assert guard["action"] == "block_duplicate", guard
    assert guard["lesson_in_digest"], "lesson text never reached the digest"
    assert any(r["tier"] == "exact" and r["digest_injected"] == 1
               and r["assist_mode"] == "block_duplicate"
               for r in guard["rows"]), guard["rows"]

    # Hop 3: cupola stub - the grant answers from the contracts, no engine.
    grant = run_py(landed_cupola, CUPOLA_STUB)
    assert grant == {"granted": True, "reason": "nominal"}

    # Hop 9 first half: windroos evidence export (deterministic rows).
    exported = run_py(landed_windroos, WINDROOS_EXPORT)
    assert exported["rows"] == 2

    # Hop 5 (guided retry, in-process form) + Hop 6 (verdict): the retry's
    # clean runner output closes the minder episode verified.
    verdict = run_py(landed_minder, MINDER_VERDICT)
    assert verdict["closed"] == "verified", (
        "a clean runner output must close the episode verified")

    # Hop 9: windtunnel replay - regrade the exported evidence through
    # windtunnel's own sweep_report; schemas must validate clean.
    replay = run_py(landed_windtunnel, WINDTUNNEL_REPLAY,
                    {"MEWS_WINDTUNNEL": landed_windtunnel["path"]})
    assert replay["validated"] == [], replay
    assert "families" in replay["keys"] and "resistance" in replay["keys"]
