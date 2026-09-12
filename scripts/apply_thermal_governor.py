from pathlib import Path

path = Path("main/tasks/power_management_task.cpp")
src = path.read_text()

include_anchor = '#define POLL_RATE 2000\n\nstatic const char *TAG = "power_management";'
include_replacement = '''#define POLL_RATE 2000\n\nstatic const char *TAG = "power_management";\n\n#ifdef NERDOCTAXEGAMMA\n// Runtime-only thermal governor for NerdOCTAXE-Gamma.\n// This never writes the configured ASIC frequency to NVS.\nstatic int nerdOctaxeThermalCap(float temp, int currentCap)\n{\n    struct Step { float trigger; int cap; };\n    static const Step steps[] = {\n        {70.0f, 675}, {72.0f, 650}, {74.0f, 625}, {76.0f, 600},\n        {78.0f, 575}, {80.0f, 550}, {82.0f, 525}\n    };\n\n    int requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n\n    // Heating: throttle immediately to the newly requested (lower) cap.\n    if (currentCap == 0 || (requested != 0 && requested < currentCap)) {\n        return requested;\n    }\n\n    // Cooling: hold the current cap until 2 C below its trigger.\n    if (currentCap != 0) {\n        float trigger = 70.0f;\n        for (const auto &step : steps) {\n            if (step.cap == currentCap) {\n                trigger = step.trigger;\n                break;\n            }\n        }\n        if (temp >= trigger - 2.0f) return currentCap;\n    }\n\n    // Once hysteresis is cleared, recompute the cap from the current temperature.\n    requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n    return requested;\n}\n#endif'''

if include_anchor not in src:
    raise SystemExit("Unable to find power-management include anchor; upstream changed")
src = src.replace(include_anchor, include_replacement, 1)

loop_anchor = '''        influx_task_set_temperature(m_chipTempMax, m_vrTemp);\n\n        // Run fan controller (reads RPM, drives fans, updates overheat flags)'''
loop_replacement = '''        influx_task_set_temperature(m_chipTempMax, m_vrTemp);\n\n#ifdef NERDOCTAXEGAMMA\n        // Apply a runtime-only frequency cap based on temperature. The user's\n        // configured frequency remains untouched and is restored after cooling.\n        static int thermalCapMHz = 0;\n        static int lastRuntimeMHz = -1;\n        static int lastConfiguredMHz = -1;\n\n        thermalCapMHz = nerdOctaxeThermalCap(m_chipTempMax, thermalCapMHz);\n        const int configuredMHz = m_board->getAsicFrequency();\n        const int runtimeMHz = thermalCapMHz ? std::min(configuredMHz, thermalCapMHz) : configuredMHz;\n        const bool configuredChanged = configuredMHz != lastConfiguredMHz;\n\n        // checkAsicFrequencyChanged() runs earlier in this loop and applies a newly\n        // configured value. If we are thermally capped and that edit is still above\n        // the cap, re-apply the cap immediately even when runtimeMHz itself did not\n        // change from the previous governor iteration.\n        const bool mustReapplyCap = thermalCapMHz > 0 && configuredChanged;\n        if (!m_shutdown && m_board->isInitialized() &&\n            (runtimeMHz != lastRuntimeMHz || mustReapplyCap)) {\n            if (m_board->setAsicFrequency((float) runtimeMHz)) {\n                ESP_LOGW(TAG, "Thermal governor: chip=%.1fC configured=%dMHz cap=%dMHz runtime=%dMHz",\n                         m_chipTempMax, configuredMHz, thermalCapMHz, runtimeMHz);\n                lastRuntimeMHz = runtimeMHz;\n            } else {\n                ESP_LOGE(TAG, "Thermal governor failed to set %dMHz", runtimeMHz);\n            }\n        }\n\n        lastConfiguredMHz = configuredMHz;\n#endif\n\n        // Run fan controller (reads RPM, drives fans, updates overheat flags)'''

if loop_anchor not in src:
    raise SystemExit("Unable to find thermal-governor insertion anchor; upstream changed")
src = src.replace(loop_anchor, loop_replacement, 1)

path.write_text(src)
print("Applied NerdOCTAXE-Gamma thermal governor")
