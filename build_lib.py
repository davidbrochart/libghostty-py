#!/usr/bin/env python3
"Build libghostty-vt from a ghostty checkout and bundle the shared lib into ghostty/_lib."
import os,shutil,subprocess,sys,sysconfig,tempfile,tomllib
from pathlib import Path

ROOT = Path(__file__).parent

def build_config():
    with open(ROOT/'pyproject.toml', 'rb') as f: return tomllib.load(f)['tool']['libghostty']

def ghostty_src():
    "The ghostty checkout to build from: $GHOSTTY_SRC, defaulting to ghostty-src inside this project."
    src = Path(os.environ.get('GHOSTTY_SRC', ROOT/'ghostty-src')).expanduser().resolve()
    if not (src/'build.zig').exists(): sys.exit(f"No ghostty checkout at {src}; set GHOSTTY_SRC")
    res = subprocess.run(['git', '-C', str(src), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    if res.returncode: sys.exit(res.stderr.strip())
    version = build_config()['vt-version']
    tag = f'vt-{version}'
    expected = subprocess.run(
        ['git', '-C', str(src), 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}'],
        capture_output=True, text=True,
    )
    if expected.returncode:
        sys.exit(f"Ghostty release tag {tag} is missing; fetch it in {src}")
    if (rev := res.stdout.strip()) != expected.stdout.strip():
        sys.exit(f"Ghostty checkout is {rev}; expected release {tag} ({expected.stdout.strip()})")
    return src

def _built_lib(prefix, returncode):
    if sys.platform == 'win32': root,pattern,name = prefix/'bin','ghostty-vt.dll','libghostty-vt.dll'
    elif sys.platform == 'darwin': root,pattern,name = prefix/'lib','libghostty-vt*.dylib','libghostty-vt.dylib'
    else: root,pattern,name = prefix/'lib','libghostty-vt.so*','libghostty-vt.so'
    found = [p for p in root.glob(pattern) if p.is_file() and not p.is_symlink()]
    if len(found) != 1: sys.exit(f"Expected one shared library in {root}, found {found} (zig exit {returncode})")
    return found[0],name

def zig_executable():
    version = build_config()['zig-version']
    local = ROOT/'.zig'/('zig.exe' if sys.platform == 'win32' else 'zig')
    executable = str(local) if local.is_file() else shutil.which('zig')
    if not executable:
        sys.exit(f"Install Zig {version} on PATH or run python install_zig.py")
    actual = subprocess.check_output([executable, 'version'], text=True).strip()
    if actual != version:
        sys.exit(f"Zig is {actual}; expected {version}")
    return executable


def _zig_build(src, prefix):
    # Zig supplies the MinGW toolchain, so Windows x64 builds need no MSVC SDK.
    target = ['-Dtarget=x86_64-windows-gnu'] if sys.platform == 'win32' and sysconfig.get_platform() == 'win-amd64' else []
    return subprocess.run([zig_executable(), 'build', '-Demit-lib-vt=true', '-Doptimize=ReleaseFast', '-Dcpu=baseline', *target, '--prefix', str(prefix)],
        cwd=src)

def main():
    src = ghostty_src()
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp)/'out'
        # Ghostty also builds static/xcframework outputs which may fail; this package only needs the shared artifact.
        res = _zig_build(src, prefix)
        lib,name = _built_lib(prefix, res.returncode)
        dest = ROOT/'ghostty'/'_lib'
        dest.mkdir(exist_ok=True)
        for old in dest.glob('libghostty-vt*'): old.unlink()
        shutil.copy2(lib, dest/name)
        print(f'Bundled: {name} (from {lib.name})')

if __name__=='__main__': main()
