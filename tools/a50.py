#!/usr/bin/env python3
"""Astro A50 Gen 3 (USB 9886:0015) — read-only inventory, passive HID listener,
and offline .astroeq decoding.

This tool NEVER writes to the headset. There is no code path here that opens a
hidraw node for writing, and none that sends a report. That is deliberate: the
response framing is evidenced (docs/FINDINGS.md §4-5) but the valid ranges and
most opcode meanings are not, so writes would be guesswork. Don't add one until
the gaps in FINDINGS.md §7 are closed.

Subcommands:
  inventory   identify the device and its audio topology from sysfs/procfs
  listen      passively read HID input reports and decode their framing
  eq          decode a .astroeq preset into the device's on-wire representation
  selftest    assert the decoders behave (no hardware needed)
"""

import configparser
import glob
import os
import sys

VID, PID = 0x9886, 0x0015
HID_ID = "0003:%08X:%08X" % (VID, PID)
REPORT_ID = 0x02

# The HID report descriptor declares 63 data bytes, so a report is 64 on the
# wire including the report ID. Two of those data bytes are the command header
# (opcode, len|seq), which leaves 61 for payload -- 60 when a high-bit opcode
# inserts the 0x0a extended marker. The 6-bit length field would allow 63, but
# report capacity is the tighter constraint and the one that actually binds.
REPORT_LEN = 64
MAX_PAYLOAD = 61
MAX_PAYLOAD_EXTENDED = 60

# Opcodes with direct evidence. Everything else in 0x60..0x7c is real but
# unidentified -- see docs/FINDINGS.md §7. Absent here means "unknown", never
# "doesn't exist".
OPCODES = {
    0x63: "RW_EQ_GAINS",
    0x64: "RW_EQ_FREQS",
    0x66: "SET_NOISEGATE",
    0x68: "SET_SIDETONE",
}


# --- protocol framing (docs/FINDINGS.md §4) --------------------------------

def frame(cmd, payload):
    """Build a 64-byte report per the evidenced KUIPER framing.

    Used by selftest and to document the format executably. Intentionally not
    wired to any transmit path.
    """
    if not 0 <= cmd <= 0xFF:
        raise ValueError("cmd out of range: %r" % cmd)
    extended = bool(cmd & 0x80)
    limit = MAX_PAYLOAD_EXTENDED if extended else MAX_PAYLOAD
    if len(payload) > limit:
        raise ValueError(
            "payload %d bytes exceeds report capacity (%d max%s)"
            % (len(payload), limit, " for an extended opcode" if extended else ""))
    length = len(payload) + (1 if extended else 0)
    body = bytes([cmd, length]) + (b"\x0a" if extended else b"") + bytes(payload)
    report = (bytes([REPORT_ID]) + body).ljust(REPORT_LEN, b"\x00")
    assert len(report) == REPORT_LEN, len(report)  # capacity check must hold
    return report


def unframe(report):
    """Decode a report read from hidraw into (cmd, seq, payload).

    Returns None if the leading byte isn't the report ID this device declares,
    so an unexpected report shape is visible rather than silently misparsed.
    """
    if len(report) < 3 or report[0] != REPORT_ID:
        return None
    cmd = report[1]
    length = report[2] & 0x3F
    seq = report[2] >> 6
    start = 3 + (1 if cmd & 0x80 else 0)
    if cmd & 0x80:
        length = max(0, length - 1)
    return cmd, seq, bytes(report[start:start + length])


# --- .astroeq (docs/FINDINGS.md §5) ----------------------------------------

BANDS, BANDWIDTH_BANDS = 5, (2, 3, 4)
# Bandwidth is in octaves, stored on the device as 4.12 fixed point. The app
# reads it as round(raw / 4096 * 10) -- i.e. tenths of an octave -- which is why
# .astroeq files carry one decimal place (0.5, 1, 1.6, 2).
BANDWIDTH_FIXED_ONE = 4096


