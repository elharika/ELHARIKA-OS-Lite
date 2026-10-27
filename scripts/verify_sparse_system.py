#!/usr/bin/env python3
"""Validate the entire Android sparse system image, bounds and checksum.

Structural check only. Does not establish filesystem validity or flash safety.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

MAGIC = 0xED26FF3A
RAW, FILL, DONT_CARE, CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4
MAX_EXPANDED = 2_300_000_000

def validate(path):
    path = Path(path)
    file_size = path.stat().st_size
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        def read_exact(n):
            data = stream.read(n)
            if len(data) != n:
                raise ValueError("Truncated sparse system image")
            digest.update(data)
            return data
        magic, major, minor, file_hdr, chunk_hdr, block_size, blocks, count, checksum = struct.unpack(
            "<I4H4I", read_exact(28))
        if magic != MAGIC or major != 1 or file_hdr < 28 or chunk_hdr < 12:
            raise ValueError("Invalid Android sparse header")
        if block_size == 0 or block_size % 4 or not blocks or not count:
            raise ValueError("Invalid sparse block geometry")
        expanded = blocks * block_size
        if expanded > MAX_EXPANDED:
            raise ValueError("Expanded image exceeds pinned SM-P900 partition bound")
        read_exact(file_hdr - 28)
        seen = 0
        for index in range(count):
            kind, reserved, chunk_blocks, total_size = struct.unpack("<2H2I", read_exact(12))
            if reserved or not chunk_blocks and kind != CRC32 or total_size < chunk_hdr:
                raise ValueError(f"Invalid chunk header {index}")
            read_exact(chunk_hdr - 12)
            payload = total_size - chunk_hdr
            if kind == RAW:
                expected = chunk_blocks * block_size
            elif kind in (FILL, CRC32):
                expected = 4
            elif kind == DONT_CARE:
                expected = 0
            else:
                raise ValueError(f"Unknown sparse chunk kind {kind:#x}")
            if payload != expected or kind == CRC32 and chunk_blocks:
                raise ValueError(f"Invalid sparse chunk length {index}")
            seen += chunk_blocks
            if seen > blocks:
                raise ValueError("Sparse chunks exceed declared blocks")
            remaining = payload
            while remaining:
                chunk = read_exact(min(remaining, 1024 * 1024))
                remaining -= len(chunk)
        if seen != blocks or stream.tell() != file_size:
            raise ValueError("Sparse block count or trailing bytes mismatch")
    return {"status": "SPARSE_STRUCTURE_VALID_NOT_HARDWARE_TESTED", "size": file_size,
            "expanded_size": expanded, "sha256": digest.hexdigest(),
            "flash_approved": False, "filesystem_verified": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    args.report.write_text(json.dumps(validate(args.image), indent=2) + "\n")

if __name__ == "__main__":
    main()
