# Fantasia / RH787T RF remote findings

Reverse-engineering notes and measured replay waveforms for a Fantasia ceiling-fan remote in the RH787T family. Captures were acquired through **[SDR-MCP](https://github.com/sandraschi/sdr-mcp) using real RTL-SDR IQ**. A complete speed-2 press was replayed through **Home Assistant's `eyocean.send_raw` action and an ESPHome CC1101 transmitter**; the owner confirmed that the stopped fan started at speed 2.

This is a research/data repository, **not a complete Home Assistant fan integration or a universal RH787T encoder**.

## Remote reference photo

[![White ANDERIC replacement remote with six speed buttons, stop, reverse and light controls](https://m.media-amazon.com/images/I/51IS9i3G3ZL._AC_SL1500_.jpg)](https://www.amazon.co.uk/Anderic-Replacement-Casablanca-Compatible-RH787T-white/dp/B0DHDDQLT5?crid=KWWMTVGJZRP7&dib=eyJ2IjoiMSJ9.gNCwdDNIMYzcwGDsCHTqkZB6rc9v0bCQNeCBoi-mWOk.10h_IPQXMW9rzMV0zCfxG86GPryoda5iavLz9NT8bkE&dib_tag=se&keywords=rh787t&qid=1794083224&sprefix=rh787t%2Caps%2C120&sr=8-1)

Product photo from the linked Amazon UK listing for the Anderic RR787T replacement. It illustrates the remote family, **not the exact unit tested**; compatibility with this fan has not been tested. The image is externally hosted and is not covered by this repository's MIT license.

## Hardware and settings

- SDR receiver: [RTL-SDR device used for capture — Amazon UK listing supplied by the owner](https://www.amazon.co.uk/dp/B01GDN1T4S?ref=ppx_yo2ov_dt_b_fed_asin_title).
- Capture software: [SDR-MCP](https://github.com/sandraschi/sdr-mcp). The capture instance included a local bounded raw-IQ recording extension.
- Remote compartment sticker: **434**.
- Numbered DIP bank: **1 ON, 2 ON, 3 OFF, 4 ON** (owner described these as UP, UP, DOWN, UP).
- Separate switch above the bank: **D / ON**, confirmed in **D** position. It is a light-mode selector, not a fifth numbered address switch.
- The owner confirms **non-dimming light operation**. LIGHT is an on/off toggle; do not expose brightness control from the held-LIGHT recording.
- Demonstrated CC1101 transmit frequency: **433.92 MHz ASK/OOK**.

**The actual remote identity and waveforms are intentionally published with the owner's permission.** They are specific to this remote's configuration and may operate a matching nearby receiver. Do not transmit indiscriminately or assume another remote uses the same address. DIP polarity, transmitted bit order and exact address-field boundaries have not been established.

The FCC manual linked below describes a **303.947 MHz variant**. Do not retune this setup based on that document or treat the `434` sticker as a calibrated measurement of exactly 434.000 MHz.

## Captured controls

These signatures classify **short/long positive marks** in the recorded envelope. They are not, by themselves, established logical data bits. The same common trailing pattern, `0111010000000`, appears after many command packets; its precise release/end semantics remain unproven.

| Control | Mark-width signature | Candidate |
| --- | --- | --- |
| Speed 1 / I | `0111010001000` | [speed_1.json](waveforms/speed_1.json) |
| Speed 2 / II | `0111010001010` | [speed_2.json](waveforms/speed_2.json) |
| Speed 3 / III | `0111010010000` | [speed_3.json](waveforms/speed_3.json) |
| Speed 4 / IV | `0111010011000` | [speed_4.json](waveforms/speed_4.json) |
| Speed 5 / V | `0111010100010` | [speed_5.json](waveforms/speed_5.json) |
| Speed 6 / VI | `0111010100000` | [speed_6.json](waveforms/speed_6.json) |
| OFF | `0111010000010` | [off.json](waveforms/off.json) |
| REV | `0111010000100` | [reverse.json](waveforms/reverse.json) |
| LIGHT tap | `0111010000001` | [light_tap.json](waveforms/light_tap.json) |
| LIGHT held | Same LIGHT signature, sustained repetition | [light_hold.json](waveforms/light_hold.json) — diagnostic only, **not dimming** |

**SET was deliberately excluded** because it initiates learning/pairing. No DIP switches or receiver pairing were changed during capture.

## What actually worked

Use **[speed_2_verified.json](waveforms/speed_2_verified.json)** as the physically proven reference, not the alternative `speed_2.json` candidate.

- One complete captured press: **nine command packets plus three common trailing packets**.
- 312 signed durations; total encoded airtime including chosen termination silence: **289560 microseconds**.
- `repeats: 1` means one full captured press, not one packet.
- HA send timestamp: **2026-11-07T19:21:31.073+00:00**.
- Initial condition: owner confirmed fan visibly stopped.
- Owner's result: **fan started at speed 2**.

All ten other waveform files are **captured candidates, not physically replay-tested payloads**. The alternative speed-2 file contains a different press from the same recording and has not been replay-tested. An earlier speed-1 replay also worked, but it was a different payload and does not validate this repository's new speed-1 candidate.

The successful trial was monitored by another real SDR recording, but that recording has not been analyzed as a transmitted-waveform comparison. HA success/timestamps alone do not prove correct RF output or appliance response. This trial does not establish why earlier attempts failed.

## Using a waveform with Home Assistant

Each waveform JSON is an action mapping for **`eyocean.send_raw`**, provided by the separate [EYOCEAN RF integration](https://github.com/charrus/eyocean-radio-frequency). This action is not a built-in HA service, and this repository does not register it.

1. Configure an ESPHome CC1101 native RF proxy correctly, including physical tuning, antenna routing and TX/RX callbacks, and connect it through HA's ESPHome integration.
2. Confirm that its `radio_frequency` transmitter entity and the administrator-only `eyocean.send_raw` action exist.
3. Replace `radio_frequency.your_transmitter` in the chosen file with your actual HA transmitter entity ID.
4. Review the complete action before invoking it. In HA's YAML action editor, use the equivalent YAML mapping; the JSON files are also intended for API clients that accept action/data mappings.
5. Send only an explicitly intended test and observe the real appliance. For start tests, confirm stopped blades first; for REV tests, wait for blades to stop fully.

Timings are signed microseconds: **positive = RF mark, negative = space**. Measured internal gaps and trailing packets are retained. Multi-second human inter-press gaps are not transmitted. Final termination silence uses the median internal gap rather than the long interval after release.

No file or validation script transmits automatically. Comply with local spectrum and duty-cycle requirements. Do not assume a local ESPHome button-permission switch also blocks native HA RF proxy requests.

## Community protocol comparison

The [September 2025 reply in the RH787T thread](https://community.home-assistant.io/t/dc-ceiling-fan-rf-remote-rh787t/386621/17) describes a closer short-frame variant than the original post's longer code example.

**All nine distinct button-command suffixes agree** when the last six positions of our mark-width signatures are inverted:

| Control | Inverted captured suffix | Code published in that reply |
| --- | --- | --- |
| Speed 1 | `110111` | `010000110111` |
| Speed 2 | `110101` | `010000110101` |
| Speed 3 | `101111` | `010000101111` |
| Speed 4 | `100111` | `010000100111` |
| Speed 5 | `011101` | `010000011101` |
| Speed 6 | `011111` | `010000011111` |
| OFF | `111101` | `010000111101` |
| REV | `111011` | `010000111011` |
| LIGHT | `111110` | `010000111110` |

Our common trailing signature has inverted suffix `111111`; the published scripts likewise send a common trailing code, `010000111111`, after command frames. This is strong evidence of a shared command-field encoding, **not a complete validated encoder or proof of identical address, sync timing or carrier**. The contributor describes 303 MHz hardware, not our demonstrated 433.92 MHz setup. Their exact command prefixes, timing values and repetition counts must not be copied as this remote's settings.

The code examples in the table are attributed comparative data, not a copied firmware implementation. No third-party firmware, manual PDF, forum image or photograph is stored in this repository; the product photo above is linked from Amazon's image host.

## Capture quality and limitations

- Separate original-controller presses were confirmed interactively in labelled capture intervals.
- Real SDR center tuning was 433.87 MHz at approximately 250 ksample/s. Offline channelization used a 17.5 kHz offset. Existing tuner correction was retained; these uncalibrated values are not a precise carrier-frequency measurement.
- Short-press signatures were compared at multiple envelope thresholds. One speed-5 press contained an anomalous speed-6-pattern packet and was excluded from the replay candidate.
- REV was captured from **one physical press**, with repeated consistent packets; cross-press verification remains outstanding.
- The highest threshold damaged part of the last LIGHT-tap press; its candidate uses the first complete press.
- Held LIGHT faded enough for high thresholds to fragment it. Thresholds 0.12, 0.2 and 0.3 recovered the same three complete held sequences. It repeats the ordinary LIGHT pattern; it is **not evidence of dimming** in this non-dimming configuration.
- Raw IQ files and the remote photo are not distributed. [manifest.json](manifest.json) records source IQ SHA256s, selection offsets, threshold counts, packet composition and candidate status for traceability. Source hashes identify the original recordings; the waveform files alone do not reproduce the IQ analysis.
- Credentials, network addresses, household entity names and machine-local paths have been omitted. RF address information remains in the intentionally published waveforms.

## Validation

Run with Python 3.14.4 (standard library only):

```sh
python scripts/validate.py
```

Validation checks inventory completeness, sender bounds, sign alternation, full-press repeat semantics, manifest consistency, all command-suffix comparisons, the exact verified payload digest and local documentation links. It does not access hardware or prove appliance compatibility. GitHub Actions runs the same checks.

## References and license

- [Original RH787T discussion](https://community.home-assistant.io/t/dc-ceiling-fan-rf-remote-rh787t/386621)
- [Short-frame command/trailing-packet example](https://community.home-assistant.io/t/dc-ceiling-fan-rf-remote-rh787t/386621/17)
- [FCC manual filing](https://fccid.io/CHQRH787T/User-Manual/User-manual-831257), [accessible PDF copy](https://fcc.report/FCC-ID/CHQRH787T/831257.pdf)
- [RH787T D/ON switch instructions](https://remotizo.com/product/regency-rh787t-ceiling-fan-remote-control)
- [EYOCEAN integration providing the diagnostic sender](https://github.com/charrus/eyocean-radio-frequency)

Original findings, measured waveform data and validation code in this repository are [MIT licensed](LICENSE). Linked third-party content remains under its respective owners' terms.
