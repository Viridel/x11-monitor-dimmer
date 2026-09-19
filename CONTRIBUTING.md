# Contributing

Thanks for helping continue development of X11 Monitor Dimmer.

## Project state

**v0.85 is the final X11 release from the original author, Viridel48.** The application is being left to the community for Wayland support, broader display-server compatibility, maintenance, and future enhancements.

`v1.0` is intentionally reserved for a future release that adds Wayland / broader display-server support.

## Priorities

Good contributions are likely to be:

- focused and easy to review
- low-risk to confirmed-working X11 behavior
- tested on the environment they claim to support
- respectful of the existing controller geometry and runtime workflow

## Please avoid

- broad rewrites of working modules without a clear need
- changing the established Set / Restore or overlay lifecycle casually
- leaving a 100% / disabled overlay alive as a transparent no-op window
- claiming Wayland support before it is implemented and validated
- changing display ordering into a user-managed feature unless there is a compelling reason

## Display naming policy

Display label precedence is:

1. Custom name
2. EDID/system display name
3. `Display #N`

The controller displays the resolved name and X11 port on two lines. Custom names always win. If EDID naming is unavailable, dimming still functions normally and the generic `Display #N` fallback is used.

## Project identity

Future developers are respectfully asked to retain the original project accreditation:

**Originally authored by Viridel48 through v0.85.**

This is a request from the original author and is not intended as an additional licensing condition.

The **For the Animals** messaging should retain its intent. Genuine enhancements such as location-aware shelter information, websites, or contact details are welcome.

## Before submitting

Please confirm that:

- Python files compile cleanly
- the controller opens, hides, and reopens correctly
- tray Show / Hide / Quit still works
- per-display dimming still works independently
- Default 1 and Default 2 remain independent
- 100% / Dimmer Off fully terminates the relevant overlay
- display naming fallback still works if EDID data is unavailable
- popup geometry remains usable at the resolutions / scaling you tested

When opening a PR or issue, include what changed, why it changed, what you tested, and the environment you tested on.
