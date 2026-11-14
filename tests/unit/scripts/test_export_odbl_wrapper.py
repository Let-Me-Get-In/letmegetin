"""The ODbL wrapper builds the exact argv, in both modes, against a fake docker.

No database and no docker: the point is the command construction, which is what a
wrong mount target or a missing `--delta` silently breaks in production.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "export-odbl.sh"

FAKE_DOCKER = """#!/bin/sh
printf '%s\\n' "$@" > "$FAKE_DOCKER_ARGV"
"""

# A jq that marks the call and fails: the wrapper must never run one.
FAKE_JQ = """#!/bin/sh
: > "$FAKE_JQ_CALLED"
exit 1
"""

# Compose appends `run -v` mounts, so `export_data:/data/export` would stay the
# service's read-only entry. The writable second target is the contract.
BASE_ARGV = [
    "compose",
    "-p",
    "letmegetin-prod",
    "-f",
    "docker-compose.prod.yml",
    "run",
    "--rm",
    "-T",
    "-v",
    "export_data:/data/export-rw",
    "api",
    "letmegetin-admin",
    "export",
    "odbl",
    "--out",
    "/data/export-rw",
]


def _run(mode: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], list[str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "docker.argv"
    jq_called = tmp_path / "jq.called"
    for name, body in (("docker", FAKE_DOCKER), ("jq", FAKE_JQ)):
        shim = bin_dir / name
        shim.write_text(body)
        shim.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_DOCKER_ARGV": str(argv_file),
        "FAKE_JQ_CALLED": str(jq_called),
    }
    # -u on top of the script's own set -euo: an undefined $OUT in either branch fails here.
    result = subprocess.run(
        ["bash", "-u", str(SCRIPT), mode],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    argv = argv_file.read_text().splitlines() if argv_file.exists() else []
    return result, argv, jq_called


def test_snapshot_writes_the_writable_mount_and_no_delta(tmp_path: Path) -> None:
    result, argv, jq_called = _run("snapshot", tmp_path)

    assert result.returncode == 0, result.stderr
    assert argv == BASE_ARGV
    assert "--delta" not in argv
    assert "--since" not in argv
    assert not jq_called.exists()


def test_delta_appends_the_flag_and_never_reads_the_watermark(tmp_path: Path) -> None:
    result, argv, jq_called = _run("delta", tmp_path)

    assert result.returncode == 0, result.stderr
    assert argv == [*BASE_ARGV, "--delta"]
    assert "export_data:/data/export-rw" in argv
    assert "--out" in argv
    assert argv[argv.index("--out") + 1] == "/data/export-rw"
    assert "--since" not in argv
    assert "cat" not in argv
    assert not jq_called.exists()


def test_an_unknown_mode_exits_2_without_running_anything(tmp_path: Path) -> None:
    result, argv, _ = _run("--out=/etc", tmp_path)

    assert result.returncode == 2
    assert "usage: export-odbl.sh {snapshot|delta}" in result.stderr
    assert argv == []
