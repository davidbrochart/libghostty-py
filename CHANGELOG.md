<!-- do not remove -->

## 0.2.0 — libghostty-py

- Update the bindings and bundled library to Ghostty 1.4.0 (Zig 0.17.0),
  matching conda-forge libghostty-vt. Adapt ground-boundary writes and VT
  serialization to the updated API and formatter behavior.
- Support Python-only wheels with `--config-settings=bundle=false` and find
  separately installed shared libraries in the active Python environment.
- Pin bundled Ghostty builds to a release version and validate its Git tag.

## 0.1.0 — libghostty-py

- Fork pyghostty as the `libghostty-py` package, preserving its history and licenses.
- Include terminal-state serialization and Windows x64 wheel builds.

The entries below describe the original pyghostty releases.

## 0.1.0

### New Features

- Build and publish Zig-backed wheels ([#2](https://github.com/AnswerDotAI/pyghostty/pull/2)), thanks to [@jph00](https://github.com/jph00)
- Add style readback API ([#1](https://github.com/AnswerDotAI/pyghostty/issues/1))

### Bugs Squashed

- Install the bundled library into platlib ([#5](https://github.com/AnswerDotAI/pyghostty/pull/5)), thanks to [@jph00](https://github.com/jph00)
- Pass Ghostty source into Linux wheel builds ([#4](https://github.com/AnswerDotAI/pyghostty/pull/4)), thanks to [@jph00](https://github.com/jph00)
- Build wheels with Python 3.11 ([#3](https://github.com/AnswerDotAI/pyghostty/pull/3)), thanks to [@jph00](https://github.com/jph00)
