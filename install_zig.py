#!/usr/bin/env python3
"""Install the pinned official Zig toolchain locally for bundled wheel builds."""
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from build_lib import ROOT, build_config


def install():
    version = build_config()['zig-version']
    executable = 'zig.exe' if platform.system() == 'Windows' else 'zig'
    destination = ROOT / '.zig'
    if (destination / executable).is_file():
        actual = subprocess.check_output([str(destination / executable), 'version'], text=True).strip()
        if actual == version:
            return destination / executable
        raise RuntimeError(f"Cached Zig is {actual}; expected {version}")
    machine = platform.machine().lower()
    arch = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(machine, machine)
    os_name = {'Darwin': 'macos', 'Linux': 'linux', 'Windows': 'windows'}[platform.system()]
    downloads = json.loads((ROOT / 'zig-downloads.json').read_text())
    artifact = downloads[version][f'{arch}-{os_name}']
    with tempfile.TemporaryDirectory(prefix='.zig-install-', dir=ROOT) as directory:
        temporary = Path(directory)
        archive = temporary / artifact['tarball'].rsplit('/', 1)[1]
        urllib.request.urlretrieve(artifact['tarball'], archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != artifact['shasum']:
            raise RuntimeError('Zig download checksum mismatch')
        extracted = temporary / 'extracted'
        shutil.unpack_archive(str(archive), str(extracted))
        toolchain, = extracted.iterdir()
        shutil.move(str(toolchain), str(destination))
    return destination / executable


if __name__ == '__main__':
    print(install())