def bandwidth_to_raw(octaves):
    return int(round(octaves * BANDWIDTH_FIXED_ONE))


def bandwidth_from_raw(raw):
    return round(raw / BANDWIDTH_FIXED_ONE * 10) / 10


def load_astroeq(path):
    """Parse a .astroeq preset (plain QSettings INI) into a dict."""
    cp = configparser.ConfigParser()
    cp.optionxform = str  # QSettings keys are case-sensitive
    with open(path, encoding="utf-8-sig") as fh:
        cp.read_file(fh)
    eq = cp["Eq_Bands"]
    return {
        "name": cp.get("General", "Name", fallback=os.path.basename(path)),
        "gains": [int(eq["Eq_Band_%d" % i]) for i in range(1, BANDS + 1)],
        "freqs": [int(eq["Eq_Freq_Band_%d" % i]) for i in range(1, BANDS + 1)],
        # Octaves, written by Qt as "2", "2.0" or "1.6" depending on the value.
        "bandwidths": {i: float(eq["Eq_Bandwidth_%d" % i]) for i in BANDWIDTH_BANDS},
    }


def encode_eq(preset):
    """Render a preset into the device's numeric encoding.

    Gains are signed bytes; frequencies little-endian uint16 Hz; bandwidths
    4.12 fixed point. This is the encoding the device's *read* responses were
    proven to use; the write payload layout is NOT established, so this returns
    fields rather than a ready-to-send packet.
    """
    return {
        "gains": bytes((g & 0xFF) for g in preset["gains"]),
        "freqs": b"".join(f.to_bytes(2, "little") for f in preset["freqs"]),
        "bandwidths": {
            band: bandwidth_to_raw(v).to_bytes(2, "little")
            for band, v in preset["bandwidths"].items()
        },
    }


# --- hardware discovery (read-only) ----------------------------------------

def find_hidraw():
    """Return the hidraw path for the A50 control interface, or None."""
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(node, "device/uevent")) as fh:
                uevent = fh.read()
        except OSError:
            continue
        if HID_ID in uevent.upper():
            return "/dev/" + os.path.basename(node)
    return None


def find_usb_sysfs():
    for path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
        base = os.path.dirname(path)
        try:
            with open(path) as fh:
                vid = fh.read().strip()
            with open(os.path.join(base, "idProduct")) as fh:
                pid = fh.read().strip()
        except OSError:
            continue
        if int(vid, 16) == VID and int(pid, 16) == PID:
            return base
    return None


def read_first(path, default=""):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return default


def cmd_inventory(_args):
    base = find_usb_sysfs()
    if not base:
        print("A50 (%04x:%04x) not connected." % (VID, PID))
        return 1
    print("device      : %04x:%04x  %s / %s" % (
        VID, PID,
        read_first(base + "/manufacturer", "?"),
        read_first(base + "/product", "?")))
    print("sysfs       : %s" % base)
    print("usb speed   : %s Mbps" % read_first(base + "/speed", "?"))

    print("\ninterfaces:")
    for iface in sorted(glob.glob(base + "/*:1.*")):
        cls = read_first(iface + "/bInterfaceClass")
        name = read_first(iface + "/interface")
        kind = {"01": "audio", "03": "HID"}.get(cls, "class " + cls)
        print("  %-10s %-6s %s" % (os.path.basename(iface), kind, name or "-"))

    hidraw = find_hidraw()
    print("\ncontrol     : %s" % (hidraw or "no hidraw node found"))
    if hidraw:
        writable = os.access(hidraw, os.R_OK)
        print("readable    : %s" % ("yes" if writable else "no (check permissions)"))

    # Which ALSA card, and what each PCM really is. Named by the USB interface
    # strings, so Game/Voice is read off the device, not guessed.
    for card in sorted(glob.glob("/proc/asound/card*/stream*")):
        text = read_first(card)
        if "Astro A50" not in text:
            continue
        print("\n%s:" % card)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("Playback", "Capture", "Channels:",
                                    "Channel map:", "Rates:", "Interface ",
                                    "Format:")):
                print("  " + stripped)
    return 0


