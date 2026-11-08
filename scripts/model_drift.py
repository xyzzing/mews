#!/usr/bin/env python3
"""The model-drift probe (mews#8): is the live engine's quality moving?

One small battery of deterministic probes through minder's supervised
proxy (:8390, never the engine directly), graded canonically - exact
strings, canonical numbers, parseable JSON, structural code shapes -
compared against a pinned baseline. A probe that passed at pin time and
fails now is a named regression; the engine's identity (strata refresh /
engine build from the systemd unit description plus /health fields) is
recorded in every baseline and report, and a changed identity is
surfaced as "re-pin after review" - deliberate updates are expected,
silent ones are not.

Stdlib only; imports no bird. The engine belongs to the night windows:
when :8081 is down the probe reports skipped and exits 0 - the
certification must not go red because someone is re-tuning the furnace.

Usage:
  python3 scripts/model_drift.py            # compare against the baseline
  python3 scripts/model_drift.py --pin      # (re)write the baseline
  python3 scripts/model_drift.py --report F # append a markdown section
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

PROXY = "http://127.0.0.1:8390/v1/chat/completions"
ENGINE_HEALTH = "http://127.0.0.1:8081/health"
BASELINE = Path(__file__).resolve().parent / "model-drift-baseline.json"
TIMEOUT_S = 90
MAX_TOKENS = 96

def _grade_json(answer):
    m = re.search(r"\{.*\}", answer, re.DOTALL)
    if not m:
        return False
    try:
        doc = json.loads(m.group(0))
    except ValueError:
        return False
    return doc.get("status") == "ok" and doc.get("n") == 2


PROBES = [
    {"id": "p-arithmetic-1",
     "prompt": "What is 7 * 6? Answer with just the number.",
     "grade": lambda a: "42" in a},
    {"id": "p-arithmetic-2",
     "prompt": "What is 13 + 29? Answer with just the number.",
     "grade": lambda a: "42" in a},
    {"id": "p-arithmetic-3",
     "prompt": "What is 144 / 12? Answer with just the number.",
     "grade": lambda a: "12" in a},
    {"id": "p-echo-exact",
     "prompt": "Reply with exactly: MIEWS-DRIFT-PROBE-7391",
     "grade": lambda a: "MIEWS-DRIFT-PROBE-7391" in a},
    {"id": "p-json-shape",
     "prompt": 'Return ONLY a JSON object {"status": "ok", "n": 2} and'
               " nothing else.",
     "grade": _grade_json},
    {"id": "p-code-fix",
     "prompt": "Rewrite this Python line so a missing key returns the"
               " string default instead of raising: def get(d, k):"
               " return d[k]. Reply with the single line only.",
     "grade": lambda a: ".get(" in a and "default" in a},
    {"id": "p-negation",
     "prompt": "Answer with just YES or NO: is 17 a prime number?",
     "grade": lambda a: "YES" in a.upper()},
    {"id": "p-sequence",
     "prompt": "Reply with exactly these three words in order: alpha"
               " beta gamma",
     "grade": lambda a: re.search(r"alpha\s+beta\s+gamma", a) is not None},
]


def _post(url, payload):
    req = Request(url, data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def _get(url):
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def engine_identity():
    """Best-effort identity of what is actually serving: /health fields
    plus the strata unit description (refresh / engine build / serve
    layer). A missing piece degrades to a shorter identity; the probe
    never fabricates one."""
    identity = {}
    try:
        health = _get(ENGINE_HEALTH)
        identity["model"] = health.get("model")
        identity["service"] = health.get("service")
        identity["max_context"] = health.get("max_context")
    except (OSError, ValueError):
        return None
    try:
        out = subprocess.run(
            ("systemctl", "--user", "show", "strata-8081.service",
             "-p", "Description", "--value"),
            capture_output=True, text=True, timeout=10,
            check=False)
        if out.returncode == 0 and out.stdout.strip():
            identity["unit_description"] = out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return identity


def run_probes():
    """Run every probe once; returns {probe_id: {"passed", "answer"}}.
    Any probe that raises/streams garbage is a fail with the error
    named - an unanswerable probe is exactly the signal."""
    results = {}
    for probe in PROBES:
        answer, error = None, None
        # one retry for transport-level failures only (timeouts on the
        # single-slot engine are contention, not capability); a
        # graded-wrong answer fails straight - that is the signal
        for attempt in (0, 1):
            try:
                doc = _post(PROXY, {
                    "model": "qwen-auto",
                    "messages": [{"role": "user",
                                  "content": probe["prompt"]}],
                    "max_tokens": MAX_TOKENS,
                    "temperature": 0,
                })
                answer = doc["choices"][0]["message"]["content"] or ""
                error = None
                break
            except (OSError, ValueError, KeyError) as exc:
                error = exc
        if answer is None:
            results[probe["id"]] = {
                "passed": False,
                "answer": f"<error: {error}>",
                "flaky_transport": True}
            continue
        results[probe["id"]] = {"passed": bool(probe["grade"](answer)),
                                "answer": answer[:200]}
    return results


def compare(baseline, results, identity=None):
    """Regressions first: passed at pin, failing now. Returns the
    verdict dict; identity change is reported, never hidden, but does
    not itself turn the verdict red (deliberate updates are expected -
    that is what --pin re-baselines)."""
    regressions, improvements = [], []
    for probe in PROBES:
        pid = probe["id"]
        was = baseline.get("probes", {}).get(pid, {}).get("passed")
        now = results.get(pid, {}).get("passed")
        if was is True and now is False:
            regressions.append(pid)
        elif was is False and now is True:
            improvements.append(pid)
    identity = identity if identity is not None else engine_identity()
    return {"regressions": regressions, "improvements": improvements,
            "rate_now": (sum(1 for r in results.values() if r["passed"])
                         / len(PROBES)),
            "rate_pinned": baseline.get("rate"),
            "identity_changed": baseline.get("provenance") != identity,
            "identity_now": identity,
            "identity_pinned": baseline.get("provenance")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pin", action="store_true",
                        help="(re)write the baseline from this run")
    parser.add_argument("--report", metavar="FILE",
                        help="append a markdown section to FILE")
    parser.add_argument("--quiet", action="store_true",
                        help="print one line only")
    args = parser.parse_args(argv)

    try:
        _get(ENGINE_HEALTH)
    except OSError:
        line = "model-drift: skipped - engine down (the night window" \
               " owns it; not red)"
        print(line)
        if args.report:
            with open(args.report, "a", encoding="utf-8") as fh:
                fh.write(f"- {line}\n")
        return 0

    identity = engine_identity()
    results = run_probes()
    passed = sum(1 for r in results.values() if r["passed"])

    if args.pin:
        baseline = {"pinned_at": _now_iso(), "provenance": identity,
                    "rate": passed / len(PROBES),
                    "probes": results}
        BASELINE.write_text(json.dumps(baseline, indent=1),
                            encoding="utf-8")
        print(f"model-drift: baseline pinned at {passed}/{len(PROBES)}"
              f" - {identity.get('unit_description', identity)}")
        return 0

    if not BASELINE.exists():
        line = ("model-drift: no baseline - run"
                " `python3 scripts/model_drift.py --pin` once to pin"
                " the current engine; not red")
        print(line)
        if args.report:
            with open(args.report, "a", encoding="utf-8") as fh:
                fh.write(f"- {line}\n")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    verdict = compare(baseline, results, identity=identity)
    red = bool(verdict["regressions"])
    if not args.quiet:
        print(json.dumps(verdict, indent=1, default=str))
    line = (f"model-drift: {'RED' if red else 'ok'} -"
            f" {passed}/{len(PROBES)} probes pass now"
            f" (pinned {verdict['rate_pinned']:.2f});"
            f" regressions: {verdict['regressions'] or 'none'};"
            f" identity_changed: {verdict['identity_changed']}"
            f" ({_identity_line(verdict['identity_now'])})")
    print(line)
    if args.report:
        with open(args.report, "a", encoding="utf-8") as fh:
            fh.write(f"- {line}\n")
            if red:
                fh.writelines(
                    f"  - regression `{pid}`: pinned answer"
                    f" `{baseline['probes'][pid]['answer'][:80]}`"
                    f" -> now"
                    f" `{results[pid]['answer'][:80]}`\n"
                    for pid in verdict["regressions"])
            if verdict["identity_changed"]:
                fh.write("  - engine identity changed since pin -"
                         " review and re-pin"
                         " (`python3 scripts/model_drift.py --pin`)"
                         " after confirming the refresh is wanted\n")
    return 1 if red else 0


def _identity_line(identity):
    if not identity:
        return "unknown"
    desc = identity.get("unit_description")
    return desc if desc else f"{identity.get('service')}," \
                             f" {identity.get('model')}"


def _now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
