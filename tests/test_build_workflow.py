"""The build workflow and the app must agree on what the app is called.

Nothing else ties the two together: the workflow stamps the name into the
macOS bundle and the app sets the same name on the Qt application. This app's
display name already matched, but its five sibling repos showed the packaged
file name in the dock because the two drifted apart unnoticed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from app.main import _APP_NAME

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"
SMOKE = ROOT / ".github" / "scripts" / "connector_smoke.py"


def _workflow_env(name: str) -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(rf"^  {re.escape(name)}: *(\S.*?) *$", text, re.MULTILINE)
    assert match is not None, f"{name} is not set in {WORKFLOW.name}"
    return match.group(1)


def _project_name() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^name *= *"(.+?)"', text, re.MULTILINE)
    assert match is not None, "pyproject.toml has no project name"
    return match.group(1)


def test_workflow_bundle_name_matches_the_app() -> None:
    # macOS shows the .app folder name in the dock and ignores the plist's
    # CFBundleName/CFBundleDisplayName, so the bundle name *is* the dock name.
    # It has to stay space-free, hence the app's name with spaces removed.
    assert _workflow_env("APP_BUNDLE_NAME") == _APP_NAME.replace(" ", "")


def test_workflow_bundle_name_has_no_spaces() -> None:
    # The bundle is a file people copy between competition folders; spaces in
    # it make every shell command that touches it need quoting.
    assert " " not in _workflow_env("APP_BUNDLE_NAME")


def test_workflow_bundle_id_is_reverse_dns_for_this_project() -> None:
    # Copied between six sibling repos, so pin it to this project's own name -
    # a bundle id left pointing at a sibling would silently make macOS treat
    # the two apps as one.
    bundle_id = _workflow_env("APP_BUNDLE_ID")
    assert re.fullmatch(r"[a-z0-9]+(\.[a-z0-9-]+)+", bundle_id), bundle_id
    assert bundle_id.rsplit(".", 1)[-1] == _project_name()


def _smoke(*command: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - this repo's own script
        [sys.executable, str(SMOKE), *command],
        cwd=ROOT,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_every_build_runs_a_connector_from_the_frozen_app() -> None:
    # A windowed onefile build gets its pipes only if Windows hands them over;
    # nothing but a run of the built file shows it, so no platform is skipped.
    text = WORKFLOW.read_text(encoding="utf-8")
    step = re.search(
        r"- name: Smoke-run a built-in connector.*?(?=\n      - |\Z)", text, re.DOTALL
    )
    assert step is not None, "the build no longer smoke-runs a connector"
    assert "if:" not in step.group(0)
    assert "connector_smoke.py" in step.group(0)


def test_the_smoke_check_passes_for_the_chronometer_run_from_source() -> None:
    done = _smoke(sys.executable, "-m", "app.main")
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_smoke_check_fails_on_a_hello_of_another_kind() -> None:
    hello = '{"type": "hello", "protocol": 1, "connector": "x", "kind": "chips"}'
    done = _smoke(sys.executable, "-c", f"print({hello!r})")
    assert done.returncode == 1
