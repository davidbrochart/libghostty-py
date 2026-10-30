"""Exercise library discovery without requiring a native library to import."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def loader(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'ghostty' / '_ffi.py'
    tree = ast.parse(source.read_text())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == '_libpath')
    namespace = {
        'Path': Path,
        'sys': SimpleNamespace(prefix=str(tmp_path / 'prefix'), platform='linux'),
        '__file__': str(tmp_path / 'ghostty' / '_ffi.py'),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    monkeypatch.delenv('LIBGHOSTTY_LIB', raising=False)
    return namespace['_libpath'], namespace


@pytest.mark.parametrize(('platform', 'relative'), [
    ('linux', 'lib/libghostty-vt.so'),
    ('darwin', 'lib/libghostty-vt.dylib'),
    ('win32', 'Library/bin/ghostty-vt.dll'),
])
def test_environment_library(loader, platform, relative):
    discover, namespace = loader
    namespace['sys'].platform = platform
    library = Path(namespace['sys'].prefix) / relative
    library.parent.mkdir(parents=True)
    library.touch()
    assert discover() == str(library)


@pytest.mark.parametrize('variable', ['LIBGHOSTTY_LIB', 'LINGHOSTTY_LIB'])
def test_stray_environment_variable_is_ignored(loader, monkeypatch, variable):
    discover, namespace = loader
    external = Path(namespace['sys'].prefix) / 'lib' / 'libghostty-vt.so'
    external.parent.mkdir(parents=True)
    external.touch()
    monkeypatch.setenv(variable, '/missing/or/incompatible/library.so')
    assert discover() == str(external)


def test_bundled_library_takes_priority(loader):
    discover, namespace = loader
    bundled = Path(namespace['__file__']).parent / '_lib' / 'libghostty-vt.so'
    external = Path(namespace['sys'].prefix) / 'lib' / 'libghostty-vt.so'
    for library in (bundled, external):
        library.parent.mkdir(parents=True)
        library.touch()
    assert discover() == str(bundled)


def test_missing_library_error(loader):
    discover, namespace = loader
    with pytest.raises(OSError, match='install a compatible shared library') as error:
        discover()
    assert str(Path(namespace['sys'].prefix) / 'lib' / 'libghostty-vt.so') in str(error.value)
