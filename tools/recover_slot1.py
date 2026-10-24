#!/usr/bin/env python3
"""Authorized one-time working-bank recovery; never persists or reverses it."""
import copy
import json
from pathlib import Path
import a50


def recover(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (directory / name).write_text(json.dumps(value, indent=2) + "\n")
    with a50.A50Client() as client:
        try:
            before = client.snapshot()
            save("before.json", before)
            gains = before["slots"][0]["gains"]
            if gains["stored"] != [-4, -2, -3, 7, 7]:
                raise a50.EqReadError("retained bank differs; recovery stopped before write")
            if gains["working"] not in ([-10, -12, -12, -12, -12], gains["stored"]):
                raise a50.EqReadError("working bank differs; recovery stopped before write")
            if gains["working"] != gains["stored"]:
                client.set_gains(1, gains["stored"])
            # First read immediately after the setter confirms both gain banks.
            readback = client.gains(1)
            save("slot1-readback.json", readback)
            assert readback["working"] == readback["stored"] == gains["stored"]
            after = client.snapshot()
            save("after.json", after)
            expected = copy.deepcopy(before)
            expected["slots"][0]["gains"]["working"] = gains["stored"]
            assert expected["slots"] == after["slots"], "unexpected EQ change"
            assert before["settings"] == after["settings"], "unexpected settings change"
            save("result.json", {"recovered": True, "only_change": "slot1 working gains",
                                 "persistent_sync_sent": False})
        finally:
            save("capture.json", client.capture)
    print("Slot 1 recovered; both banks agree; all other EQ/settings unchanged.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_evidence_directory")
    recover(parser.parse_args().new_evidence_directory)
