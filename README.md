# NerdOCTAXE-Gamma Adaptive Thermal Governor

Custom build wrapper for `shufps/ESP-Miner-NerdQAxePlus`, pinned to upstream commit `b4af4e84aa3cb5ab066c9fea77dbc77beb9abcb3`, targeting **NERDOCTAXEGAMMA**.

## Goal

Keep the miner as fast as practical while automatically reducing ASIC frequency when temperatures rise. Runtime frequency changes do **not** overwrite the frequency saved in AxeOS; the configured value is treated as the maximum ceiling.

## AUTO mode

AUTO mode targets a conservative thermal band:

- Above **69 C** for about 6 seconds: reduce frequency by **25 MHz**.
- At or below **66 C** continuously for about 60 seconds: increase frequency by **25 MHz**, up to the AxeOS configured ceiling.
- Between 66 C and 69 C: hold the current runtime frequency.
- If the user lowers the configured frequency, the lower value takes effect immediately. Raising the configured value only raises the ceiling; AUTO mode climbs gradually when cool.

## ASIC hard safety caps

These remain in force even if AUTO mode would otherwise choose a higher frequency:

| ASIC temperature | Maximum runtime frequency |
|---|---:|
| < 70 C | AUTO-selected value |
| >= 70 C | 675 MHz |
| >= 72 C | 650 MHz |
| >= 74 C | 625 MHz |
| >= 76 C | 600 MHz |
| >= 78 C | 575 MHz |
| >= 80 C | 550 MHz |
| >= 82 C | 525 MHz |

ASIC hard caps use 2 C recovery hysteresis.

## VRM hard safety caps

| VRM temperature | Maximum runtime frequency |
|---|---:|
| < 80 C | AUTO-selected value |
| >= 80 C | 675 MHz |
| >= 85 C | 650 MHz |
| >= 90 C | 600 MHz |
| >= 95 C | 550 MHz |
| >= 100 C | 525 MHz |

VRM caps use 3 C recovery hysteresis.

## Sensor failsafe

Three consecutive invalid ASIC-temperature readings (about 6 seconds) force the runtime frequency to **525 MHz** until valid telemetry returns. The stock AxeOS over-temperature shutdown is not removed or weakened.

## Build

GitHub Actions fetches the pinned upstream source, applies `scripts/apply_thermal_governor.py`, builds only `NERDOCTAXEGAMMA`, and uploads OTA, matching WWW, and factory binaries as workflow artifacts.

This is experimental custom firmware. Test conservatively and keep the known-good firmware available for rollback.
