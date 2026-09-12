from pathlib import Path

path = Path("main/tasks/power_management_task.cpp")
src = path.read_text()

old = '''            if (!chipTempValid) {
                invalidChipPolls++;
                hotPolls = 0;
                coolPolls = 0;
                // Three consecutive invalid readings (~6 s) -> safe minimum.
                if (invalidChipPolls >= 3) autoMHz = 525;
            } else {
                invalidChipPolls = 0;

                if (m_chipTempMax > hotThreshold) {'''
new = '''            if (!chipTempValid) {
                // The shared sensor-failsafe block below owns invalidChipPolls so
                // each 2 s loop counts exactly once.
                hotPolls = 0;
                coolPolls = 0;
            } else {
                if (m_chipTempMax > hotThreshold) {'''

if old not in src:
    raise SystemExit("AUTO v3 invalid-reading block not found")
src = src.replace(old, new, 1)

old2 = '''        vrHardCapMHz = vrTempValid ? nerdOctaxeVrHardCap(vrMax, vrHardCapMHz) : vrHardCapMHz;

        int runtimeMHz = autoEnabled ? autoMHz : configuredMHz;'''
new2 = '''        vrHardCapMHz = vrTempValid ? nerdOctaxeVrHardCap(vrMax, vrHardCapMHz) : vrHardCapMHz;

        if (autoEnabled && invalidChipPolls >= 3) autoMHz = 525;

        int runtimeMHz = autoEnabled ? autoMHz : configuredMHz;'''

if old2 not in src:
    raise SystemExit("AUTO v3 failsafe insertion anchor not found")
src = src.replace(old2, new2, 1)

path.write_text(src)
print("Fixed AUTO v3 sensor failsafe: three invalid readings means ~6 seconds")
