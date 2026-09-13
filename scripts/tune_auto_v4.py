from pathlib import Path

path = Path("main/tasks/power_management_task.cpp")
src = path.read_text()

replacements = [
    (
        "// AUTO steps down after ~6 s above target+1 C and steps up only after\n        // ~60 s at/below target-2 C. Hard ASIC/VRM caps remain active even when",
        "// AUTO steps down after ~12 s above target+1 C and steps up only after\n        // ~180 s at/below target-3 C. Hard ASIC/VRM caps remain active even when",
        "governor timing comment",
    ),
    (
        "const float coolThreshold = (float)targetTemp - 2.0f;",
        "const float coolThreshold = (float)targetTemp - 3.0f;",
        "cool threshold",
    ),
    (
        "if (hotPolls >= 3) {",
        "if (hotPolls >= 6) {",
        "hot debounce",
    ),
    (
        "if (coolPolls >= 30) {",
        "if (coolPolls >= 90) {",
        "cool recovery delay",
    ),
]

for old, new, label in replacements:
    if old not in src:
        raise SystemExit(f"AUTO v4 patch failed: {label} not found")
    src = src.replace(old, new, 1)

path.write_text(src)
print("AUTO v4 tuned: ~12 s hot debounce, target-3 C recovery threshold, ~180 s cool recovery")
