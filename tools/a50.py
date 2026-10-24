#!/usr/bin/env python3
"""Astro A50 Gen 3 (USB 9886:0015) — read-only inventory, passive HID listener,
offline .astroeq decoding, and one evidenced live EQ read.

This tool has exactly one path that writes to the headset: `eq-read`. It sends
only the KUIPER_RW_EQ_GAINS request (opcode 0x63, payload {page, slot}) that
the stock app itself issues at startup to read current EQ state back
(docs/FINDINGS.md §5), and validates the reply the same way the decompiled
app does (status byte, 2-bit sequence match -- docs/FINDINGS.md §14). There is
no generic/raw opcode argument and no settings-write path. Don't add one until
the gaps in FINDINGS.md §7 are closed.

Subcommands:
  inventory   identify the device and its audio topology from sysfs/procfs
  listen      passively read HID input reports and decode their framing
  eq          decode a .astroeq preset into the device's on-wire representation
  eq-read     send the evidenced EQ-gains read request and print the live reply
  selftest    assert the decoders behave (no hardware needed)
"""

import configparser
import glob
import math
import os
import select
import sys
import time

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

def frame(cmd, payload, seq=0):
    """Build a 64-byte report per the evidenced KUIPER framing.

    Used by selftest and to document the format executably. Intentionally not
    wired to any transmit path.
    """
    if not 0 <= cmd <= 0xFF:
        raise ValueError("cmd out of range: %r" % cmd)
    if type(seq) is not int or not 0 <= seq <= 3:
        raise ValueError("sequence must be an integer from 0 to 3")
    extended = bool(cmd & 0x80)
    limit = MAX_PAYLOAD_EXTENDED if extended else MAX_PAYLOAD
    if len(payload) > limit:
        raise ValueError(
            "payload %d bytes exceeds report capacity (%d max%s)"
            % (len(payload), limit, " for an extended opcode" if extended else ""))
    length = len(payload) + (1 if extended else 0)
    body = bytes([cmd, length | (seq << 6)]) + (b"\x0a" if extended else b"") + bytes(payload)
    report = (bytes([REPORT_ID]) + body).ljust(REPORT_LEN, b"\x00")
    assert len(report) == REPORT_LEN, len(report)  # capacity check must hold
    return report


def unframe(report):
    """Decode a report read from hidraw into (cmd, seq, payload).

    Returns None if the leading byte isn't the report ID this device declares,
    so an unexpected report shape is visible rather than silently misparsed.
    """
    if len(report) != REPORT_LEN or report[0] != REPORT_ID:
        return None
    cmd = report[1]
    length = report[2] & 0x3F
    seq = report[2] >> 6
    start = 3 + (1 if cmd & 0x80 else 0)
    if length > MAX_PAYLOAD:
        return None
    if cmd & 0x80:
        if length == 0 or report[3] != 0x0A:
            return None
        length -= 1
    return cmd, seq, bytes(report[start:start + length])


# --- .astroeq (docs/FINDINGS.md §5) ----------------------------------------

BANDS, BANDWIDTH_BANDS = 5, (2, 3, 4)
# Bandwidth is in octaves, stored on the device as 4.12 fixed point. The app
# reads it as round(raw / 4096 * 10) -- i.e. tenths of an octave -- which is why
# .astroeq files carry one decimal place (0.5, 1, 1.6, 2).
BANDWIDTH_FIXED_ONE = 4096


def bandwidth_to_raw(octaves):
    if not math.isfinite(octaves) or not 0 < octaves <= 0xFFFF / BANDWIDTH_FIXED_ONE:
        raise ValueError("bandwidth must be finite, positive and representable as uint16 4.12")
    raw = math.floor(octaves * BANDWIDTH_FIXED_ONE + 0.5)
    if raw == 0:
        raise ValueError("bandwidth rounds to zero")
    return raw


def bandwidth_from_raw(raw):
    return math.floor(raw / BANDWIDTH_FIXED_ONE * 10 + 0.5) / 10


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
    if len(preset["gains"]) != BANDS or len(preset["freqs"]) != BANDS:
        raise ValueError("a preset requires five gains and five frequencies")
    if set(preset["bandwidths"]) != set(BANDWIDTH_BANDS):
        raise ValueError("bandwidths are required for bands 2, 3 and 4")
    if any(type(g) is not int or not -128 <= g <= 127 for g in preset["gains"]):
        raise ValueError("gains must fit signed 8-bit integers")
    if any(type(f) is not int or not 0 <= f <= 0xFFFF for f in preset["freqs"]):
        raise ValueError("frequencies must fit unsigned 16-bit integers")
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
    except OSError as exc:
        print("cannot open %s: %s" % (path, exc), file=sys.stderr)
        return 1
    count = 0
    try:
        while True:
            data = os.read(fd, 64)
            if not data:
                print("HID input closed; stopping.", file=sys.stderr)
                return 1
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
            print("No unsolicited reports observed during this capture.")
            print("Polling or initialization may still be required to read controls.")
    except OSError as exc:
        print("HID read failed: %s" % exc, file=sys.stderr)
        return 1
    finally:
        os.close(fd)
    return 0


