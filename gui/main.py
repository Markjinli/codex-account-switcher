#!/usr/bin/env python3
"""Codex Account Switcher — cross-platform GUI (Flet)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flet as ft
from gui.core import (
    get_current, is_codex_running, list_profiles,
    save_profile, switch_profile, delete_profile, logout,
)

REPO_URL = "https://github.com/Markjinli/codex-account-switcher"

C = {
    "bg":          "#FFFFFF",
    "card_light":  "#F7F8FA",
    "card_dark":   "#0A0A0A",
    "text":        "#1A1A1A",
    "text_sec":    "#666666",
    "text_muted":  "#888888",
    "text_inv":    "#FFFFFF",
    "accent":      "#4A9FD8",
    "danger":      "#E05555",
}


def _ak(n, s=34, fs=13):
    """Avatar circle with first letter of name."""
    return ft.Container(
        content=ft.Text(n[0].upper(), size=fs, weight="w700",
                        color=C["text_inv"], text_align="center"),
        width=s, height=s, border_radius=9999,
        bgcolor=C["card_dark"], alignment=ft.alignment.Alignment.CENTER,
    )


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "Codex Account Switcher"
        page.window.width = 440
        page.window.height = 580
        page.window.resizable = True
        page.window.min_width = 400
        page.window.min_height = 500
        page.padding = 0
        page.bgcolor = C["bg"]
        page.theme_mode = ft.ThemeMode.LIGHT

        # ---- dynamic widgets (rebuilt on refresh) --------------------------
        self.current_avatar = _ak("?", 42, 16)
        self.current_email_txt = ft.Text("", size=14, weight="w600", color=C["text_inv"])
        self.current_profile_txt = ft.Text("", size=11, color="#999999")
        self.current_card = ft.Container(visible=False)
        self.profiles_col = ft.Column(spacing=6)
        self.add_btn = ft.Container(visible=False)

        # ---- dialogs -------------------------------------------------------
        self._build_dialogs()

        # ---- layout --------------------------------------------------------
        self._build_layout()
        self.refresh()

    # -- dialogs -----------------------------------------------------------
    def _build_dialogs(self):
        # save dialog
        self.save_field = ft.TextField(
            hint_text="Enter profile name (default: email)",
            border_radius=12,
            bgcolor=C["card_light"],
            border_color=ft.Colors.TRANSPARENT,
            content_padding=ft.padding.Padding.symmetric(horizontal=14, vertical=10),
            text_size=13,
            autofocus=True,
            on_submit=self._on_save_confirm,
        )
        self.save_dlg = ft.AlertDialog(
            title=ft.Text("Save Current Account", size=18, weight="w700"),
            content=ft.Column([
                ft.Text("Enter a name for this account profile.", size=12, color=C["text_muted"]),
                self.save_field,
            ], spacing=14, height=100),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Save Profile", on_click=self._on_save_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # delete confirm
        self._del_target = None
        self.del_dlg = ft.AlertDialog(
            title=ft.Text("Delete Profile", size=18, weight="w700"),
            content=ft.Text("Are you sure? This cannot be undone.", size=13, color=C["text_muted"]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Delete", on_click=self._on_delete_confirm,
                                style=ft.ButtonStyle(bgcolor=C["danger"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # switch confirm (when Codex is running)
        self._switch_target = None
        self.switch_dlg = ft.AlertDialog(
            title=ft.Text("Switch Account", size=18, weight="w700"),
            content=ft.Column([
                ft.Text(
                    "Codex is currently running. Switching accounts will stop all "
                    "Codex processes before proceeding.",
                    size=13, color=C["text_muted"],
                ),
                ft.Text(
                    "Are you sure you want to continue?",
                    size=13, weight="w600", color=C["text"],
                ),
            ], spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Switch Anyway", on_click=self._on_switch_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

    # -- build static UI ----------------------------------------------------
    def _build_layout(self):
        # header
        header = ft.Row([
            ft.Container(
                content=ft.Text("C", size=18, weight="w700", color=C["text_inv"], text_align="center"),
                width=38, height=38, border_radius=12, bgcolor=C["card_dark"],
                alignment=ft.alignment.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text("Codex Account Switcher", size=18, weight="w700", color=C["text"]),
                ft.Text("Manage and switch between accounts", size=11, color=C["text_muted"]),
            ], spacing=2),
        ], spacing=12)

        # current account card
        self.current_card = ft.Container(
            content=ft.Row([
                self.current_avatar,
                ft.Column([
                    self.current_email_txt,
                    self.current_profile_txt,
                ], spacing=2, expand=True),
                ft.FilledButton(
                    "Save", icon=ft.Icons.SAVE_OUTLINED,
                    on_click=self._on_save,
                    style=ft.ButtonStyle(
                        bgcolor=C["accent"], color=C["text_inv"],
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.Padding.symmetric(horizontal=14, vertical=8),
                    ),
                    height=34,
                ),
            ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
            padding=16, border_radius=16, bgcolor=C["card_dark"], visible=False,
        )

        # add account button
        self.add_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD_CIRCLE, size=16, color=C["text_sec"]),
                ft.Text("Add New Account", size=12, weight="w500", color=C["text_sec"]),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
            height=40, border_radius=12, bgcolor=C["card_light"],
            alignment=ft.alignment.Alignment.CENTER,
            on_click=self._on_add_account, visible=False,
        )

        # footer
        footer = ft.Row([
            ft.Text("CLI:", size=10, color=C["text_muted"]),
            ft.Text("codex-switch", size=10, color=C["text_muted"]),
            ft.Text("·", size=10, color=C["text_muted"]),
            ft.GestureDetector(
                content=ft.Text("GitHub", size=10, color=C["accent"]),
                on_tap=lambda e: self.page.launch_url(REPO_URL),
            ),
        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER)

        self.page.add(
            ft.Container(
                content=ft.Column([
                    header,
                    ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                    ft.Text("Current Account", size=11, weight="w600", color=C["text_muted"]),
                    self.current_card,
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    ft.Text("Saved Profiles", size=11, weight="w600", color=C["text_muted"]),
                    self.profiles_col,
                    self.add_btn,
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    footer,
                ], spacing=6, scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.Padding.symmetric(horizontal=28, vertical=24),
                expand=True,
            ),
        )

    # -- refresh ------------------------------------------------------------
    def refresh(self):
        email, aid, prof = get_current()
        self._current_email = email or ""

        if email and email != "unknown":
            self.current_email_txt.value = email
            self.current_profile_txt.value = f"Saved as: {prof}" if prof else "Not saved yet"
            self.current_avatar.content.value = email[0].upper()
        else:
            self.current_email_txt.value = "Not logged in"
            self.current_profile_txt.value = "Run 'codex login' to sign in"
            self.current_avatar.content.value = "?"
        self.current_avatar.content.update()
        self.current_email_txt.update()
        self.current_profile_txt.update()
        self.current_card.visible = True
        self.current_card.update()

        # profiles
        self.profiles_col.controls.clear()
        for name, em in list_profiles():
            is_cur = (em == self._current_email)
            card = self._build_profile_card(name, em, is_cur)
            self.profiles_col.controls.append(card)
        self.profiles_col.update()

        self.add_btn.visible = True
        self.add_btn.update()

    def _build_profile_card(self, name, email, is_current):
        border = ft.border.Border.all(1.5, C["accent"]) if is_current else None
        return ft.Container(
            content=ft.Row([
                _ak(name, 34, 13),
                ft.Column([
                    ft.Text(name, size=13, weight="w600", color=C["text"]),
                    ft.Text(email, size=10, color=C["text_muted"]),
                ], spacing=2, expand=True),
                ft.IconButton(
                    icon=ft.Icons.ARROW_FORWARD_IOS,
                    icon_size=14, icon_color=C["accent"],
                    tooltip="Switch to this account",
                    on_click=lambda e, n=name: self._on_switch(n),
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=12, icon_color=C["text_muted"],
                    tooltip="Delete profile",
                    on_click=lambda e, n=name: self._on_delete_ask(n),
                ),
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=12, bgcolor=C["card_light"], border=border,
        )

    # -- event handlers -----------------------------------------------------
    def _on_save(self, e):
        if not self._current_email or self._current_email == "unknown":
            self._snack("No account to save. Run 'codex login' first.", C["danger"])
            return
        self.save_field.value = self._current_email
        self.page.show_dialog(self.save_dlg)

    def _on_save_confirm(self, e):
        name = self.save_field.value.strip() or self._current_email
        try:
            save_profile(name)
            self.page.pop_dialog(self.save_dlg)
            self._snack(f"Profile '{name}' saved.")
            self.refresh()
        except Exception as ex:
            self._snack(f"Error: {ex}", C["danger"])

    def _on_switch(self, name):
        if is_codex_running():
            self._switch_target = name
            self.page.show_dialog(self.switch_dlg)
        else:
            self._do_switch(name)

    def _do_switch(self, name):
        try:
            new_email = switch_profile(name)
            self._snack(f"Switched to {new_email}")
            self.refresh()
        except Exception as ex:
            self._snack(f"Error: {ex}", C["danger"])

    def _on_switch_confirm(self, e):
        self.page.pop_dialog()
        self._do_switch(self._switch_target)
        self._switch_target = None

    def _on_delete_ask(self, name):
        self._del_target = name
        self.page.show_dialog(self.del_dlg)

    def _on_delete_confirm(self, e):
        name = self._del_target
        if name:
            try:
                delete_profile(name)
                self.page.pop_dialog(self.del_dlg)
                self._snack(f"Profile '{name}' deleted.")
                self.refresh()
            except Exception as ex:
                self._snack(f"Error: {ex}", C["danger"])

    def _on_add_account(self, e):
        try:
            logout()
            self._snack("Logged out. Run 'codex login' to sign in with a new account.")
            self.refresh()
        except Exception as ex:
            self._snack(f"Error: {ex}", C["danger"])

    def _snack(self, msg, bgcolor=None):
        self.page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=bgcolor or C["accent"]))


if __name__ == "__main__":
    ft.run(lambda page: App(page))
