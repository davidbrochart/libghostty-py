"VT serialization helpers. The source terminal is never mutated."
import re

from ._ffi import ffi, lib, check, GhosttyError
from .core import Terminal, read_bytes


def _format(t, *, emit=None, unwrap=True, **extras):
    formatter = ffi.new('GhosttyFormatter*')
    check(lib.ghostty_formatter_terminal_new(ffi.NULL, formatter, t._t[0]), 'formatter_new')
    try:
        flags = 0
        for name, value in extras.items():
            if value: flags |= getattr(lib, f'GHOSTTY_FORMATTER_EXTRA_{name.upper()}')
        for option, ctype, value in (
            ('EMIT', 'GhosttyFormatterFormat', lib.GHOSTTY_FORMATTER_FORMAT_VT if emit is None else emit),
            ('UNWRAP', 'bool', unwrap), ('TRIM', 'bool', False),
            ('EXTRAS', 'GhosttyFormatterExtras', flags),
        ):
            check(lib.ghostty_formatter_set(formatter[0], getattr(lib, f'GHOSTTY_FORMATTER_OPT_{option}'),
                  ffi.new(ctype+'*', value)), f'formatter {option}')
        return read_bytes(lambda b,n,out: lib.ghostty_formatter_format_buf(formatter[0], b, n, out))
    finally:
        lib.ghostty_formatter_free(formatter[0])


def _extras(t, content, *, before=False, **extras):
    # The C formatter has no content=none option. Its before/after extras
    # surround the exact same content; isolate them without parsing VT data.
    data = _format(t, **extras)
    if before:
        if not data.endswith(content): raise GhosttyError('unexpected formatter prefix')
        return data[:len(data)-len(content)] if content else data
    if not data.startswith(content): raise GhosttyError('unexpected formatter suffix')
    return data[len(content):]


def _screen(t, palette):
    content = _format(t)
    prefix = _extras(t, content, before=True, palette=palette, tabstops=True)
    modes = _extras(t, content, before=True, modes=True)
    # Screen selection is handled explicitly after restoring the primary.
    modes = re.sub(rb'\x1b\[\?(?:47|1047|1048|1049)[hl]', b'', modes)
    state = _extras(t, content, scrolling_region=True, keyboard=True, pwd=True)
    if t.mode(69): state = b'\x1b[?69h' + state
    cursor = _extras(t, content, cursor=True, style=True, hyperlink=True,
                     protection=True, kitty_keyboard=True, charsets=True)
    if t.mode(6):
        vertical = re.search(rb'\x1b\[(\d+);(\d+)r', state)
        horizontal = re.search(rb'\x1b\[(\d+);(\d+)s', state) if t.mode(69) else None
        top = int(vertical[1]) - 1 if vertical else 0
        left = int(horizontal[1]) - 1 if horizontal else 0
        cursor = re.sub(rb'\x1b\[(\d+);(\d+)H',
                        lambda m: f'\x1b[{int(m[1])-top};{int(m[2])-left}H'.encode(), cursor, count=1)
    return prefix + content + state + modes + cursor


def _primary_clone(t):
    snapshot = read_bytes(lambda b,n,out: lib.ghostty_snapshot_encode_buf(t._t[0], b, n, out), 'snapshot')
    decoder = ffi.new('GhosttySnapshotDecoder*')
    handle = ffi.new('GhosttyTerminal*')
    check(lib.ghostty_snapshot_decoder_new_buf(ffi.NULL, decoder, snapshot, len(snapshot)), 'snapshot_decoder_new')
    try:
        check(lib.ghostty_snapshot_decoder_decode(decoder[0], handle), 'snapshot_decode')
    finally:
        lib.ghostty_snapshot_decoder_free(decoder[0])
    clone = object.__new__(Terminal)
    clone._adopt(handle)
    try:
        # Only the alternate screen may change while cancelling an unfinished
        # UTF-8/VT sequence. The primary screen being exported stays untouched.
        clone.feed(b'\x18' + (b'\x1b[?1049l' if t.mode(1049) else b'\x1b[?47l'))
        return clone
    except BaseException:
        clone.close()
        raise


def serialize(t, palette):
    continuation = b'' if t.get('vt_ground', 'bool') else read_bytes(
        lambda b,n,out: lib.ghostty_terminal_continuation_buf(t._t[0], b, n, out), 'continuation')
    alternate = t.get('active_screen', 'GhosttyTerminalScreen') == lib.GHOSTTY_TERMINAL_SCREEN_ALTERNATE
    result = b'\x18\x1bc'
    if alternate:
        with _primary_clone(t) as primary:
            result += _screen(primary, palette)
            modes = _extras(primary, _format(primary), before=True, modes=True)
            modes = re.sub(rb'\x1b\[\?(?:47|1047|1048|1049)[hl]', b'', modes)
            defaults = re.sub(rb'(\x1b\[\??\d+)([hl])',
                              lambda m: m[1] + (b'l' if m[2] == b'h' else b'h'), modes)
        # Match the active screen mode, including 1049 cursor save/restore.
        entry = 1049 if t.mode(1049) else 1047 if t.mode(1047) else 47
        result += f'\x1b[?{entry}h'.encode()
        # Rendering assumes default modes/styles. Save the primary cursor
        # first, then neutralize state inherited on entering the alternate.
        result += defaults + b'\x1b[0m\x1b[r\x1b]8;;\x1b\\\x1b(B\x0f\x1b[2J\x1b[H'
    result += _screen(t, palette)
    return result + continuation
