from pathlib import Path


def replace_once(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        raise SystemExit(f"Unable to find {label}; pinned upstream may have changed")
    return src.replace(old, new, 1)


# -----------------------------------------------------------------------------
# Persistent settings keys
# -----------------------------------------------------------------------------
path = Path("main/nvs_config.h")
src = path.read_text()
anchor = '#define NVS_CONFIG_VR_FREQUENCY "vr_frequency"\n'
replacement = anchor + '''\n// NerdOCTAXE-Gamma adaptive thermal governor\n#define NVS_CONFIG_THERMAL_AUTO "th_auto"\n#define NVS_CONFIG_THERMAL_TARGET "th_target"\n'''
src = replace_once(src, anchor, replacement, "NVS thermal settings anchor")
path.write_text(src)


# -----------------------------------------------------------------------------
# Runtime governor
# -----------------------------------------------------------------------------
path = Path("main/tasks/power_management_task.cpp")
src = path.read_text()

include_anchor = '#define POLL_RATE 2000\n\nstatic const char *TAG = "power_management";'
include_replacement = '''#define POLL_RATE 2000\n\nstatic const char *TAG = "power_management";\n\n#ifdef NERDOCTAXEGAMMA\n// NerdOCTAXE-Gamma adaptive runtime governor.\n// The frequency configured in AxeOS is a ceiling while AUTO mode is enabled.\n// Runtime frequency changes are never written back to persistent settings.\nstatic int nerdOctaxeChipHardCap(float temp, int currentCap)\n{\n    struct Step { float trigger; int cap; };\n    static const Step steps[] = {\n        {70.0f, 675}, {72.0f, 650}, {74.0f, 625}, {76.0f, 600},\n        {78.0f, 575}, {80.0f, 550}, {82.0f, 525}\n    };\n\n    int requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n\n    // Heating: lower the cap immediately.\n    if (currentCap == 0 || (requested != 0 && requested < currentCap)) {\n        return requested;\n    }\n\n    // Cooling: 2 C hysteresis before releasing the current cap.\n    if (currentCap != 0) {\n        float trigger = 70.0f;\n        for (const auto &step : steps) {\n            if (step.cap == currentCap) {\n                trigger = step.trigger;\n                break;\n            }\n        }\n        if (temp >= trigger - 2.0f) return currentCap;\n    }\n\n    requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n    return requested;\n}\n\nstatic int nerdOctaxeVrHardCap(float temp, int currentCap)\n{\n    struct Step { float trigger; int cap; };\n    static const Step steps[] = {\n        {80.0f, 675}, {85.0f, 650}, {90.0f, 600}, {95.0f, 550}, {100.0f, 525}\n    };\n\n    int requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n\n    if (currentCap == 0 || (requested != 0 && requested < currentCap)) {\n        return requested;\n    }\n\n    if (currentCap != 0) {\n        float trigger = 80.0f;\n        for (const auto &step : steps) {\n            if (step.cap == currentCap) {\n                trigger = step.trigger;\n                break;\n            }\n        }\n        if (temp >= trigger - 3.0f) return currentCap;\n    }\n\n    requested = 0;\n    for (const auto &step : steps) {\n        if (temp >= step.trigger) requested = step.cap;\n    }\n    return requested;\n}\n\nstatic int nerdOctaxeFloorSupported(int mhz)\n{\n    if (mhz <= 525) return 525;\n    return 525 + ((mhz - 525) / 25) * 25;\n}\n\nstatic int nerdOctaxeStepDown(int mhz)\n{\n    return std::max(525, nerdOctaxeFloorSupported(mhz) - 25);\n}\n\nstatic int nerdOctaxeStepUp(int mhz, int ceiling)\n{\n    const int maxSupported = nerdOctaxeFloorSupported(ceiling);\n    return std::min(maxSupported, nerdOctaxeFloorSupported(mhz) + 25);\n}\n#endif'''
src = replace_once(src, include_anchor, include_replacement, "power-management include anchor")

loop_anchor = '''        influx_task_set_temperature(m_chipTempMax, m_vrTemp);\n\n        // Run fan controller (reads RPM, drives fans, updates overheat flags)'''
loop_replacement = '''        influx_task_set_temperature(m_chipTempMax, m_vrTemp);\n\n#ifdef NERDOCTAXEGAMMA\n        // Configurable adaptive AUTO mode. The user-selected AxeOS frequency is\n        // the ceiling. The target is configurable from 60 to 69 C (default 68 C).\n        // AUTO steps down after ~6 s above target+1 C and steps up only after\n        // ~60 s at/below target-2 C. Hard ASIC/VRM caps remain active even when\n        // AUTO is switched off, and stock over-temperature shutdown is untouched.\n        static int autoMHz = -1;\n        static int chipHardCapMHz = 0;\n        static int vrHardCapMHz = 0;\n        static int lastRuntimeMHz = -1;\n        static int lastConfiguredMHz = -1;\n        static bool lastAutoEnabled = true;\n        static int hotPolls = 0;\n        static int coolPolls = 0;\n        static int invalidChipPolls = 0;\n\n        const int configuredMHz = m_board->getAsicFrequency();\n        const bool configuredChanged = configuredMHz != lastConfiguredMHz;\n        const bool autoEnabled = Config::cfgGetBool(NVS_CONFIG_THERMAL_AUTO, true);\n        int targetTemp = (int)Config::cfgGetU16(NVS_CONFIG_THERMAL_TARGET, 68);\n        targetTemp = std::max(60, std::min(69, targetTemp));\n        const float hotThreshold = (float)targetTemp + 1.0f;\n        const float coolThreshold = (float)targetTemp - 2.0f;\n\n        const float vrMax = std::max(m_vrTemp, m_vrTempInt);\n        const bool chipTempValid = m_chipTempMax >= 10.0f && m_chipTempMax <= 110.0f;\n        const bool vrTempValid = vrMax > 0.0f && vrMax <= 125.0f;\n\n        if (autoMHz < 0) autoMHz = nerdOctaxeFloorSupported(configuredMHz);\n\n        if (!autoEnabled) {\n            // Manual frequency mode, but hard safety caps below still apply.\n            autoMHz = nerdOctaxeFloorSupported(configuredMHz);\n            hotPolls = 0;\n            coolPolls = 0;\n        } else {\n            // When AUTO is re-enabled, resume from the current effective speed\n            // instead of jumping immediately to the configured ceiling.\n            if (!lastAutoEnabled) {\n                autoMHz = lastRuntimeMHz > 0\n                    ? std::min(nerdOctaxeFloorSupported(configuredMHz), nerdOctaxeFloorSupported(lastRuntimeMHz))\n                    : nerdOctaxeFloorSupported(configuredMHz);\n            }\n\n            // Lowering the AxeOS ceiling takes effect immediately. Raising it only\n            // raises the ceiling; AUTO climbs gradually when sufficiently cool.\n            if (configuredChanged && configuredMHz < autoMHz) {\n                autoMHz = nerdOctaxeFloorSupported(configuredMHz);\n            }\n\n            if (!chipTempValid) {\n                invalidChipPolls++;\n                hotPolls = 0;\n                coolPolls = 0;\n                // Three consecutive invalid readings (~6 s) -> safe minimum.\n                if (invalidChipPolls >= 3) autoMHz = 525;\n            } else {\n                invalidChipPolls = 0;\n\n                if (m_chipTempMax > hotThreshold) {\n                    hotPolls++;\n                    coolPolls = 0;\n                    if (hotPolls >= 3) {\n                        autoMHz = nerdOctaxeStepDown(autoMHz);\n                        hotPolls = 0;\n                    }\n                } else if (m_chipTempMax <= coolThreshold) {\n                    coolPolls++;\n                    hotPolls = 0;\n                    if (coolPolls >= 30) {\n                        autoMHz = nerdOctaxeStepUp(autoMHz, configuredMHz);\n                        coolPolls = 0;\n                    }\n                } else {\n                    hotPolls = 0;\n                    coolPolls = 0;\n                }\n            }\n        }\n\n        // Sensor failsafe is deliberately delayed until three bad readings so an\n        // isolated startup/read glitch does not unnecessarily force 525 MHz.\n        if (chipTempValid) {\n            invalidChipPolls = 0;\n            chipHardCapMHz = nerdOctaxeChipHardCap(m_chipTempMax, chipHardCapMHz);\n        } else {\n            invalidChipPolls++;\n            if (invalidChipPolls >= 3) chipHardCapMHz = 525;\n        }\n        vrHardCapMHz = vrTempValid ? nerdOctaxeVrHardCap(vrMax, vrHardCapMHz) : vrHardCapMHz;\n\n        int runtimeMHz = autoEnabled ? autoMHz : configuredMHz;\n        if (chipHardCapMHz > 0) runtimeMHz = std::min(runtimeMHz, chipHardCapMHz);\n        if (vrHardCapMHz > 0) runtimeMHz = std::min(runtimeMHz, vrHardCapMHz);\n        if (invalidChipPolls >= 3) runtimeMHz = 525;\n\n        // When AUTO is active, a hard safety cap also pulls its internal state\n        // down so recovery remains gradual after temperatures fall.\n        if (autoEnabled) {\n            autoMHz = std::min(autoMHz, runtimeMHz);\n            autoMHz = std::max(autoMHz, 525);\n        }\n\n        // checkAsicFrequencyChanged() runs earlier in this loop. If the user edits\n        // settings while the governor is limiting, re-apply the effective value.\n        const bool modeChanged = autoEnabled != lastAutoEnabled;\n        const bool mustReapply = (configuredChanged || modeChanged) && runtimeMHz != configuredMHz;\n        if (!m_shutdown && m_board->isInitialized() &&\n            (runtimeMHz != lastRuntimeMHz || mustReapply)) {\n            if (m_board->setAsicFrequency((float) runtimeMHz)) {\n                ESP_LOGW(TAG,\n                         "Thermal governor: auto=%d target=%dC chip=%.1fC vr=%.1fC configured=%dMHz autoMHz=%dMHz chipCap=%dMHz vrCap=%dMHz runtime=%dMHz",\n                         autoEnabled ? 1 : 0, targetTemp, m_chipTempMax, vrMax, configuredMHz, autoMHz,\n                         chipHardCapMHz, vrHardCapMHz, runtimeMHz);\n                lastRuntimeMHz = runtimeMHz;\n            } else {\n                ESP_LOGE(TAG, "Thermal governor failed to set %dMHz", runtimeMHz);\n            }\n        }\n\n        lastConfiguredMHz = configuredMHz;\n        lastAutoEnabled = autoEnabled;\n#endif\n\n        // Run fan controller (reads RPM, drives fans, updates overheat flags)'''
src = replace_once(src, loop_anchor, loop_replacement, "thermal-governor insertion anchor")
path.write_text(src)


# -----------------------------------------------------------------------------
# /api/v2/settings backend fields
# -----------------------------------------------------------------------------
path = Path("main/http_server/v2/handler_v2_settings.cpp")
src = path.read_text()

get_anchor = '''    {\n        JsonArray arr = doc["voltageOptions"].to<JsonArray>();\n        for (uint32_t v : board->getVoltageOptions()) arr.add(v);\n    }\n\n    // --- stratum / pools ---'''
get_replacement = '''    {\n        JsonArray arr = doc["voltageOptions"].to<JsonArray>();\n        for (uint32_t v : board->getVoltageOptions()) arr.add(v);\n    }\n#ifdef NERDOCTAXEGAMMA\n    doc["thermalAutoEnabled"] = Config::cfgGetBool(NVS_CONFIG_THERMAL_AUTO, true);\n    doc["thermalTargetTemp"] = Config::cfgGetU16(NVS_CONFIG_THERMAL_TARGET, 68);\n#endif\n\n    // --- stratum / pools ---'''
src = replace_once(src, get_anchor, get_replacement, "v2 settings GET ASIC anchor")

patch_anchor = '''    if (doc["vrFrequency"].is<uint32_t>()) {\n        Config::setVrFrequency(doc["vrFrequency"].as<uint32_t>());\n    }\n\n    // --- display ---'''
patch_replacement = '''    if (doc["vrFrequency"].is<uint32_t>()) {\n        Config::setVrFrequency(doc["vrFrequency"].as<uint32_t>());\n    }\n#ifdef NERDOCTAXEGAMMA\n    if (doc["thermalAutoEnabled"].is<bool>()) {\n        Config::cfgSetBool(NVS_CONFIG_THERMAL_AUTO, doc["thermalAutoEnabled"].as<bool>());\n    }\n    if (doc["thermalTargetTemp"].is<uint16_t>()) {\n        uint16_t target = doc["thermalTargetTemp"].as<uint16_t>();\n        if (target >= 60 && target <= 69) {\n            Config::cfgSetU16(NVS_CONFIG_THERMAL_TARGET, target);\n        }\n    }\n#endif\n\n    // --- display ---'''
src = replace_once(src, patch_anchor, patch_replacement, "v2 settings PATCH ASIC anchor")
path.write_text(src)


# -----------------------------------------------------------------------------
# AxeOS settings model
# -----------------------------------------------------------------------------
path = Path("main/http_server/axe-os/src/app/models/ISettingsV2.ts")
src = path.read_text()
anchor = '''    absMinCoreVoltage: number;\n    absMaxCoreVoltage: number;\n\n    // Stratum / pools'''
replacement = '''    absMinCoreVoltage: number;\n    absMaxCoreVoltage: number;\n\n    // NerdOCTAXE-Gamma adaptive thermal governor\n    thermalAutoEnabled?: boolean;\n    thermalTargetTemp?: number;\n\n    // Stratum / pools'''
src = replace_once(src, anchor, replacement, "AxeOS settings model anchor")
path.write_text(src)


# -----------------------------------------------------------------------------
# AxeOS settings component logic
# -----------------------------------------------------------------------------
path = Path("main/http_server/axe-os/src/app/pages/edit/edit.component.ts")
src = path.read_text()

prop_anchor = '''  public defaultVrFrequency: number = 0;\n  public fanCount: number = 1;'''
prop_replacement = '''  public defaultVrFrequency: number = 0;\n  public fanCount: number = 1;\n  public isNerdOctaxeGamma: boolean = false;'''
src = replace_once(src, prop_anchor, prop_replacement, "edit component property anchor")

model_anchor = '''        this.asicModel = info.asicModel;\n\n        this.defaultFrequency = info.defaultFrequency ?? 0;'''
model_replacement = '''        this.asicModel = info.asicModel;\n        const normalizedDeviceModel = (info.deviceModel || '').replace(/γ/g, 'Gamma').replace(/\\s+/g, '').toLowerCase();\n        this.isNerdOctaxeGamma = normalizedDeviceModel.includes('nerdoctaxe-gamma') || normalizedDeviceModel.includes('nerdoctaxegamma');\n\n        this.defaultFrequency = info.defaultFrequency ?? 0;'''
src = replace_once(src, model_anchor, model_replacement, "device model detection anchor")

form_anchor = '''          coreVoltage: [info.coreVoltage, [Validators.min(info.absMinCoreVoltage || 1005), Validators.max(info.absMaxCoreVoltage || 1400), Validators.required]],\n          frequency: [info.frequency, [Validators.required]],\n          jobInterval: [info.jobInterval, [Validators.required]],'''
form_replacement = '''          coreVoltage: [info.coreVoltage, [Validators.min(info.absMinCoreVoltage || 1005), Validators.max(info.absMaxCoreVoltage || 1400), Validators.required]],\n          frequency: [info.frequency, [Validators.required]],\n          thermalAutoEnabled: [info.thermalAutoEnabled ?? true],\n          thermalTargetTemp: [info.thermalTargetTemp ?? 68, [Validators.min(60), Validators.max(69), Validators.required]],\n          jobInterval: [info.jobInterval, [Validators.required]],'''
src = replace_once(src, form_anchor, form_replacement, "thermal form controls anchor")

payload_anchor = '''      frequency: f.frequency,\n      coreVoltage: f.coreVoltage,\n      vrFrequency: f.vrFrequency,\n      jobInterval: f.jobInterval,'''
payload_replacement = '''      frequency: f.frequency,\n      coreVoltage: f.coreVoltage,\n      vrFrequency: f.vrFrequency,\n      jobInterval: f.jobInterval,'''
src = replace_once(src, payload_anchor, payload_replacement, "ASIC payload anchor")

return_anchor = '''    // WiFi password — allow empty, strip masked\n    const wifiPass = f.wifiPass == null ? '' : f.wifiPass;'''
return_replacement = '''    // NerdOCTAXE-Gamma adaptive thermal governor\n    if (this.isNerdOctaxeGamma) {\n      payload.thermalAutoEnabled = !!f.thermalAutoEnabled;\n      payload.thermalTargetTemp = Math.max(60, Math.min(69, Number(f.thermalTargetTemp) || 68));\n    }\n\n    // WiFi password — allow empty, strip masked\n    const wifiPass = f.wifiPass == null ? '' : f.wifiPass;'''
src = replace_once(src, return_anchor, return_replacement, "thermal payload insertion anchor")
path.write_text(src)


# -----------------------------------------------------------------------------
# AxeOS visible controls
# -----------------------------------------------------------------------------
path = Path("main/http_server/axe-os/src/app/pages/edit/edit.component.html")
src = path.read_text()
anchor = '''                <ng-container *ngIf="supportLevel >= 2">\n                    <div class="form-row">\n                        <label for="jobInterval" class="form-label">Job Interval:</label>'''
replacement = '''                <ng-container *ngIf="isNerdOctaxeGamma">\n                    <div class="form-row">\n                        <label class="form-label">AUTO Thermal Mode:</label>\n                        <div class="form-control-wrapper">\n                            <nb-checkbox formControlName="thermalAutoEnabled">Adaptive frequency control</nb-checkbox><br />\n                            <small>Automatically lowers ASIC frequency when hot and restores it gradually when cool. Hard thermal safety caps remain active even when AUTO is off.</small>\n                        </div>\n                    </div>\n                    <div class="form-row" *ngIf="form.controls['thermalAutoEnabled'].value">\n                        <label for="thermalTargetTemp" class="form-label">Target ASIC temperature:</label>\n                        <div class="form-control-wrapper">\n                            <input nbInput id="thermalTargetTemp" formControlName="thermalTargetTemp" type="number" min="60" max="69" step="1" />\n                            <span>&nbsp;°C</span><br />\n                            <small>60–69 °C. Default: 68 °C. The configured MHz above remains the maximum frequency ceiling.</small>\n                        </div>\n                    </div>\n                </ng-container>\n\n                <ng-container *ngIf="supportLevel >= 2">\n                    <div class="form-row">\n                        <label for="jobInterval" class="form-label">Job Interval:</label>'''
src = replace_once(src, anchor, replacement, "AxeOS mining controls anchor")
path.write_text(src)

print("Applied NerdOCTAXE-Gamma AUTO v3 governor, persistent settings and AxeOS controls")
