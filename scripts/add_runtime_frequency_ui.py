from pathlib import Path


def replace_once(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        raise SystemExit(f"Runtime frequency UI patch failed: {label} not found")
    return src.replace(old, new, 1)


# -----------------------------------------------------------------------------
# Export the governor's successfully-applied runtime frequency.
# -----------------------------------------------------------------------------
path = Path("main/tasks/power_management_task.cpp")
src = path.read_text()

anchor = '''#ifdef NERDOCTAXEGAMMA
// NerdOCTAXE-Gamma adaptive runtime governor.'''
replacement = '''#ifdef NERDOCTAXEGAMMA
// Last frequency successfully applied to the ASIC by the adaptive governor.
// This is intentionally separate from Board::getAsicFrequency(), which remains
// the user-configured ceiling loaded from NVS.
static volatile int g_nerdOctaxeRuntimeMHz = 0;
int nerdOctaxeGetRuntimeMHz()
{
    return g_nerdOctaxeRuntimeMHz;
}

// NerdOCTAXE-Gamma adaptive runtime governor.'''
src = replace_once(src, anchor, replacement, "runtime frequency export")

anchor = '''                lastRuntimeMHz = runtimeMHz;
            } else {'''
replacement = '''                lastRuntimeMHz = runtimeMHz;
                g_nerdOctaxeRuntimeMHz = runtimeMHz;
            } else {'''
src = replace_once(src, anchor, replacement, "runtime frequency update")
path.write_text(src)


# -----------------------------------------------------------------------------
# Return both actual runtime frequency and configured ceiling in dashboard API.
# -----------------------------------------------------------------------------
path = Path("main/http_server/v2/handler_v2_dashboard.cpp")
src = path.read_text()

anchor = '''static const char *TAG = "http_v2_dashboard";'''
replacement = '''static const char *TAG = "http_v2_dashboard";

#ifdef NERDOCTAXEGAMMA
int nerdOctaxeGetRuntimeMHz();
#endif'''
src = replace_once(src, anchor, replacement, "dashboard runtime getter declaration")

anchor = '''        perf["frequency"]       = board->getAsicFrequency();'''
replacement = '''#ifdef NERDOCTAXEGAMMA
        const int runtimeMHz = nerdOctaxeGetRuntimeMHz();
        perf["configuredFrequency"] = board->getAsicFrequency();
        perf["frequency"] = runtimeMHz > 0 ? runtimeMHz : board->getAsicFrequency();
#else
        perf["frequency"] = board->getAsicFrequency();
#endif'''
src = replace_once(src, anchor, replacement, "dashboard frequency fields")
path.write_text(src)


# -----------------------------------------------------------------------------
# AxeOS dashboard model.
# -----------------------------------------------------------------------------
path = Path("main/http_server/axe-os/src/app/models/IDashboardV2.ts")
src = path.read_text()
anchor = '''    frequency: number;
    asicCount: number;'''
replacement = '''    frequency: number;              // actual/runtime MHz
    configuredFrequency?: number;   // user-selected ceiling (NerdOCTAXE-Gamma AUTO)
    asicCount: number;'''
src = replace_once(src, anchor, replacement, "dashboard TypeScript model")
path.write_text(src)


# -----------------------------------------------------------------------------
# Home tile: Current Frequency now displays runtime MHz and, when available,
# the configured ceiling beside it.
# -----------------------------------------------------------------------------
path = Path("main/http_server/axe-os/src/app/pages/home/home.component.html")
src = path.read_text()
anchor = '''                  <div class="power-bar__value">{{ info.performance.frequency | number: '1.0-0' }}<span
                    class="unit">&nbsp;MHz</span></div>'''
replacement = '''                  <div class="power-bar__value">{{ info.performance.frequency | number: '1.0-0' }}<span
                    class="unit">&nbsp;MHz</span><span
                    class="unit" *ngIf="info.performance.configuredFrequency !== undefined && info.performance.configuredFrequency !== null">&nbsp;· max {{ info.performance.configuredFrequency | number: '1.0-0' }} MHz</span></div>'''
src = replace_once(src, anchor, replacement, "home runtime frequency value")
path.write_text(src)

print("Runtime frequency UI added: dashboard shows actual MHz plus configured ceiling")
