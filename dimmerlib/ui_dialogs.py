from __future__ import annotations

from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Pango, GdkPixbuf, GLib, Gdk

from .config import MAX_CUSTOM_NAME, save_config


ABOUT_CREDITS_RESPONSE = 1001
ABOUT_HISTORY_RESPONSE = 1002
ABOUT_ROADMAP_RESPONSE = 1003


_EDITABLE_ENTRY_CSS = b"""
entry.editable-name-field {
    background-color: #4a4a4a;
    color: #f2f2f2;
}
entry.editable-name-field:focus {
    background-color: #515151;
}
"""


_PRIMARY_POPUP_CSS = b"""
.primary-popup-header {
    background-color: #202124;
    border-bottom: 1px solid #303136;
}
.primary-popup-title {
    color: #9a9a9a;
    font-weight: bold;
}
button.primary-popup-close {
    color: #9a9a9a;
    background-image: none;
    background-color: transparent;
    border-color: transparent;
    box-shadow: none;
}
button.primary-popup-close:hover {
    color: #c3c3c3;
}
"""


_ICON_CANDIDATES = (
    Path.home() / ".local" / "share" / "x11-monitor-dimmer" / "icons" / "x11-monitor-dimmer.png",
    Path("/usr/share/x11-monitor-dimmer/icons/x11-monitor-dimmer.png"),
    Path("/usr/share/icons/hicolor/256x256/apps/x11-monitor-dimmer.png"),
)


def _hide_native_action_area(dialog):
    """Remove Gtk.Dialog's native action strip; the shared shell owns actions."""
    action = dialog.get_action_area()
    for child in list(action.get_children()):
        action.remove(child)
    action.set_no_show_all(True)
    action.hide()


