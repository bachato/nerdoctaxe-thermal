# NerdOCTAXE-Gamma Adaptive Thermal Governor — AUTO v4

Custom build wrapper for `shufps/ESP-Miner-NerdQAxePlus`, pinned to upstream commit `b4af4e84aa3cb5ab066c9fea77dbc77beb9abcb3`, targeting **NERDOCTAXEGAMMA**.

## Goal

Keep the miner as fast as practical while automatically reducing ASIC frequency when temperatures rise, while avoiding unnecessary frequency hunting around the thermal target. Runtime frequency changes do **not** overwrite the frequency saved in AxeOS; the configured value is treated as the maximum ceiling.

## AxeOS controls

AUTO v4 keeps the two persistent settings in the AxeOS Mining Settings screen:

- **AUTO Thermal Mode** — enable/disable adaptive frequency control.
- **Target ASIC temperature** — configurable from **60 to 69 C**, default **68 C**.

When AUTO is disabled, the configured AxeOS frequency is used normally, but the hard ASIC/VRM safety caps below remain active.

## AUTO v4 algorithm

For a target `T`:

- Above **T + 1 C** continuously for about **12 seconds**: reduce frequency by **25 MHz**.
- At or below **T - 3 C** continuously for about **180 seconds**: increase frequency by **25 MHz**, up to the AxeOS configured ceiling.
- Inside that band: hold the current runtime frequency.
- If the user lowers the configured frequency, the lower ceiling takes effect immediately. Raising the configured value only raises the ceiling; AUTO climbs gradually when cool.

At the default target of **68 C**, this means stepping down after about 12 seconds above **69 C** and recovering only after about 3 minutes at or below **65 C**. This wider, asymmetric hysteresis is intended to reduce repeated MHz changes when the miner sits near its thermal equilibrium.

## ASIC hard safety caps

These remain in force whether AUTO is enabled or disabled and are unchanged from AUTO v3:

| ASIC temperature | Maximum runtime frequency |
|---|---:|
| < 70 C | selected/configured value |
| >= 70 C | 675 MHz |
| >= 72 C | 650 MHz |
| >= 74 C | 625 MHz |
| >= 76 C | 600 MHz |
| >= 78 C | 575 MHz |
| >= 80 C | 550 MHz |
| >= 82 C | 525 MHz |

ASIC hard caps use 2 C recovery hysteresis. When a hard cap lowers runtime frequency while AUTO is enabled, AUTO's internal state is pulled down too, so subsequent recovery remains gradual.

## VRM hard safety caps

| VRM temperature | Maximum runtime frequency |
|---|---:|
| < 80 C | selected/configured value |
| >= 80 C | 675 MHz |
| >= 85 C | 650 MHz |
| >= 90 C | 600 MHz |
| >= 95 C | 550 MHz |
| >= 100 C | 525 MHz |

VRM caps use 3 C recovery hysteresis.

## Sensor failsafe

Three consecutive invalid ASIC-temperature readings (about 6 seconds) force the runtime frequency to **525 MHz** until valid telemetry returns. The stock AxeOS over-temperature shutdown is not removed or weakened.

## Build outputs

GitHub Actions fetches the pinned upstream source, applies the base governor, the corrected sensor failsafe, and the AUTO v4 anti-hunting tuning, builds only `NERDOCTAXEGAMMA`, and uploads:

- `esp-miner-NerdOCTAXE-Gamma.bin` — firmware OTA image.
- `www.bin` — matching AxeOS web interface containing the AUTO controls.
- `nerdOCTAXE-Gamma-auto-v4-factory.bin` — complete factory/recovery image.

For a normal web update, firmware and WWW are flashed through the two separate manual update fields in AxeOS. The factory image is for recovery/full flashing, not the normal OTA field.

This is experimental custom firmware. Test conservatively and keep the known-good firmware available for rollback.

## Support development

If this firmware is useful to you and you would like to support further development, Bitcoin donations are welcome.

**Bitcoin (on-chain):**

`bc1qehf6evpr6w8wcw0jp5t7z3vtz2wech0u33854p`
