"""M0 tripwire scaffolding: locate sibling repos and snapshot LANDED state.

The mews imports no bird and owns no shape (docs/PRD.md section 2), so
every cross-repo check runs a producer's current LANDED output through a
consumer's current LANDED validator via subprocess, each in its own
directory. "Landed" means the sibling's default branch (main), snapshotted
read-only with `git archive` - never the working checkout, whose branch may
be anything, and never a write into the sibling's .git.

A missing sibling skips WITH REASON (the minder room-boundaries pattern);
a silent pass measures nothing.
"""
import os
import subprocess
import tarfile

import pytest

SIBLINGS_ROOT = os.environ.get(
    "MEWS_SIBLINGS", os.path.join(os.path.expanduser("~"), "projects")
)


def _git(repo, *args):
    return subprocess.run(
        ("git", "-C", repo, *args), capture_output=True, text=True, check=True
    )


def _landed_snapshot(tmp_path_factory, name: str):
    """Extract sibling `name`'s main branch into a temp dir; return
    (path, commit) or None when the repo is absent."""
    repo = os.path.join(SIBLINGS_ROOT, name)
    if not os.path.isdir(os.path.join(repo, ".git")):
        return None
    commit = _git(repo, "rev-parse", "--short", "main").stdout.strip()
    dest = tmp_path_factory.mktemp(f"landed-{name}-{commit}-")
    archive = dest / "snapshot.tar"
    _git(repo, "archive", "--format=tar", "--output", str(archive), "main")
    with tarfile.open(archive, "r:") as tar:
        tar.extractall(dest, filter="data")
    archive.unlink()
    return dest, commit


def _sibling_fixture(name: str):
    @pytest.fixture(scope="session")
    def fixture(tmp_path_factory):
        snap = _landed_snapshot(tmp_path_factory, name)
        if snap is None:
            pytest.skip(
                f"sibling repo '{name}' not found under {SIBLINGS_ROOT} "
                "(set MEWS_SIBLINGS); the tripwire measures nothing without it"
            )
        path, commit = snap
        return {"path": str(path), "commit": commit, "name": name}

    fixture.__name__ = f"landed_{name}"
    return fixture


landed_windtunnel = _sibling_fixture("windtunnel")
landed_windroos = _sibling_fixture("windroos")
landed_minder = _sibling_fixture("minder")
landed_cupola = _sibling_fixture("cupola")
