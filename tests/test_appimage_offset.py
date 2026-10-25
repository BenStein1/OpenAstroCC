#!/usr/bin/env python3
"""Pure offline checks of the AppImage SquashFS offset scanner."""
import struct
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from appimage_offset import squashfs_offset


class SquashFSTests(unittest.TestCase):
    def test_validated_offset_skips_wrong_magic(self):
        fake = bytearray(b"\x7fELF" + b"x" * 127)
        fake.extend(b"hsqs" + b"x" * 25)
        offset = len(fake)
        header = bytearray(96)
        header[:4] = b"hsqs"
        struct.pack_into("<I", header, 12, 131072)
        struct.pack_into("<H", header, 20, 6)  # zstd
        struct.pack_into("<HH", header, 28, 4, 0)
        struct.pack_into("<Q", header, 40, 96)
        fake.extend(header)
        with tempfile.TemporaryDirectory() as dirname:
            image = Path(dirname) / "tool.AppImage"
            image.write_bytes(fake)
            self.assertEqual(squashfs_offset(image), offset)
            image.write_bytes(b"\x7fELF" + b"hsqs" + bytes(200))
            with self.assertRaises(ValueError):
                squashfs_offset(image)


if __name__ == "__main__":
    unittest.main()
