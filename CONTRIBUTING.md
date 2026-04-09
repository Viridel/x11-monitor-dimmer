# Contributing

Thanks for helping continue development.

## Project state

This project is being released in a stable state for the original author's environment.  
Please treat confirmed-working behavior as valuable, especially where geometry and runtime flow are concerned.

## Priorities

Good contributions are likely to be:

- isolated
- easy to review
- low-risk
- respectful of already-working modules

## Please avoid

- broad rewrites of `ui_window.py` unless clearly necessary
- destabilizing `ui_alignment.py` without strong reason
- changing working runtime toggle/tray behavior casually
- claiming Wayland support before it is actually implemented and validated

## Labeling policy

Default monitor label precedence should remain:

1. Custom override
2. DDC/EDID model label in format `ModelName (Port)`
3. Generic fallback `Monitor (Port)`

## Versioning note

`v1.0` should remain reserved for a release that supports both:

- X11
- Wayland

## Recommended contribution style

Keep changes small and focused.

Examples of good change scopes:

- one bug fix
- one UI refinement
- one dependency/install improvement
- one module extraction
- one desktop integration improvement

## Before submitting

Please make sure:

- Python files compile cleanly
- the dimmer still opens and closes correctly
- tray behavior still works if tray support is enabled
- panel/launcher toggle behavior still works
- no-working overlay behavior is not left running pointlessly

## Communication

When opening a PR or issue, include:

- what changed
- why it changed
- what was tested
- what environment you tested on
