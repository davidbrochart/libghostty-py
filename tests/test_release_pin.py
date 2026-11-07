"""Validate release-tag pins against real Git checkouts."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def source(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / 'build_lib.py'
    spec = importlib.util.spec_from_file_location('release_build_lib', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'build_config', lambda: {'vt-version': '1.0.0'})
    monkeypatch.setenv('GHOSTTY_SRC', str(tmp_path))

    def git(*args):
        return subprocess.run(
            ['git', '-C', str(tmp_path), '-c', 'user.name=Test',
             '-c', 'user.email=test@example.invalid', *args],
            check=True, capture_output=True, text=True,
        )

    git('init')
    (tmp_path / 'build.zig').touch()
    git('add', 'build.zig')
    git('commit', '-m', 'Release')
    return module, git, tmp_path


def test_annotated_release_tag(source):
    module, git, path = source
    git('tag', '-a', 'vt-1.0.0', '-m', 'Release 1.4.0')
    assert module.ghostty_src() == path.resolve()


def test_wrong_commit_is_rejected(source):
    module, git, _ = source
    git('tag', 'vt-1.0.0')
    git('commit', '--allow-empty', '-m', 'After release')
    with pytest.raises(SystemExit, match='expected release vt-1.0.0'):
        module.ghostty_src()


def test_missing_release_tag_is_actionable(source):
    module, _, _ = source
    with pytest.raises(SystemExit, match='release tag vt-1.0.0 is missing; fetch it'):
        module.ghostty_src()
