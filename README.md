# libghostty-py

This is a fork of [pyghostty](https://github.com/AnswerDotAI/pyghostty) (from [this commit](https://github.com/AnswerDotAI/pyghostty/commit/5abf31813fb3707fcded75d9521b03e3bdbdfee8)).

Python bindings for [libghostty-vt](https://github.com/ghostty-org/ghostty/tree/vt-1.0.0), Ghostty's embeddable terminal emulation core, a headless, high-fidelity VT emulator. These bindings cover terminal state, screen and scrollback snapshots, kitty graphics, and everything else Ghostty's production terminal core handles.

The binding is Python-ABI-independent: pure Python (cffi ABI mode) over a bundled `libghostty-vt` shared library, so one wheel per platform covers every Python version. No compiler is needed at install time. Wheel builds cover Linux and macOS (x86-64 and ARM64) and Windows (x86-64).

## Usage

```python
from ghostty import Terminal

with Terminal(cols=80, rows=24) as t:
    t.feed('hello\r\nworld')
    t.cursor      # (x, y), 0-indexed
    t.text()      # plain text of the visible screen only
    t.contents()  # everything: scrollback plus screen, soft-wraps unwrapped
    t.resize(120, 24)  # reflows the primary screen
```

The base layer, `ghostty._cdef`/`_ffi`, exposes the complete generated C API as raw `ffi`/`lib` (regenerate with `gen_cdef.py` after updating the pinned libghostty-vt release).

`ghostty.core.Terminal` provides an ergonomic wrapper for commonly used parts.

### Restoring a terminal on reconnect

`serialize()` returns **VT bytes**, rather than plain text or Ghostty's binary
snapshot format. Feed the result to a terminal with the same columns, rows, and character-width rules,
then forward subsequent PTY bytes in order:

```python
with Terminal(cols=80, rows=24) as t:
    t.feed(b"hello\r\n\x1b[31mprompt> ")
    initial_output = t.serialize()
    # Send initial_output to the reconnecting terminal before live PTY output.
```

The snapshot resets the destination and restores screen content, scrollback,
styles, cursor, modes, and the active alternate screen with its underlying primary
screen. Use `serialize(palette=True)` to also export the palette.

Snapshots may end with incomplete UTF-8 or VT sequences: send bytes directly, or
use a streaming decoder across the snapshot and live output. Serialize between
feeds/resizes and send the snapshot before subsequent output. Unfinished input is
limited by `continuation_limit` (1 MiB by default); exceeding it raises
`GhosttyError` until the sequence completes.

Graphics, titles, default colors, inactive alternate screens, and arbitrary saved
cursors are not exported. Rendering can differ between terminal emulators.

## Building the library

The shared library is built from a Ghostty checkout with Zig 0.17.0. Install
that Zig version on PATH, or download the pinned official toolchain with
`python install_zig.py` (downloads are verified against recorded SHA-256 hashes):

```bash
GHOSTTY_SRC=/path/to/ghostty python build_lib.py
```

Without `GHOSTTY_SRC`, the build looks for a checkout in `ghostty-src/` inside this project.

The checkout must be at the release tag for `vt-version` in `pyproject.toml`
(currently `vt-1.0.0`), with that tag available locally. This runs `zig build -Demit-lib-vt=true` and copies the resulting shared library into `ghostty/_lib/`, where the package loader and wheel builds pick it up.

### Using an external shared library

Wheel builds bundle libghostty-vt by default. To build a Python-only wheel
without compiling or bundling Ghostty, pass `--config-settings=bundle=false`:

```bash
python -m pip install . --config-settings=bundle=false
```

The resulting wheel is platform-independent and does not need Zig to build.
This also excludes any library left by an earlier bundled build.
The loader checks the bundled library, then the active Python environment
(`sys.prefix`):

- Linux: `lib/libghostty-vt.so`
- macOS: `lib/libghostty-vt.dylib`
- Windows: `Library/bin/ghostty-vt.dll`

Libraries installed in these locations are found automatically. The external
library must provide the ABI of libghostty-vt 1.0.0, pinned in `pyproject.toml`.

Bundled builds require Zig 0.17.0 on PATH or the local toolchain installed by
`python install_zig.py`. Release CI installs the verified toolchain before building.
The `bundle` setting accepts `true` or `false` and defaults to `true`.

## Development

```bash
pip install -e .[dev]
python install_zig.py
GHOSTTY_SRC=/path/to/ghostty python build_lib.py
pytest -q
```

To test against headless xterm.js:

```bash
npm install --prefix /tmp/libghostty-xterm @xterm/headless@6.0.0
LIBGHOSTTY_XTERM_MODULE=/tmp/libghostty-xterm/node_modules/@xterm/headless pytest -q
```

### Versioning

Version lives in `ghostty/__init__.py` as `__version__`.

### Releases

Pushing a `v*` tag runs `.github/workflows/release.yml`, which builds and tests one Python-ABI-independent wheel for each supported platform and publishes the wheels to GitHub and PyPI. Releases are wheel-only; source remains available from the corresponding GitHub tag.
