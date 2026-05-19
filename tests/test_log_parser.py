import struct

from portainer_cli.client import LogStreamParser


def _frame(stream_type: int, content: bytes) -> bytes:
    header = struct.pack(">BxxxI", stream_type, len(content))
    return header + content


def test_single_frame():
    parser = LogStreamParser()
    data = _frame(1, b"hello\n")
    parser.feed(data)
    frames = parser.frames()
    assert frames == [(1, b"hello\n")]


def test_multiple_frames():
    parser = LogStreamParser()
    data = _frame(1, b"stdout\n") + _frame(2, b"stderr\n")
    parser.feed(data)
    frames = parser.frames()
    assert frames == [(1, b"stdout\n"), (2, b"stderr\n")]


def test_partial_frame_buffered():
    parser = LogStreamParser()
    header = struct.pack(">BxxxI", 1, 10)
    parser.feed(header + b"abc")
    assert parser.frames() == []
    parser.feed(b"defghij")
    frames = parser.frames()
    assert frames == [(1, b"abcdefghij")]


def test_flush_remaining():
    parser = LogStreamParser()
    parser.feed(b"hello")
    frames = parser.flush()
    assert frames == [(1, b"hello")]


def test_flush_empty():
    parser = LogStreamParser()
    frames = parser.flush()
    assert frames == []
