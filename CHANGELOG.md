# Changelog

## v0.75
- Runtime flow completed into a self-contained desktop-style application model
- Panel launcher toggle flow finalized
- Tray support added with Show / Hide and Quit
- Quit helper added
- `ui_animals.py` extracted from `ui_window.py`
- Read-only EDID/DDCU model-name integration finalized in live UI
- Default display label format finalized as `ModelName (Port)`
- Label precedence locked as:
  1. Custom override
  2. DDC/EDID model label in format `ModelName (Port)`
  3. Generic fallback `Monitor (Port)`
- Optional `ddcutil` installer helper added and tested
- Backup / locked-state workflow matured for milestone preservation

## v0.60
- DDCU scope clarified and narrowed to **read-only model retrieval**
- Full DDC/CI brightness control explicitly removed from milestone scope
- `ddcu.py` created for read-only probing and EDID/model resolution
- Verified output-to-model mapping from the live display stack
- Model-name retrieval confirmed working without requiring successful VCP brightness control
- EDID-backed labels verified for:
  - `ARZOPA (DP-3)`
  - `TOSHIBA-TV (DP-5)`

## v0.50
- `for_the_animals` feature implemented
- Inline support-the-author message added to the controller window
- Launch-count-based reminder logic finalized
- Reminder behavior finalized as:
  - first appearance at open 100
  - **Remind me later** = +10 opens
  - **No thanks** = +200 opens
- `for_the_animals.py` established as the policy/state module
- Feature intentionally kept non-popup, bounded, and low-frequency

## Pre-v0.50 foundation work
This is where the bulk of the project’s engineering effort occurred.

### Core dimmer architecture
- Project established as an **X11 overlay dimmer** rather than a gamma/colour-shift tool
- Real per-monitor overlay dimming made functional
- Overlay lifecycle stabilized so functionally-off dim states do not leave pointless no-op behavior behind
- Persistent configuration support established

### Main controller behavior
- Per-monitor slider workflow implemented
- Per-monitor **Off** behavior implemented
- **Save as Default** and **Restore Default** behavior implemented
- Default validation rules added, including lower-bound restrictions for saved defaults
- Error messaging refined and kept inline instead of disruptive popups

### Naming and monitor identity
- Manual custom monitor naming implemented
- Reset Device Names behavior added
- Fallback naming behavior established
- Monitor naming and persistence behavior stabilized before later EDID/model integration

### Windowing and placement
- Host monitor selection implemented
- Host monitor persistence added
- Controller movement between monitors implemented
- Top-level always-on-top style behavior implemented
- Top-middle placement behavior established
- Fade show / fade hide behavior implemented
- Fade transition between host monitors implemented

### UI refactor and alignment work
- Original UI layout went through multiple restructuring passes
- Per-row independent layout approach was replaced with a **shared-grid layout**
- Column alignment problems were resolved
- Bottom row alignment and button positioning were resolved
- Width/profile tuning for 1080p and 4K usage was repeatedly refined
- Height/spacing behavior was compacted and stabilized

### Geometry separation
- Geometry logic was extracted from the main window into `ui_alignment.py`
- This separation resolved long-standing centering and size-application issues
- Confirmed working host alignment achieved on both:
  - `DP-3`
  - `DP-5`
- Final confirmed geometry state stabilized after multiple troubleshooting passes

### Runtime and control model
- Single-instance behavior implemented
- Signal-based reopen/toggle flow implemented
- Hide vs reopen logic stabilized
- Close-button behavior finalized as **hide**, not terminate
- Toggle launcher wrapper added and verified
- Desktop-style usage model became possible before tray support was added

### Project structure maturation
- Codebase gradually split into focused modules instead of one growing window file
- `ui_rows.py` established for row widgets
- `ui_alignment.py` established for geometry
- Later milestones continued this modularization, but the core structural cleanup began here

## Notes
- `v1.0` is intentionally reserved for a release that supports both X11 and Wayland.
- The project is currently considered stable for the original author’s configuration and is being released for community continuation.