def cmd_listen(args):
    """Passively read input reports. Opens O_RDONLY -- cannot write."""
    path = args.device or find_hidraw()
    if not path:
        print("A50 control interface not found.", file=sys.stderr)
        return 1
    print("listening on %s (read-only, Ctrl-C to stop)" % path)
    print("press/flip the headset controls now; see docs/HARDWARE-TESTS.md\n")
    try:
        fd = os.open(path, os.O_RDONLY)
    except PermissionError:
        print("permission denied on %s" % path, file=sys.stderr)
        return 1
    count = 0
    try:
        while True:
            data = os.read(fd, 64)
            if not data:
                continue
            count += 1
            decoded = unframe(data)
            stamp = "[%04d]" % count
            if decoded:
                cmd, seq, payload = decoded
                print("%s cmd=0x%02x (%s) seq=%d len=%d payload=%s" % (
                    stamp, cmd, OPCODES.get(cmd, "unknown"), seq,
                    len(payload), payload.hex(" ") or "-"))
            else:
                print("%s unrecognised report shape" % stamp)
            print("%s raw: %s" % (" " * len(stamp), data.hex(" ")))
    except KeyboardInterrupt:
        print("\nstopped after %d report(s)." % count)
        if count == 0:
            print("No reports received. If controls were used, that is itself a")
            print("result: this device does not push HID events for them.")
    finally:
        os.close(fd)
    return 0


def cmd_eq(args):
    preset = load_astroeq(args.path)
    enc = encode_eq(preset)
    print("preset: %s" % preset["name"])
    print("\n%-6s %8s %8s %10s" % ("band", "gain dB", "freq Hz", "bw oct"))
    for i in range(BANDS):
        band = i + 1
        bw = preset["bandwidths"].get(band)
        print("%-6d %8d %8d %10s" % (
            band, preset["gains"][i], preset["freqs"][i],
            bw if bw is not None else "-"))
    print("\ndevice encoding (docs/FINDINGS.md §5):")
    print("  gains (int8 x5)      : %s" % enc["gains"].hex(" "))
    print("  freqs (LE u16 x5)    : %s" % enc["freqs"].hex(" "))
    for band, raw in sorted(enc["bandwidths"].items()):
        print("  bandwidth band %d     : %s (raw %d, 4.12 fixed)" % (
            band, raw.hex(" "), int.from_bytes(raw, "little")))
    print("\nRead-request packets for slot 0 (built, not sent):")
    for cmd, label in ((0x63, "gains"), (0x64, "freqs")):
        for page in (0, 1):
            pkt = frame(cmd, bytes([page, 0]))
            print("  %-6s page %d: %s" % (label, page, pkt[:8].hex(" ") + " ..."))
    return 0


