#!/usr/bin/env python3
"Build libghostty-vt from a ghostty checkout and bundle the shared lib into ghostty/_lib."
import os,re,shutil,subprocess,sys,sysconfig,tempfile,tomllib
from pathlib import Path

ROOT = Path(__file__).parent

def build_config():
    with open(ROOT/'pyproject.toml', 'rb') as f: return tomllib.load(f)['tool']['libghostty']

def ghostty_src():
    "The ghostty checkout to build from: $GHOSTTY_SRC, defaulting to ghostty-src inside this project."
    src = Path(os.environ.get('GHOSTTY_SRC', ROOT/'ghostty-src')).expanduser().resolve()
    if not (src/'build.zig').exists(): sys.exit(f"No ghostty checkout at {src}; set GHOSTTY_SRC")
    version = build_config()['vt-version']
    major, minor, patch = map(int, version.split('.'))
    series = f'vt-{major}.'
    tags = subprocess.run(
        ['git', '-C', str(src), 'tag', '--points-at', 'HEAD', '--list', f'{series}*'],
        capture_output=True, text=True,
    )
    if tags.returncode: sys.exit(tags.stderr.strip())
    for tag in tags.stdout.splitlines():
        release = re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag.removeprefix(series))
        if release and tuple(map(int, release.groups())) >= (minor, patch):
            return src
    sys.exit(f"Expected a {series}x.x release tag at HEAD in {src} "
             f"(minimum vt-{version}); fetch the tag and check it out")

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
