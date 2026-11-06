"""FR-M1 contract-drift tripwires.

Each test runs one producer's current landed output against one consumer's
current landed validator. A rename anywhere in the pair fails here first,
loudly. The founding pair is the sweep-run schema pair that
windroos-internal#28 fixed (and whose surviving key gap, windroos-internal
#36, this suite caught on its first run).
"""
import json
import subprocess

# A minimal windroos eval manifest, shape pinned by windroos's own tests
# (tests/test_evidence_export.py::manifest). The mews owns no shape: this
# fixture only drives the producer.
MANIFEST = {
    "command": "eval run",
    "eval_id": "mews-tripwire-0001",
    "policy": "none",
    "tasks": [
        {
            "task_id": "mews-pair-1",
            "family": "tripwire",
            "split": "dev",
            "verdict": "PASS",
            "reason_code": "ok",
            "attempts": 1,
            "usage": {"inputTokens": 10, "outputTokens": 2},
            "wall_seconds": 1.5,
            "run_id": "run-mews",
        },
        {
            "task_id": "mews-pair-2",
            "family": "tripwire",
            "split": "dev",
            "verdict": "FAIL",
            "reason_code": "check_failed",
            "attempts": 2,
            "usage": {"inputTokens": 5, "outputTokens": 1},
            "wall_seconds": 3.0,
            "run_id": "run-mews",
        },
    ],
    "aggregate": {"total": 2, "passed": 1, "failed": 1, "blocked": 0},
}

# One well-formed windtunnel.sweep-run/v1 record per docs/SCHEMAS-room.md
# section 2, used only by the negative self-test.
VALID_RUN_RECORD = {
    "schema": "windtunnel.sweep-run/v1",
    "setting": "json:off:0",
    "repeat": 1,
    "id": "tripwire-self-test",
    "answer": {},
    "raw_chars": 3,
    "finish_reason": "stop",
    "reasoning_tokens": 0,
    "completion_tokens": 7,
    "prompt_tokens": 42,
    "latency_s": 0.4,
    "error": None,
    "t_start": "2026-11-06T00:00:00+08:00",
    "t_end": "2026-11-06T00:00:01+08:00",
}


def _run_python(sibling: dict, code: str, *args: str) -> str:
    """Run a snippet inside the sibling's landed snapshot (python3 -I;
    the explicit sys.path insert is the only path in)."""
    result = subprocess.run(
        ("python3", "-I", "-c", code, *args),
        cwd=sibling["path"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_sweep_run_pair_producer_output_passes_consumer_validator(
    landed_windroos, landed_windtunnel, tmp_path
):
    """Founding pair (FR-M1): windroos's evidence export (producer of
    windtunnel.sweep-run/v1 lines) must satisfy windtunnel's validator."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    exported = tmp_path / "exported.jsonl"

    producer_code = (
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "from pathlib import Path\n"
        "from windroos.evidence_export import export_windtunnel\n"
        "n = export_windtunnel(Path(sys.argv[1]), Path(sys.argv[2]),"
        " model_profile='mews-tripwire')\n"
        "print(n)\n"
    )
    count = _run_python(
        landed_windroos, producer_code, str(manifest), str(exported)
    ).strip()
    lines = exported.read_text(encoding="utf-8").splitlines()
    assert int(count) == len(lines) == 2, "producer exported unexpected count"

    consumer_code = (
        "import json, sys\n"
        "sys.path.insert(0, '.')\n"
        "from windtunnel.schemas import validate\n"
        "errors = []\n"
        "with open(sys.argv[1], encoding='utf-8') as fh:\n"
        "    for i, line in enumerate(fh):\n"
        "        errors += [f'line {i}: {e}'"
        " for e in validate(json.loads(line))]\n"
        "print(json.dumps(errors))\n"
    )
    errors = json.loads(
        _run_python(landed_windtunnel, consumer_code, str(exported))
    )
    # The loud failure the rig exists to produce: a rename in either bird
    # lands here with the exact missing keys named.
    assert errors == [], (
        f"contract drift between windroos export "
        f"(landed {landed_windroos['commit']}) and windtunnel validator "
        f"(landed {landed_windtunnel['commit']}): {errors}"
    )


def test_tripwire_actually_detects_drift(landed_windtunnel, tmp_path):
    """Negative self-test: the consumer validator MUST reject a record
    whose required key was renamed. A tripwire that cannot fail catches
    nothing (mews AGENTS.md P2)."""
    drifted = dict(VALID_RUN_RECORD)
    drifted["tokens_done"] = drifted.pop("completion_tokens")  # simulated rename
    path = tmp_path / "drifted.jsonl"
    path.write_text(json.dumps(drifted) + "\n", encoding="utf-8")

    consumer_code = (
        "import json, sys\n"
        "sys.path.insert(0, '.')\n"
        "from windtunnel.schemas import validate\n"
        "print(json.dumps(validate(json.loads(open(sys.argv[1]).read()))))\n"
    )
    errors = json.loads(
        _run_python(landed_windtunnel, consumer_code, str(path))
    )
    assert any("completion_tokens" in e for e in errors), (
        f"validator failed to flag a renamed required key: {errors}"
    )


def test_tripwire_accepts_the_documented_shape(landed_windtunnel, tmp_path):
    """Control: the documented SCHEMAS-room.md section 2 record itself
    validates clean, so the negative self-test's rejection is drift, not
    an over-strict consumer."""
    path = tmp_path / "valid.jsonl"
    path.write_text(json.dumps(VALID_RUN_RECORD) + "\n", encoding="utf-8")
    consumer_code = (
        "import json, sys\n"
        "sys.path.insert(0, '.')\n"
        "from windtunnel.schemas import validate\n"
        "print(json.dumps(validate(json.loads(open(sys.argv[1]).read()))))\n"
    )
    errors = json.loads(
        _run_python(landed_windtunnel, consumer_code, str(path))
    )
    assert errors == [], f"documented shape rejected: {errors}"
