"""Validate the published research artifacts offline; never transmit RF."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {*(f"speed_{i}" for i in range(1, 7)), "off", "reverse", "light_tap", "light_hold", "speed_2_verified"}
FORUM_SUFFIXES = {
    "speed_1": "110111", "speed_2": "110101", "speed_3": "101111",
    "speed_4": "100111", "speed_5": "011101", "speed_6": "011111",
    "off": "111101", "reverse": "111011", "light_tap": "111110",
}
VERIFIED_TIMINGS_SHA256 = "6f654aaa24f54ce1a782b8e58aea77cf5e997210ac4f3652d843cb49dfcb33a7"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_waveform(timings, repeats):
    require(type(repeats) is int and 1 <= repeats <= 20, "Invalid total repeats")
    require(isinstance(timings, list), "Timings must be a list")
    require(2 <= len(timings) <= 4096 and len(timings) % 2 == 0, "Invalid duration count")
    for index, duration in enumerate(timings):
        require(type(duration) is int, "Durations must be integers, never booleans")
        require(1 <= abs(duration) <= 500000, "Duration out of range")
        require((duration > 0) == (index % 2 == 0), "Mark/space signs must alternate")
    airtime = sum(map(abs, timings)) * repeats
    require(airtime <= 5000000, "Encoded burst exceeds five seconds")
    return airtime


def main():
    # Exercise the validator's rejection paths as well as the real files.
    invalid = [([True, -250], 1), ([250, 250], 1), ([250, -250, 250], 1),
               ([0, -250], 1), ([500001, -250], 1), ([250, -250], True),
               ([250, -250], 21), ([500000, -500000], 6)]
    for timings, repeats in invalid:
        try:
            validate_waveform(timings, repeats)
        except ValueError:
            pass
        else:
            raise ValueError("Validator accepted an invalid test case")

    manifest = json.loads((ROOT / "manifest.json").read_text())
    require(set(manifest["waveforms"]) == EXPECTED, "Unexpected or missing manifest controls")
    actual = {path.stem for path in (ROOT / "waveforms").glob("*.json")}
    require(actual == EXPECTED, "Unexpected or missing waveform files")
    require(manifest["remote"]["separate_light_switch"] == "D", "Incorrect light-mode switch")
    require(manifest["remote"]["light_behavior"] == "non-dimming toggle", "Incorrect light behavior")
    require(manifest["remote"]["dip_bank"] == {"1": "ON", "2": "ON", "3": "OFF", "4": "ON"}, "Incorrect DIP baseline")
    require("SET" in manifest["excluded_controls"], "SET exclusion is missing")
    referenced = set()
    for control, record in manifest["waveforms"].items():
        path = ROOT / record["path"]
        require(path.resolve().is_relative_to(ROOT), "Waveform path escapes repository")
        require(path.name == f"{control}.json", "Waveform name mismatch")
        action = json.loads(path.read_text())
        require(set(action) == {"action", "data"}, "Unexpected action fields")
        require(action["action"] == "eyocean.send_raw", "Wrong sender action")
        data = action["data"]
        require(set(data) == {"transmitter", "timings", "repeats"}, "Unexpected sender fields")
        require(data["transmitter"] == "radio_frequency.your_transmitter", "Unsanitized transmitter")
        require(data["repeats"] == record["total_transmissions"] == 1, "Whole-press repetition mismatch")
        airtime = validate_waveform(data["timings"], data["repeats"])
        require(airtime == record["airtime_us"], "Airtime mismatch")
        require(len(data["timings"]) == record["duration_count"], "Pulse-count mismatch")
        require(re.fullmatch(r"[0-9a-f]{64}", record["source_sha256"]), "Invalid source SHA256")
        require(re.fullmatch(r"[01]{13}", record["mark_width_pattern"]), "Invalid signature")
        packets = sum(record["selected_packet_patterns"].values())
        require(packets * 26 == record["duration_count"], "Packet inventory mismatch")
        if control == "speed_2_verified":
            digest = hashlib.sha256(json.dumps(data["timings"], separators=(",", ":")).encode()).hexdigest()
            require(digest == VERIFIED_TIMINGS_SHA256, "The proven payload changed")
            require(record["replay_status"] == "owner_confirmed_fan_started_at_speed_2", "Missing physical evidence")
        else:
            require(record["replay_status"] == "not_tested", "Unverified candidate claims physical success")
        if control in FORUM_SUFFIXES:
            inverted = record["mark_width_pattern"][-6:].translate(str.maketrans("01", "10"))
            require(inverted == FORUM_SUFFIXES[control], "Forum suffix mismatch")
        referenced.add(path.resolve())
        print(f"PASS {control}: {len(data['timings'])} durations, {airtime} us")
    require(len(referenced) == len(EXPECTED), "Duplicate file references")
    require(manifest["waveforms"]["light_tap"]["mark_width_pattern"] == manifest["waveforms"]["light_hold"]["mark_width_pattern"], "Unexpected held-LIGHT signature")

    for markdown in ROOT.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", markdown.read_text()):
            if "://" not in target and not target.startswith("#"):
                require((markdown.parent / target.split("#")[0]).exists(), f"Broken link: {target}")
    print(f"Validated {len(EXPECTED)} waveform files, {len(FORUM_SUFFIXES)} command-suffix comparisons and local documentation links. No RF transmitted.")


if __name__ == "__main__":
    main()
