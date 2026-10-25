#!/usr/bin/env python3
"""Locate the validated embedded SquashFS of a type-2 AppImage.

Used ONLY if local AppImageLauncher prevents appimagetool's own runtime from
starting. This script reads bytes; it does not execute arbitrary downloaded
AppImages. External 'unsquashfs' still handles the filesystem extraction.
"""
import mmap
from pathlib import Path
import struct
import sys


def squashfs_offset(path):
    with open(path, "rb") as fh:
        if fh.read(4) != b"\x7fELF":
            raise ValueError("Expected an AppImage ELF executable")
        fh.seek(0)
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as data:
            size = len(data)
            offset = 0
            while True:
                offset = data.find(b"hsqs", offset)
                if offset == -1:
                    break
                # SquashFS v4 superblock is little-endian, 96+ bytes.
                if offset + 96 <= size:
                    compression = struct.unpack_from("<H", data, offset + 20)[0]
                    major, minor = struct.unpack_from("<HH", data, offset + 28)
                    used = struct.unpack_from("<Q", data, offset + 40)[0]
                    block_size = struct.unpack_from("<I", data, offset + 12)[0]
                    if (major, minor) == (4, 0) and 1 <= compression <= 6 and (
                            block_size >= 4096 and block_size <= 1048576 and
                            block_size & (block_size - 1) == 0) and (
                            96 <= used <= size - offset):
                        return offset
                offset += 4
    raise ValueError("No valid embedded SquashFS v4 filesystem found")


if __name__ == "__main__":
    try:
        print(squashfs_offset(Path(sys.argv[1])))
    except (OSError, ValueError, IndexError) as exc:
        print("Cannot locate AppImage filesystem: " + str(exc), file=sys.stderr)
        sys.exit(2)
