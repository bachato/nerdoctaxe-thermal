# NerdOCTAXE-Gamma Thermal Governor

Custom build wrapper for `shufps/ESP-Miner-NerdQAxePlus` (develop branch), targeting **NERDOCTAXEGAMMA**.

## Goal

Add automatic ASIC-frequency throttling based on the hottest measured ASIC/board temperature, while keeping the user's configured frequency unchanged in settings.

## Thermal policy

The runtime frequency is capped progressively:

| Temperature | Maximum runtime frequency |
|---|---:|
| < 70 C | configured value |
| >= 70 C | 675 MHz |
| >= 72 C | 650 MHz |
| >= 74 C | 625 MHz |
| >= 76 C | 600 MHz |
| >= 78 C | 575 MHz |
| >= 80 C | 550 MHz |
| >= 82 C | 525 MHz |

Each level has 2 C recovery hysteresis, so the miner does not constantly switch frequencies around a threshold. The existing AxeOS over-temperature shutdown remains untouched and still has priority.

## Build

GitHub Actions clones the upstream firmware, applies `scripts/apply_thermal_governor.py`, builds only `NERDOCTAXEGAMMA`, and uploads OTA and factory binaries as workflow artifacts.

This is an experimental custom firmware. Test conservatively and keep the stock firmware available for rollback.