class PrimaryPopupDialog(Gtk.Dialog):
    """One shell for Name Displays, Name Defaults, and About.

    The parent window supplies the exact horizontal geometry. This class owns
    only the common chrome and content-tight vertical behavior, ensuring all
    three primary popups remain visually identical in construction.
    """

    def __init__(self, app, title, close_response):
        super().__init__(title=title, transient_for=app, modal=True)
        self.app = app
        self._locked_width = None
        self._width_fitters = []

        # Client-side chrome means the requested window width is the *actual*
        # outer popup width; there is no hidden WM decoration to spill into Set.
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_border_width(0)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_position(Gtk.WindowPosition.NONE)
        self.set_gravity(Gdk.Gravity.NORTH_WEST)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_keep_above(True)
        _hide_native_action_area(self)

        outer = self.get_content_area()
        outer.set_border_width(0)
        outer.set_spacing(0)

        header = Gtk.Grid()
        header.set_column_homogeneous(False)
        header.set_column_spacing(0)
        header.set_margin_start(8)
        header.set_margin_end(6)
        header.set_margin_top(5)
        header.set_margin_bottom(5)

        shell_css = Gtk.CssProvider()
        shell_css.load_from_data(_PRIMARY_POPUP_CSS)
        header_style = header.get_style_context()
        header_style.add_class('primary-popup-header')
        header_style.add_provider(shell_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        left_pad = Gtk.Box()
        left_pad.set_size_request(36, 30)
        header.attach(left_pad, 0, 0, 1, 1)

        title_label = Gtk.Label(label=title)
        title_label.set_hexpand(True)
        title_label.set_halign(Gtk.Align.FILL)
        title_label.set_xalign(0.5)
        title_label.modify_font(Pango.FontDescription('Sans Bold 10'))
        title_style = title_label.get_style_context()
        title_style.add_class('primary-popup-title')
        title_style.add_provider(shell_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        header.attach(title_label, 1, 0, 1, 1)

        close_btn = Gtk.Button(label='×')
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.set_size_request(36, 30)
        close_btn.set_tooltip_text('Close')
        close_style = close_btn.get_style_context()
        close_style.add_class('primary-popup-close')
        close_style.add_provider(shell_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        close_btn.connect('clicked', lambda *_args: self.response(close_response))
        header.attach(close_btn, 2, 0, 1, 1)

        outer.pack_start(header, False, False, 0)
        outer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.body.set_border_width(10)
        self.body.set_hexpand(True)
        outer.pack_start(self.body, False, False, 0)

    def add_width_fitter(self, callback):
        self._width_fitters.append(callback)

    def lock_width(self, width):
        """Force one exact shell width; children must fit inside it."""
        width = max(1, int(width))
        self._locked_width = width

        # First force every content set to accept the shell's available width.
        # This removes the content-driven minimum-width growth that previously
        # made Name Defaults/About wider and pushed into the Set column.
        for callback in tuple(self._width_fitters):
            callback(width)

        geometry = Gdk.Geometry()
        geometry.min_width = width
        geometry.max_width = width
        self.set_geometry_hints(
            None,
            geometry,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE,
        )
        self.set_default_size(width, -1)
        self.set_size_request(width, -1)
        self.resize(width, 1)

    def refit_height(self):
        """Collapse/grow to the natural content height without changing width."""
        if self._locked_width is None:
            return False
        self.resize(int(self._locked_width), 1)
        return False

    def bind_vertical_expander(self, expander):
        """Keep Read more content-tight when expanded or collapsed."""
        expander.set_resize_toplevel(True)
        expander.connect(
            'notify::expanded',
            lambda *_args: GLib.idle_add(self.refit_height),
        )


def _two_line_header(primary, secondary=None):
    label = Gtk.Label()
    if secondary:
        label.set_text(f"{primary}\n{secondary}")
    else:
        label.set_text(primary)
    label.set_justify(Gtk.Justification.CENTER)
    label.set_xalign(0.5)
    label.set_halign(Gtk.Align.FILL)
    label.set_hexpand(True)
    label.modify_font(Pango.FontDescription("Sans Bold 9"))
    return label


def _entry(text="", *, editable=False, max_length=None):
    entry = Gtk.Entry()
    entry.set_text(str(text))
    entry.set_hexpand(True)
    # Keep the natural minimum deliberately small. The live main-window anchor
    # determines the popup width; the three columns divide that width evenly.
    entry.set_width_chars(1)

    if editable:
        if max_length is not None:
            entry.set_max_length(int(max_length))
        provider = Gtk.CssProvider()
        provider.load_from_data(_EDITABLE_ENTRY_CSS)
        style = entry.get_style_context()
        style.add_class("editable-name-field")
        style.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    else:
        entry.set_editable(False)
        entry.set_can_focus(False)

    return entry


def _info_label(text):
    label = Gtk.Label(label=text)
    label.set_xalign(0.0)
    label.set_halign(Gtk.Align.FILL)
    label.set_hexpand(True)
    label.set_line_wrap(True)
    label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    # Name Displays is the approved master shell. Long explanatory text must
    # wrap inside that shell rather than increasing the top-level requisition.
    label.set_width_chars(1)
    label.set_max_width_chars(48)
    label.set_size_request(1, -1)
    return label


def _make_name_action_row(dialog, reset_label, reset_callback):
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    row.set_hexpand(True)
    row.set_halign(Gtk.Align.FILL)
    row.set_margin_top(10)

    reset_btn = Gtk.Button(label=reset_label)
    reset_btn.set_hexpand(True)
    reset_btn.set_size_request(1, -1)
    reset_btn.connect("clicked", reset_callback)
    row.pack_start(reset_btn, True, True, 0)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.set_size_request(1, -1)
    cancel_btn.set_hexpand(True)
    cancel_btn.connect("clicked", lambda *_args: dialog.response(Gtk.ResponseType.CANCEL))
    row.pack_start(cancel_btn, True, True, 0)

    save_btn = Gtk.Button(label="Save")
    save_btn.set_size_request(1, -1)
    save_btn.set_hexpand(True)
    save_btn.connect("clicked", lambda *_args: dialog.response(Gtk.ResponseType.OK))
    row.pack_start(save_btn, True, True, 0)

    return row


def _make_about_action_row(dialog):
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    row.set_hexpand(True)
    row.set_halign(Gtk.Align.FILL)
    row.set_homogeneous(True)
    row.set_margin_top(10)

    buttons = (
        ("Credits", ABOUT_CREDITS_RESPONSE),
        ("History\nLog", ABOUT_HISTORY_RESPONSE),
        ("Future\nRoadmap", ABOUT_ROADMAP_RESPONSE),
        ("Close", Gtk.ResponseType.CLOSE),
    )
    for label, response in buttons:
        button = Gtk.Button(label=label)
        child = button.get_child()
        if isinstance(child, Gtk.Label):
            child.set_justify(Gtk.Justification.CENTER)
            child.set_xalign(0.5)
            child.set_halign(Gtk.Align.CENTER)
        button.connect("clicked", lambda _btn, value=response: dialog.response(value))
        row.pack_start(button, True, True, 0)

    return row


def _project_icon(size=82):
    for path in _ICON_CANDIDATES:
        if not path.exists():
            continue
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, True)
            return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception:
            continue
    return Gtk.Image.new_from_icon_name("x11-monitor-dimmer", Gtk.IconSize.DIALOG)


class _ReadOnlyTextDialog(Gtk.Dialog):
    def __init__(self, title, parent, text, *, width=700, height=500):
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_default_size(width, height)
        self.set_border_width(8)
        self.add_button("Close", Gtk.ResponseType.CLOSE)

        content = self.get_content_area()
        content.set_spacing(8)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_left_margin(14)
        text_view.set_right_margin(14)
        text_view.set_top_margin(12)
        text_view.set_bottom_margin(12)
        text_view.get_buffer().set_text(text)

        scroller.add(text_view)
        content.pack_start(scroller, True, True, 0)
        self.show_all()


class NameDisplaysDialog(PrimaryPopupDialog):
    def __init__(self, app):
        super().__init__(app, "Name Displays", Gtk.ResponseType.CANCEL)
        self.entries = {}
        content = self.body

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(7)
        grid.set_column_homogeneous(True)
        grid.set_hexpand(True)
        content.pack_start(grid, False, False, 0)

        grid.attach(_two_line_header("Display", "(read only)"), 0, 0, 1, 1)
        grid.attach(
            _two_line_header("Custom", f"(max {MAX_CUSTOM_NAME} characters)"),
            1, 0, 1, 1,
        )
        grid.attach(_two_line_header("Port", "(read only)"), 2, 0, 1, 1)

        unresolved = []

        for row_index, mon in enumerate(app.monitors, start=1):
            output = mon["output"]
            cfg_mon = app.config.setdefault("monitors", {}).setdefault(output, {})
            automatic_name = app.automatic_display_name(mon)
            custom_name = str(cfg_mon.get("custom_name") or "")[:MAX_CUSTOM_NAME]

            grid.attach(_entry(automatic_name, editable=False), 0, row_index, 1, 1)

            custom_entry = _entry(
                custom_name,
                editable=True,
                max_length=MAX_CUSTOM_NAME,
            )
            self.entries[output] = custom_entry
            grid.attach(custom_entry, 1, row_index, 1, 1)

            grid.attach(_entry(output, editable=False), 2, row_index, 1, 1)

            if not app.edid_display_name(mon):
                unresolved.append(mon)

        if unresolved:
            summary = _info_label(
                "Display name unavailable from the system configuration. This does not affect "
                "dimming functionality; automatic naming is only for ease of reference. The "
                "simplest solution is to enter a Custom name."
            )
            content.pack_start(summary, False, False, 0)

            expander = Gtk.Expander(label="Read more")
            self.bind_vertical_expander(expander)
            details = _info_label(
                "The display did not provide a usable EDID model name through X11. EDID is "
                "identification information supplied by the display; the dimmer does not depend "
                "on that information to control the overlay, so all dimming functions remain "
                "available.\n\n"
                "This can occur with some KVM switches, docks, adapters, virtual displays, "
                "graphics-driver paths, cables, ports, or displays that do not expose their "
                "identification data correctly. Connecting the display directly, trying another "
                "port or cable, power-cycling the display, or checking the graphics-driver "
                "configuration may help, but there may be no operating-system-side remedy.\n\n"
                "Advanced DDC tools can sometimes retrieve identification information when X11 "
                "does not expose it, but this is not guaranteed. Hardware that blocks or alters "
                "EDID, including some KVMs and adapters, can also block DDC communication."
            )
            details.set_margin_start(18)
            details.set_margin_top(6)
            expander.add(details)
            content.pack_start(expander, False, False, 0)
        else:
            content.pack_start(
                _info_label("A blank Custom name uses the Display name."),
                False,
                False,
                0,
            )

        self.action_row = _make_name_action_row(
            self,
            "Reset Custom Names to Display Defaults",
            self._on_reset,
        )
        content.pack_start(self.action_row, False, False, 0)
        self.name_grid = grid
        self.add_width_fitter(self._fit_shell_width)

    def _fit_shell_width(self, shell_width):
        inner = max(240, int(shell_width) - 20)
        grid_width = max(180, inner)
        self.name_grid.set_size_request(grid_width, -1)
        self.action_row.set_size_request(inner, -1)

        # Three equal columns must fit inside the fixed shell.  Explicitly
        # lower every child's minimum so GTK cannot widen the top-level.
        col_width = max(1, (grid_width - 16) // 3)
        for child in self.name_grid.get_children():
            child.set_size_request(col_width, -1)

    def _on_reset(self, *_args):
        for entry in self.entries.values():
            entry.set_text("")

    def commit(self):
        for output, entry in self.entries.items():
            cfg_mon = self.app.config.setdefault("monitors", {}).setdefault(output, {})
            custom_name = entry.get_text().strip()[:MAX_CUSTOM_NAME]
            if custom_name:
                cfg_mon["custom_name"] = custom_name
            else:
                cfg_mon.pop("custom_name", None)
        save_config(self.app.config)
        self.app.refresh_display_names()


class NameDefaultsDialog(PrimaryPopupDialog):
    def __init__(self, app):
        super().__init__(app, "Name Defaults", Gtk.ResponseType.CANCEL)
        self.entries = {}
        self.previews = {}
        content = self.body

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(7)
        grid.set_column_homogeneous(True)
        grid.set_hexpand(True)
        content.pack_start(grid, False, False, 0)

        grid.attach(_two_line_header("Default", "(read only)"), 0, 0, 1, 1)
        grid.attach(
            _two_line_header("Custom", f"(max {MAX_CUSTOM_NAME} characters)"),
            1, 0, 1, 1,
        )
        grid.attach(_two_line_header("Preview", "(read only)"), 2, 0, 1, 1)

        stored = app.config.setdefault("default_names", {})
        for row_index, slot in enumerate((1, 2), start=1):
            built_in = f"Default {slot}"
            custom = str(stored.get(str(slot)) or "")[:MAX_CUSTOM_NAME]

            grid.attach(_entry(built_in, editable=False), 0, row_index, 1, 1)

            custom_entry = _entry(
                custom,
                editable=True,
                max_length=MAX_CUSTOM_NAME,
            )
            custom_entry.connect("changed", self._on_changed, slot)
            self.entries[slot] = custom_entry
            grid.attach(custom_entry, 1, row_index, 1, 1)

            preview = _entry(custom or built_in, editable=False)
            self.previews[slot] = preview
            grid.attach(preview, 2, row_index, 1, 1)

        self.info_label = _info_label(
            "A blank Custom name uses Default 1 or Default 2. "
            "Custom names change labels only; saved brightness values are unaffected."
        )
        content.pack_start(self.info_label, False, False, 0)

        self.action_row = _make_name_action_row(
            self,
            "Reset Custom Default Names",
            self._on_reset,
        )
        content.pack_start(self.action_row, False, False, 0)
        self.name_grid = grid
        self.add_width_fitter(self._fit_shell_width)

    def _fit_shell_width(self, shell_width):
        # Exact same body budget as Name Displays. Nothing in this content set
        # is permitted to create a wider top-level requisition.
        inner = max(240, int(shell_width) - 20)
        grid_width = max(180, inner)
        self.name_grid.set_size_request(grid_width, -1)
        self.info_label.set_size_request(inner, -1)
        self.action_row.set_size_request(inner, -1)
        col_width = max(1, (grid_width - 16) // 3)
        for child in self.name_grid.get_children():
            child.set_size_request(col_width, -1)

    def _on_changed(self, entry, slot):
        custom = entry.get_text().strip()[:MAX_CUSTOM_NAME]
        self.previews[slot].set_text(custom or f"Default {slot}")

    def _on_reset(self, *_args):
        for entry in self.entries.values():
            entry.set_text("")

    def commit(self):
        stored = self.app.config.setdefault("default_names", {})
        for slot, entry in self.entries.items():
            custom = entry.get_text().strip()[:MAX_CUSTOM_NAME]
            if custom:
                stored[str(slot)] = custom
            else:
                stored.pop(str(slot), None)
        save_config(self.app.config)
        self.app.refresh_default_names()


class AboutDialog(PrimaryPopupDialog):
    def __init__(self, app):
        super().__init__(app, "About", Gtk.ResponseType.CLOSE)
        content = self.body

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        body.set_hexpand(True)
        body.set_halign(Gtk.Align.FILL)

        icon = _project_icon(82)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        body.pack_start(icon, False, False, 4)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label()
        title.set_markup("<b>X11 Monitor Dimmer</b>")
        title.set_xalign(0.0)
        title.set_halign(Gtk.Align.FILL)
        title.set_hexpand(True)
        title.set_width_chars(1)
        title.set_size_request(1, -1)
        title.modify_font(Pango.FontDescription("Sans 13"))
        text_box.pack_start(title, False, False, 0)

        version = Gtk.Label(label="Version 0.85")
        version.set_xalign(0.0)
        version.set_halign(Gtk.Align.FILL)
        version.set_hexpand(True)
        version.set_width_chars(1)
        version.set_size_request(1, -1)
        text_box.pack_start(version, False, False, 0)
        version.set_margin_bottom(8)

        description = Gtk.Label(
            label="A lightweight per-monitor overlay dimmer\nfor Linux X11"
        )
        description.set_xalign(0.0)
        description.set_halign(Gtk.Align.FILL)
        description.set_hexpand(True)
        description.set_line_wrap(True)
        description.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        description.set_width_chars(1)
        description.set_max_width_chars(36)
        description.set_size_request(1, -1)
        text_box.pack_start(description, False, False, 0)

        body.pack_start(text_box, True, True, 0)
        content.pack_start(body, False, False, 0)
        self.about_body = body
        self.about_text_box = text_box
        self.about_title = title
        self.about_version = version
        self.about_description = description
        self.about_actions = _make_about_action_row(self)
        content.pack_start(self.about_actions, False, False, 0)
        self.add_width_fitter(self._fit_shell_width)

    def _fit_shell_width(self, shell_width):
        # Name Displays is the master shell. About is not allowed to contribute
        # a larger horizontal minimum; every child must shrink/wrap inside it.
        inner = max(240, int(shell_width) - 20)
        text_width = max(1, inner - 110)

        self.about_body.set_size_request(1, -1)
        self.about_text_box.set_size_request(text_width, -1)
        self.about_title.set_size_request(1, -1)
        self.about_version.set_size_request(1, -1)
        self.about_description.set_size_request(1, -1)
        self.about_actions.set_size_request(1, -1)


class CreditsDialog(_ReadOnlyTextDialog):
    def __init__(self, parent):
        text = (
            "Originally authored by Viridel48 through v0.85.\n\n"
            "If this tool has been useful to you, please consider showing appreciation by "
            "donating to a local animal shelter or cruelty-prevention organization.\n\n"
            "Original project accreditation\n\n"
            "Consistent with the attribution principles recognized in GPLv3 Section 7(b), "
            "future developers are respectfully asked to retain the original project "
            "accreditation through all future updates and enhancements: Originally authored "
            "by Viridel48 through v0.85.\n\n"
            "This is a request from the original author and is not intended as an additional "
            "licensing condition."
        )
        super().__init__(
            "X11 Monitor Dimmer — Credits",
            parent,
            text,
            width=650,
            height=380,
        )


class FutureRoadmapDialog(_ReadOnlyTextDialog):
    def __init__(self, parent):
        text = (
            "Future Roadmap\n\n"
            "v0.85 is the final X11 release planned from the original author, Viridel48. "
            "Active development by the original author ends here. The project is being left "
            "to the community for Wayland support, future display-server or operating-system "
            "structures, compatibility work, and other enhancements, with no expectation of "
            "compensation to the original author.\n\n"
            "Planned milestone\n\n"
            "v1.0 — reserved for Wayland support and/or broader display-server compatibility "
            "implemented by future community developers.\n\n"
            "Future compatibility and naming\n\n"
            "If future development adds Wayland or broader platform compatibility, the 'X11' "
            "portion of the application name may be replaced with a more universally "
            "representative name.\n\n"
            "Community-development intent\n\n"
            "The original author's intention is that the application remain freely available "
            "and not be converted into software sold through purchase, subscription, paid "
            "feature access, or another monetary structure. This is an author preference, not "
            "an additional GPL licensing condition.\n\n"
            "For the Animals messaging should remain part of the project and retain its intent. "
            "Definitive enhancements are encouraged where they improve usefulness, including "
            "location-aware shelter information, websites, or contact details.\n\n"
            "Consistent with the attribution principles recognized in GPLv3 Section 7(b), "
            "future developers are respectfully asked to retain the original project "
            "accreditation through all future updates and enhancements: Originally authored "
            "by Viridel48 through v0.85. This is a request from the original author and is not "
            "intended as an additional licensing condition."
        )
        super().__init__(
            "X11 Monitor Dimmer — Future Roadmap",
            parent,
            text,
            width=720,
            height=520,
        )


class HistoryLogDialog(_ReadOnlyTextDialog):
    def __init__(self, parent):
        history_candidates = (
            Path.home() / ".local" / "share" / "x11-monitor-dimmer" / "CHANGELOG.md",
            Path("/usr/share/doc/x11-monitor-dimmer/CHANGELOG.md"),
        )
        history_text = None
        for history_path in history_candidates:
            try:
                history_text = history_path.read_text(encoding="utf-8")
                break
            except Exception:
                continue
        if history_text is None:
            history_text = (
                "The history log could not be opened.\n\n"
                "The application's normal dimming functions are unaffected."
            )

        super().__init__(
            "X11 Monitor Dimmer — Full History Log",
            parent,
            history_text,
            width=760,
            height=560,
        )
