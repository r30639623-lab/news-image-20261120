#!/usr/bin/env python3
"""Entry program for make.fun bounty news-image-20261120.

Copies the pre-rendered image news.png (kept in this repository)
to /output/entry.png. Standard library only, no network access,
fully deterministic: the same input bytes always produce the
same output bytes.

Run:  python3 main.py
"""
import os
import shutil
import struct

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news.png")
DEST_DIR = "/output"
DEST = os.path.join(DEST_DIR, "entry.png")
MAX_BYTES = 1024 * 1024  # 1 MiB


def check_png(path):
    """Verify the file is a 1024x1024 PNG and within the size limit."""
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise SystemExit(f"entry too large: {size} bytes (limit {MAX_BYTES})")
    with open(path, "rb") as fh:
        header = fh.read(33)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("entry is not a PNG file")
    width, height = struct.unpack(">II", header[16:24])
    if (width, height) != (1024, 1024):
        raise SystemExit(f"entry is {width}x{height}, expected 1024x1024")
    return size, width, height


def main():
    if not os.path.exists(SOURCE):
        raise SystemExit(f"missing source image: {SOURCE}")
    os.makedirs(DEST_DIR, exist_ok=True)
    shutil.copyfile(SOURCE, DEST)
    # A plain byte copy: running this twice writes identical bytes,
    # so the two grader runs always agree.
    if os.path.getsize(SOURCE) != os.path.getsize(DEST):
        raise SystemExit("copy incomplete: size mismatch")
    size, width, height = check_png(DEST)
    print(f"Wrote {DEST}: {width}x{height}, {size} bytes")


if __name__ == "__main__":
    main()
