"""Packaging checks use a fake library to avoid compiling Ghostty."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


@pytest.fixture
def project(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ("setup.py", "_build_backend.py", "pyproject.toml", "MANIFEST.in",
                 "README.md", "LICENSE", "LICENSE.ghostty", "CHANGELOG.md"):
        shutil.copy2(root / name, tmp_path / name)
    shutil.copytree(root / "ghostty", tmp_path / "ghostty",
                    ignore=shutil.ignore_patterns("_lib", "__pycache__"))
    lib = tmp_path / "ghostty" / "_lib"
    lib.mkdir()
    (lib / "libghostty-vt.so").write_bytes(b"previously built library")
    (tmp_path / "build_lib.py").write_text(
        "from pathlib import Path\n"
        "Path('library-build-ran').touch()\n"
        "Path('ghostty/_lib/libghostty-vt.so').write_bytes(b'new library')\n"
    )
    return tmp_path


def run_backend(project, code, bundle):
    env = dict(os.environ)
    # Ambient state must not affect the explicit build setting.
    env["LIBGHOSTTY_BUNDLE"] = "0" if bundle is None else "1"
    settings = {} if bundle is None else {"bundle": bundle}
    code = f"config_settings = {settings!r}; " + code
    return subprocess.run([sys.executable, "-c", code], cwd=project, env=env,
                          text=True, capture_output=True)


@pytest.mark.parametrize("bundle", [None, "true", "false", ["false"]])
def test_wheel_contents_and_requirements(project, bundle):
    result = run_backend(project,
        "from _build_backend import build_wheel; build_wheel('dist', config_settings=config_settings)", bundle)
    assert result.returncode == 0, result.stdout + result.stderr
    wheel, = (project / "dist").glob("*.whl")
    bundled = bundle not in ("false", ["false"])
    assert (project / "library-build-ran").exists() == bundled
    assert wheel.name.endswith("-py3-none-any.whl") == (not bundled)
    with zipfile.ZipFile(wheel) as archive:
        assert ("ghostty/_lib/libghostty-vt.so" in archive.namelist()) == bundled
        metadata = archive.read(next(n for n in archive.namelist() if n.endswith('/WHEEL')))
        assert f"Root-Is-Purelib: {str(not bundled).lower()}".encode() in metadata
    result = run_backend(project,
        "import json; from _build_backend import get_requires_for_build_wheel; "
        "print(json.dumps(get_requires_for_build_wheel(config_settings)))", bundle)
    assert result.returncode == 0, result.stdout + result.stderr
    requirements = json.loads(result.stdout.splitlines()[-1])
    assert ("ziglang==0.17.0" in requirements) == bundled


def test_invalid_bundle_setting(project):
    result = run_backend(project,
        "from _build_backend import get_requires_for_build_wheel; "
        "get_requires_for_build_wheel(config_settings)", "invalid")
    assert result.returncode != 0
    assert "bundle must be 'true' or 'false'" in result.stderr


def test_external_wheel_after_bundled_build(project):
    for bundle in ("true", "false"):
        result = run_backend(project,
            "from _build_backend import build_wheel; build_wheel('dist', config_settings=config_settings)", bundle)
        assert result.returncode == 0, result.stdout + result.stderr
    wheel, = (project / "dist").glob("*-py3-none-any.whl")
    with zipfile.ZipFile(wheel) as archive:
        assert not any("/_lib/" in name for name in archive.namelist())


def test_metadata_matches_external_wheel(project):
    result = run_backend(project,
        "from pathlib import Path; Path('metadata').mkdir(); "
        "from _build_backend import prepare_metadata_for_build_wheel, build_wheel; "
        "prepare_metadata_for_build_wheel('metadata', config_settings); "
        "build_wheel('dist', config_settings, 'metadata')", "false")
    assert result.returncode == 0, result.stdout + result.stderr
    wheel, = (project / "dist").glob("*-py3-none-any.whl")
    with zipfile.ZipFile(wheel) as archive:
        assert not any("/_lib/" in name for name in archive.namelist())


def test_build_setting_does_not_leak(project):
    result = run_backend(project,
        "from _build_backend import get_requires_for_build_wheel, bundle_library; "
        "get_requires_for_build_wheel(config_settings); "
        "assert bundle_library() is True; "
        "assert 'ziglang==0.17.0' in get_requires_for_build_wheel()", "false")
    assert result.returncode == 0, result.stdout + result.stderr
