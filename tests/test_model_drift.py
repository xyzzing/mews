"""The model-drift probe's pure logic (mews#8).

The script drives HTTP and systemd, so only the deterministic parts are
imported here: probe grading (canonical answers) and the compare
verdict (regressions named, identity change reported but not red).
Grading lambdas live in the PROBES table; compare() is the FR-7-shaped
core - a regression is a probe that passed at pin and fails now, never
a rate dip alone, and an engine-identity change is surfaced, never
hidden and never silently fatal.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "model_drift",
    Path(__file__).resolve().parent.parent / "scripts" / "model_drift.py")
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)


def test_grades_are_canonical():
    by_id = {p["id"]: p for p in md.PROBES}
    assert by_id["p-arithmetic-1"]["grade"]("The answer is 42.")
    assert not by_id["p-arithmetic-1"]["grade"]("The answer is 43.")
    assert by_id["p-json-shape"]["grade"]('{"status": "ok", "n": 2}')
    assert not by_id["p-json-shape"]["grade"]('{"status": "ok"}')
    assert by_id["p-code-fix"]["grade"]('return d.get(k, "default")')
    assert not by_id["p-code-fix"]["grade"]("return d[k]")
    assert by_id["p-echo-exact"]["grade"]("MIEWS-DRIFT-PROBE-7391")
    assert not by_id["p-echo-exact"]["grade"]("MIEWS-DRIFT-PROBE-7392")


def test_compare_names_regressions_not_rate_dips():
    baseline = {"probes": {p["id"]: {"passed": True} for p in md.PROBES},
                "provenance": {"model": "qwen3.8-flash-next"}}
    results = {p["id"]: {"passed": True, "answer": ""} for p in md.PROBES}
    results["p-arithmetic-1"]["passed"] = False
    verdict = md.compare(baseline, results,
                         identity={"model": "qwen3.8-flash-next"})
    assert verdict["regressions"] == ["p-arithmetic-1"]
    assert verdict["improvements"] == []
    assert verdict["identity_changed"] is False


def test_improvements_are_reported_and_never_red():
    baseline = {"probes": {p["id"]: {"passed": False} for p in md.PROBES},
                "provenance": None}
    results = {p["id"]: {"passed": True, "answer": ""} for p in md.PROBES}
    verdict = md.compare(baseline, results, identity={"model": "new"})
    assert verdict["regressions"] == []
    assert verdict["improvements"]  # surfaced for the report
    assert verdict["identity_changed"] is True  # None -> identity


def test_identity_change_is_reported_not_red():
    baseline = {"probes": {p["id"]: {"passed": True} for p in md.PROBES},
                "provenance": {"unit_description": "refresh-0148"}}
    results = {p["id"]: {"passed": True, "answer": ""} for p in md.PROBES}
    verdict = md.compare(baseline, results,
                         identity={"unit_description": "refresh-0149"})
    assert verdict["regressions"] == []
    assert verdict["identity_changed"] is True  # 0148 -> 0149: report it


def test_compare_with_monkeypatched_identity(tmp_path, monkeypatch):
    baseline = {"probes": {p["id"]: {"passed": True} for p in md.PROBES},
                "provenance": {"model": "old"}}
    results = {p["id"]: {"passed": True, "answer": ""} for p in md.PROBES}
    monkeypatch.setattr(md, "engine_identity",
                        lambda: {"model": "new"})
    verdict = md.compare(baseline, results)
    assert verdict["identity_changed"] is True
    assert verdict["identity_pinned"] == {"model": "old"}
    assert verdict["identity_now"] == {"model": "new"}