def cmd_selftest(_args):
    # Framing, per FINDINGS.md §4.
    pkt = frame(0x63, bytes([0x00, 0x01]))
    assert len(pkt) == 64, len(pkt)
    assert pkt[0] == REPORT_ID
    assert pkt[1] == 0x63
    assert pkt[2] & 0x3F == 2, "length lives in the low 6 bits"
    assert pkt[3:5] == bytes([0x00, 0x01])
    assert pkt[5:] == b"\x00" * 59, "must be zero-padded to the report length"

    # Extended form: high-bit opcode inserts 0x0a and bumps the length.
    ext = frame(0xDA, bytes([0x07]))
    assert ext[2] & 0x3F == 2, "extended length counts the 0x0a byte"
    assert ext[3] == 0x0A
    assert ext[4] == 0x07

    # unframe must invert frame for both forms.
    assert unframe(frame(0x68, b"\x00\x20")) == (0x68, 0, b"\x00\x20")
    assert unframe(frame(0xDA, b"\x07")) == (0xDA, 0, b"\x07")
    # A report that isn't ours must be rejected, not misparsed.
    assert unframe(b"\x01" + b"\x00" * 63) is None

    # Payload capacity is bounded by the report, not by the 6-bit length field.
    # 61 bytes is the largest that fits; 62 must be refused even though the
    # length field could encode it.
    assert len(frame(0x63, b"\x00" * MAX_PAYLOAD)) == REPORT_LEN
    assert frame(0x63, b"\x00" * MAX_PAYLOAD)[2] & 0x3F == MAX_PAYLOAD
    for cmd, too_big in ((0x63, MAX_PAYLOAD + 1), (0xDA, MAX_PAYLOAD_EXTENDED + 1)):
        try:
            frame(cmd, b"\x00" * too_big)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "payload of %d must be rejected for cmd 0x%02x" % (too_big, cmd))
    # An extended opcode loses one more byte to the 0x0a marker.
    assert len(frame(0xDA, b"\x00" * MAX_PAYLOAD_EXTENDED)) == REPORT_LEN

    # Bandwidth round-trip across the range the shipped presets actually use
    # (0.5-2.0 octaves, one decimal place).
    for tenths in range(1, 21):
        octaves = tenths / 10
        assert bandwidth_from_raw(bandwidth_to_raw(octaves)) == octaves, octaves
    assert bandwidth_to_raw(2.0) == 8192
    assert bandwidth_to_raw(0.5) == 2048

    # Frequencies are little-endian uint16.
    assert (7001).to_bytes(2, "little") == b"\x59\x1b"

    # Negative gains must survive as signed bytes.
    enc = encode_eq({"gains": [-5, 0, 6, 7, -4], "freqs": [90] * 5,
                     "bandwidths": {2: 2}})
    assert enc["gains"] == bytes([0xFB, 0x00, 0x06, 0x07, 0xFC]), enc["gains"].hex()

    # Parse the real shipped presets if preserved, and check the schema the
    # decompiled reader implies: 5 gains, 5 freqs, 3 bandwidths for bands 2-4.
    here = os.path.dirname(os.path.abspath(__file__))
    presets = glob.glob(os.path.join(
        here, "..", "artifacts", "classic-acc", "assets",
        "Astro A50 Wireless", "Astro EQ", "*.astroeq"))
    for path in presets:
        preset = load_astroeq(path)
        assert len(preset["gains"]) == BANDS
        assert len(preset["freqs"]) == BANDS
        assert set(preset["bandwidths"]) == set(BANDWIDTH_BANDS), preset["bandwidths"]
        assert all(-128 <= g <= 127 for g in preset["gains"]), preset["gains"]
        assert all(0 < f <= 0xFFFF for f in preset["freqs"]), preset["freqs"]
        assert preset["freqs"] == sorted(preset["freqs"]), "bands ascend in frequency"
        # Every shipped bandwidth must survive the fixed-point round-trip and
        # fit 4.12, or the encoding model is wrong.
        for band, octaves in preset["bandwidths"].items():
            raw = bandwidth_to_raw(octaves)
            assert 0 < raw <= 0xFFFF, (path, band, raw)
            assert bandwidth_from_raw(raw) == octaves, (path, band, octaves)
    print("selftest OK (framing, encoding and fixed-point assertions passed; "
          "%d shipped preset(s) parsed)" % len(presets))
    if not presets:
        print("note: artifacts/ not present, preset schema checks skipped")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", help="identify device and audio topology")
    listen = sub.add_parser("listen", help="passively read HID input reports")
    listen.add_argument("-d", "--device", help="hidraw path (default: autodetect)")
    eq = sub.add_parser("eq", help="decode a .astroeq preset")
    eq.add_argument("path")
    sub.add_parser("selftest", help="run offline assertions")
    args = parser.parse_args()
    return {"inventory": cmd_inventory, "listen": cmd_listen,
            "eq": cmd_eq, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
