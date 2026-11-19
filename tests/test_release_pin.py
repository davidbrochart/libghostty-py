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


@pytest.mark.parametrize('tag', ['vt-1.0.0', 'vt-1.0.1', 'vt-1.1.0'])
def test_annotated_release_tag(source, tag):
    module, git, path = source
    git('tag', '-a', tag, '-m', 'Release')
    assert module.ghostty_src() == path.resolve()


def test_wrong_commit_is_rejected(source):
    module, git, _ = source
    git('tag', 'vt-1.0.0')
    git('commit', '--allow-empty', '-m', 'After release')
    with pytest.raises(SystemExit, match=r'Expected a vt-1\.x\.x release tag at HEAD'):
        module.ghostty_src()


def test_missing_release_tag_is_actionable(source):
    module, _, _ = source
    with pytest.raises(SystemExit, match='fetch the tag and check it out'):
        module.ghostty_src()


@pytest.mark.parametrize('tag', ['vt-2.0.0', 'vt-1.0.1-rc.1'])
def test_unsupported_tag_is_rejected(source, tag):
    module, git, _ = source
    git('tag', tag)
    with pytest.raises(SystemExit, match=r'Expected a vt-1\.x\.x release tag at HEAD'):
        module.ghostty_src()