def _read_one_report(fd, timeout):
    """Block for one input report with a bounded, tool-chosen timeout.

    The app's own blocking read (FUN_00494b10's getReport call) has no
    traceable timeout in this binary -- ReadFile has zero call sites in this
    EXE, so that wait lives in a vendor HID backend outside this analysis
    pass (docs/FINDINGS.md §14). This timeout is ours, not evidenced from the
    device.
    """
    deadline = time.monotonic() + timeout
    remaining = deadline - time.monotonic()
    while remaining > 0:
        ready, _, _ = select.select([fd], [], [], remaining)
        if ready:
            return os.read(fd, REPORT_LEN)
        remaining = deadline - time.monotonic()
    raise TimeoutError("no reply within %.1fs" % timeout)


def query_eq_gains(path, slot, page, timeout=2.0):
    """Send the evidenced KUIPER_RW_EQ_GAINS read request for one slot/page
    and return the device's 5 signed-byte gains.

    This is the exact read the stock app performs at startup for every slot
    (docs/FINDINGS.md §5); nothing is written to any setting. Reply
    validation follows the decompiled FUN_00494b10/FUN_00479f70 chain: the
    reply's status byte must be 0x02 (anything else is an app-defined error
    packet) and its 2-bit sequence must match what we sent (§14). Raises
    OSError, TimeoutError or RuntimeError on any failure; never retries or
    guesses -- a mismatch is reported, not papered over.
    """
    if page not in (0, 1):
        raise ValueError("page must be 0 or 1")
    if slot not in (0, 1, 2):
        raise ValueError("slot must be 0, 1 or 2")
    seq = 0
    req = frame(0x63, bytes([page, slot]), seq)
    fd = os.open(path, os.O_RDWR)
    try:
        os.write(fd, req)
        reply = _read_one_report(fd, timeout)
    finally:
        os.close(fd)
    decoded = unframe(reply)
    if decoded is None:
        raise RuntimeError("malformed reply report: %s" % reply.hex(" "))
    status, reply_seq, payload = decoded
    if reply_seq != seq:
        raise RuntimeError(
            "sequence mismatch: sent seq=%d, device replied seq=%d (stray report?)"
            % (seq, reply_seq))
    if status != 0x02:
        raise RuntimeError(
            "device returned error status 0x%02x instead of success (0x02); "
            "payload=%s -- see docs/FINDINGS.md §14 for the error-packet layout"
            % (status, payload.hex(" ")))
    if len(payload) < 5:
        raise RuntimeError("reply payload too short for 5 gain bytes: %s" % payload.hex(" "))
    return [b if b < 128 else b - 256 for b in payload[:5]]


