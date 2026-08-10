from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


WIDTH = 32
HEIGHT = 32
WEST = 104.0
NORTH = 31.0
PIXEL_SIZE = 0.0001
EXPECTED_SIZE = 1384
EXPECTED_SHA256 = "6AD2C14C444B8FB47FD8F3FC5BEE3550B0425B32D13CB0E9021A8130E8176AD1"


def _inline_short(value: int) -> bytes:
    return struct.pack("<H", value) + b"\x00\x00"


def _inline_long(value: int) -> bytes:
    return struct.pack("<I", value)


def build_geotiff() -> bytes:
    pixel_scale = struct.pack("<3d", PIXEL_SIZE, PIXEL_SIZE, 0.0)
    tiepoint = struct.pack("<6d", 0.0, 0.0, 0.0, WEST, NORTH, 0.0)
    geokeys = struct.pack(
        "<20H",
        1,
        1,
        0,
        4,
        1024,
        0,
        1,
        2,
        1025,
        0,
        1,
        1,
        2048,
        0,
        1,
        4326,
        2054,
        0,
        1,
        9102,
    )
    x_resolution = struct.pack("<2I", 72, 1)
    y_resolution = struct.pack("<2I", 72, 1)

    tag_count = 18
    ifd_offset = 8
    ifd_size = 2 + tag_count * 12 + 4
    extras_offset = ifd_offset + ifd_size
    if extras_offset % 8:
        extras_offset += 8 - extras_offset % 8

    pixel_scale_offset = extras_offset
    tiepoint_offset = pixel_scale_offset + len(pixel_scale)
    geokeys_offset = tiepoint_offset + len(tiepoint)
    x_resolution_offset = geokeys_offset + len(geokeys)
    y_resolution_offset = x_resolution_offset + len(x_resolution)
    strip_offset = y_resolution_offset + len(y_resolution)

    entries = [
        (256, 4, 1, _inline_long(WIDTH)),
        (257, 4, 1, _inline_long(HEIGHT)),
        (258, 3, 1, _inline_short(8)),
        (259, 3, 1, _inline_short(1)),
        (262, 3, 1, _inline_short(1)),
        (273, 4, 1, _inline_long(strip_offset)),
        (274, 3, 1, _inline_short(1)),
        (277, 3, 1, _inline_short(1)),
        (278, 4, 1, _inline_long(HEIGHT)),
        (279, 4, 1, _inline_long(WIDTH * HEIGHT)),
        (282, 5, 1, _inline_long(x_resolution_offset)),
        (283, 5, 1, _inline_long(y_resolution_offset)),
        (284, 3, 1, _inline_short(1)),
        (296, 3, 1, _inline_short(2)),
        (339, 3, 1, _inline_short(1)),
        (33550, 12, 3, _inline_long(pixel_scale_offset)),
        (33922, 12, 6, _inline_long(tiepoint_offset)),
        (34735, 3, 20, _inline_long(geokeys_offset)),
    ]

    header = b"II" + struct.pack("<H", 42) + struct.pack("<I", ifd_offset)
    ifd = bytearray(struct.pack("<H", tag_count))
    for tag, field_type, count, value_or_offset in entries:
        ifd.extend(struct.pack("<HHI", tag, field_type, count))
        ifd.extend(value_or_offset)
    ifd.extend(struct.pack("<I", 0))

    prefix = header + bytes(ifd)
    prefix += b"\x00" * (extras_offset - len(prefix))
    pixels = bytes(
        ((row * WIDTH + column) % 251) + 1
        for row in range(HEIGHT)
        for column in range(WIDTH)
    )
    return prefix + pixel_scale + tiepoint + geokeys + x_resolution + y_resolution + pixels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")

    payload = build_geotiff()
    digest = hashlib.sha256(payload).hexdigest().upper()
    if len(payload) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise RuntimeError("canonical fixture bytes do not match the frozen identity")

    with output.open("xb") as stream:
        stream.write(payload)

    print(json.dumps({"path": str(output), "sha256": digest, "size": len(payload)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