def cmd_eq_read(args):
    path = args.device or find_hidraw()
    if not path:
        print("A50 control interface not found.", file=sys.stderr)
        return 1
    try:
        gains = query_eq_gains(path, args.slot, args.page)
    except (OSError, TimeoutError, RuntimeError) as exc:
        print("eq-read failed: %s" % exc, file=sys.stderr)
        return 1
    print("slot %d page %d gains (dB, 5 bands): %s" % (args.slot, args.page, gains))
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
    for seq in range(4):
        assert unframe(frame(0x63, b"\x00\x01", seq)) == (0x63, seq, b"\x00\x01")
        assert unframe(frame(0xDA, b"\x07", seq)) == (0xDA, seq, b"\x07")
    for bad in (pkt[:-1], pkt + b"\x00", b"\x02\x63\x3f" + bytes(61),
                b"\x02\xda\x00" + bytes(61), b"\x02\xda\x01" + bytes(61)):
        assert unframe(bad) is None

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
    assert bandwidth_from_raw(1024) == 0.3, "match the app's roundf at half tenths"

    # Frequencies are little-endian uint16.
    assert (7001).to_bytes(2, "little") == b"\x59\x1b"

    # Negative gains must survive as signed bytes.
    enc = encode_eq({"gains": [-5, 0, 6, 7, -4], "freqs": [90] * 5,
                     "bandwidths": {2: 2, 3: 1.6, 4: 0.5}})
    assert enc["gains"] == bytes([0xFB, 0x00, 0x06, 0x07, 0xFC]), enc["gains"].hex()
    valid = {"gains": [0] * 5, "freqs": [90] * 5,
             "bandwidths": {2: 2, 3: 1.6, 4: 0.5}}
    for change in ({"gains": [128] * 5}, {"gains": [-129] * 5},
                   {"gains": [0] * 4}, {"freqs": [-1] * 5},
                   {"freqs": [65536] * 5}, {"freqs": [1.5] * 5},
                   {"bandwidths": {2: 1}},
                   *({"bandwidths": {2: v, 3: 1, 4: 1}}
                     for v in (float("nan"), float("inf"), -1, 0, 0.000001, 16))):
        try:
            encode_eq({**valid, **change})
        except ValueError:
            pass
        else:
            raise AssertionError("invalid preset accepted: %r" % change)

    # A vanished device must return failure and close its fd, never busy-loop.
    import contextlib
    import io
    from types import SimpleNamespace
    from unittest.mock import patch
    for read_result in ({"return_value": b""}, {"side_effect": OSError("disconnected")}):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch.object(os, "open", return_value=99), \
                patch.object(os, "read", **read_result) as read_mock, \
                patch.object(os, "close") as close_mock:
            assert cmd_listen(SimpleNamespace(device="/mock-hid")) == 1
            read_mock.assert_called_once_with(99, 64)
            close_mock.assert_called_once_with(99)

    # eq-read: validate the request bytes we send, and that we tell apart a
    # successful reply from a sequence mismatch and from an error status
    # (docs/FINDINGS.md §14 -- the decompiled FUN_00494b10/FUN_00479f70 chain).
    good_reply = frame(0x02, bytes([5, 253, 0, 7, 255]), seq=0)  # signed: 5, -3, 0, 7, -1
    with patch.object(os, "open", return_value=77) as open_mock, \
            patch.object(os, "write") as write_mock, \
            patch.object(select, "select", return_value=([77], [], [])), \
            patch.object(os, "read", return_value=good_reply), \
            patch.object(os, "close"):
        gains = query_eq_gains("/mock-hid", slot=1, page=0)
        open_mock.assert_called_once_with("/mock-hid", os.O_RDWR)
        sent = write_mock.call_args[0][1]
        assert sent[:5] == bytes([0x02, 0x63, 2, 0, 1]), sent[:5].hex(" ")  # cmd 0x63, len=2 seq=0, payload={page=0,slot=1}
        assert gains == [5, -3, 0, 7, -1], gains

    wrong_seq_reply = frame(0x02, b"\x00" * 5, seq=1)
    with patch.object(os, "open", return_value=77), patch.object(os, "write"), \
            patch.object(select, "select", return_value=([77], [], [])), \
            patch.object(os, "read", return_value=wrong_seq_reply), \
            patch.object(os, "close"):
        try:
            query_eq_gains("/mock-hid", slot=0, page=0)
        except RuntimeError as exc:
            assert "sequence mismatch" in str(exc), exc
        else:
            raise AssertionError("sequence mismatch must raise")

    error_reply = frame(0x7F, b"\x00" * 5, seq=0)
    with patch.object(os, "open", return_value=77), patch.object(os, "write"), \
            patch.object(select, "select", return_value=([77], [], [])), \
            patch.object(os, "read", return_value=error_reply), \
            patch.object(os, "close"):
        try:
            query_eq_gains("/mock-hid", slot=0, page=0)
        except RuntimeError as exc:
            assert "error status" in str(exc), exc
        else:
            raise AssertionError("non-0x02 status must raise")

    with patch.object(os, "open", return_value=77), patch.object(os, "write"), \
            patch.object(select, "select", return_value=([], [], [])), \
            patch.object(os, "close"):
        try:
            query_eq_gains("/mock-hid", slot=0, page=0, timeout=0.01)
        except TimeoutError:
            pass
        else:
            raise AssertionError("no reply must time out, not hang")

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
    eqread = sub.add_parser(
        "eq-read",
        help="send the evidenced EQ-gains read request and print the live reply")
    eqread.add_argument("-d", "--device", help="hidraw path (default: autodetect)")
    eqread.add_argument("--slot", type=int, choices=(0, 1, 2), required=True)
    eqread.add_argument("--page", type=int, choices=(0, 1), required=True)
    sub.add_parser("selftest", help="run offline assertions")
    args = parser.parse_args()
    return {"inventory": cmd_inventory, "listen": cmd_listen, "eq": cmd_eq,
            "eq-read": cmd_eq_read, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
