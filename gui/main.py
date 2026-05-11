#!/usr/bin/env python3
"""Codex Account Switcher — cross-platform GUI (Flet)."""

import sys
import locale
import asyncio
import traceback
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

# ── i18n ───────────────────────────────────────────────────────────────
def _detect_lang():
    if sys.platform == "win32":
        try:
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if lid in (0x0804, 0x0404, 0x0c04, 0x1004):
                return "zh"
        except Exception:
            pass
    try:
        loc = locale.getdefaultlocale()[0] or ""
        if loc.startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"

LANG = _detect_lang()

STR = {
    "title":              {"en": "Codex Account Switcher",            "zh": "Codex 账号切换器"},
    "subtitle":           {"en": "Manage and switch between accounts","zh": "管理和切换 Codex 账号"},
    "current_account":    {"en": "Current Account",                   "zh": "当前账号"},
    "saved_profiles":     {"en": "Saved Profiles",                    "zh": "已保存的账号"},
    "save_btn":           {"en": "Save",                              "zh": "保存"},
    "add_account":        {"en": "Add New Account",                   "zh": "添加新账号"},
    "save_field_hint":    {"en": "Enter profile name (default: email)","zh": "输入配置名称（默认为邮箱）"},
    "save_dlg_title":     {"en": "Save Current Account",              "zh": "保存当前账号"},
    "save_dlg_desc":      {"en": "Enter a name for this account profile.","zh": "为这个账号配置起一个名称。"},
    "save_dlg_cancel":    {"en": "Cancel",                            "zh": "取消"},
    "save_dlg_confirm":   {"en": "Save Profile",                      "zh": "保存"},
    "delete_dlg_title":   {"en": "Delete Profile",                    "zh": "删除配置"},
    "delete_dlg_desc":    {"en": "Are you sure? This cannot be undone.","zh": "确定删除吗？此操作无法撤销。"},
    "delete_dlg_cancel":  {"en": "Cancel",                            "zh": "取消"},
    "delete_dlg_confirm": {"en": "Delete",                            "zh": "删除"},
    "switch_dlg_title":   {"en": "Switch Account",                    "zh": "切换账号"},
    "switch_dlg_desc":    {"en": "Codex is currently running. Switching accounts will stop all Codex processes before proceeding.",
                           "zh": "Codex 当前正在运行，切换账号前将结束所有 Codex 进程。"},
    "switch_dlg_confirm_ask": {"en": "Are you sure you want to continue?","zh": "确定要继续吗？"},
    "switch_dlg_cancel":  {"en": "Cancel",                            "zh": "取消"},
    "switch_dlg_confirm": {"en": "Switch Anyway",                     "zh": "确认切换"},
    "logout_dlg_title":   {"en": "Add New Account",                   "zh": "添加新账号"},
    "logout_dlg_desc":    {"en": "This will clear your login credentials so you can sign in with a new account.",
                           "zh": "此操作会清空登录信息，以便你切换到新账号。"},
    "logout_dlg_codex":   {"en": "Codex is currently running. Its processes will be stopped.",
                           "zh": "Codex 当前正在运行，将结束其进程。"},
    "logout_dlg_cancel":  {"en": "Cancel",                            "zh": "取消"},
    "logout_dlg_confirm": {"en": "Confirm",                           "zh": "确认"},
    "not_logged_in":      {"en": "Not logged in",                     "zh": "未登录"},
    "not_saved":          {"en": "Not saved yet",                     "zh": "未保存"},
    "saved_as":           {"en": "Saved as: {name}",                  "zh": "已保存为：{name}"},
    "login_hint":         {"en": "Run 'codex login' to sign in",     "zh": "运行 codex login 登录"},
    "switch_tooltip":     {"en": "Switch to this account",            "zh": "切换到此账号"},
    "delete_tooltip":     {"en": "Delete profile",                    "zh": "删除此配置"},
    "cli_label":          {"en": "CLI:",                              "zh": "命令行："},
    "snack_no_account":   {"en": "No account to save. Run 'codex login' first.", "zh": "没有可保存的账号，请先运行 codex login 登录。"},
    "snack_saved":        {"en": "Profile '{name}' saved.",           "zh": "配置「{name}」已保存。"},
    "snack_switched":     {"en": "Switched to {email}",               "zh": "已切换到 {email}"},
    "snack_deleted":      {"en": "Profile '{name}' deleted.",         "zh": "配置「{name}」已删除。"},
    "snack_logged_out":   {"en": "Logged out. Run 'codex login' to sign in with a new account.",
                           "zh": "已退出登录，运行 codex login 登录新账号。"},
    "snack_duplicate":    {"en": "This account is already saved as '{name}'.", "zh": "此账号已在配置「{name}」中保存。"},
    "snack_error":        {"en": "Error: {msg}",                      "zh": "错误：{msg}"},
}

def T(key, **kwargs):
    entry = STR.get(key, {})
    s = entry.get(LANG) or entry.get("en", key)
    if kwargs:
        s = s.format(**kwargs)
    return s


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
        page.title = T("title")
        page.window.width = 440
        page.window.height = 580
        page.window.resizable = True
        page.window.min_width = 400
        page.window.min_height = 500
        page.padding = 0
        page.bgcolor = C["bg"]
        page.theme_mode = ft.ThemeMode.LIGHT

        self._switch_loading_name = None
        self.current_avatar = _ak("?", 42, 16)
        self.current_email_txt = ft.Text("", size=14, weight="w600", color=C["text_inv"])
        self.current_profile_txt = ft.Text("", size=11, color="#999999")
        self.current_card = ft.Container(visible=False)
        self.profiles_col = ft.Column(spacing=6)
        self.add_btn = ft.Container(visible=False)

        self._build_dialogs()
        self._build_layout()
        self.refresh()

    # -- dialogs -----------------------------------------------------------
    def _build_dialogs(self):
        # save dialog
        self.save_field = ft.TextField(
            hint_text=T("save_field_hint"),
            border_radius=12,
            bgcolor=C["card_light"],
            border_color=ft.Colors.TRANSPARENT,
            content_padding=ft.padding.Padding.symmetric(horizontal=14, vertical=10),
            text_size=13,
            autofocus=True,
            on_submit=self._on_save_confirm,
        )
        self.save_dlg = ft.AlertDialog(
            title=ft.Text(T("save_dlg_title"), size=18, weight="w700"),
            content=ft.Column([
                ft.Text(T("save_dlg_desc"), size=12, color=C["text_muted"]),
                self.save_field,
            ], spacing=14, height=100),
            actions=[
                ft.TextButton(T("save_dlg_cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(T("save_dlg_confirm"), on_click=self._on_save_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # delete confirm
        self._del_target = None
        self.del_dlg = ft.AlertDialog(
            title=ft.Text(T("delete_dlg_title"), size=18, weight="w700"),
            content=ft.Text(T("delete_dlg_desc"), size=13, color=C["text_muted"]),
            actions=[
                ft.TextButton(T("delete_dlg_cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(T("delete_dlg_confirm"), on_click=self._on_delete_confirm,
                                style=ft.ButtonStyle(bgcolor=C["danger"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # switch confirm (when Codex is running)
        self._switch_target = None
        self.switch_dlg = ft.AlertDialog(
            title=ft.Text(T("switch_dlg_title"), size=18, weight="w700"),
            content=ft.Column([
                ft.Text(T("switch_dlg_desc"), size=13, color=C["text_muted"]),
                ft.Text(T("switch_dlg_confirm_ask"), size=13, weight="w600", color=C["text"]),
            ], spacing=10),
            actions=[
                ft.TextButton(T("switch_dlg_cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(T("switch_dlg_confirm"), on_click=self._on_switch_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # logout confirm (Add New Account when Codex is running)
        self._logout_pending = False
        self.logout_codex_dlg = ft.AlertDialog(
            title=ft.Text(T("logout_dlg_title"), size=18, weight="w700"),
            content=ft.Column([
                ft.Text(T("logout_dlg_desc"), size=13, color=C["text_muted"]),
                ft.Text(T("logout_dlg_codex"), size=13, color=C["text_muted"]),
                ft.Text(T("switch_dlg_confirm_ask"), size=13, weight="w600", color=C["text"]),
            ], spacing=10),
            actions=[
                ft.TextButton(T("logout_dlg_cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(T("logout_dlg_confirm"), on_click=self._on_logout_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # simple logout confirm (no Codex running)
        self.logout_dlg = ft.AlertDialog(
            title=ft.Text(T("logout_dlg_title"), size=18, weight="w700"),
            content=ft.Text(T("logout_dlg_desc"), size=13, color=C["text_muted"]),
            actions=[
                ft.TextButton(T("logout_dlg_cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(T("logout_dlg_confirm"), on_click=self._on_logout_confirm,
                                style=ft.ButtonStyle(bgcolor=C["accent"], color=C["text_inv"])),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

    # -- build static UI ----------------------------------------------------
    def _build_layout(self):
        header = ft.Row([
            ft.Container(
                content=ft.Text("C", size=18, weight="w700", color=C["text_inv"], text_align="center"),
                width=38, height=38, border_radius=12, bgcolor=C["card_dark"],
                alignment=ft.alignment.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(T("title"), size=18, weight="w700", color=C["text"]),
                ft.Text(T("subtitle"), size=11, color=C["text_muted"]),
            ], spacing=2),
        ], spacing=12)

        self.current_card = ft.Container(
            content=ft.Row([
                self.current_avatar,
                ft.Column([
                    self.current_email_txt,
                    self.current_profile_txt,
                ], spacing=2, expand=True),
                ft.FilledButton(
                    T("save_btn"), icon=ft.Icons.SAVE_OUTLINED,
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

        self.add_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD_CIRCLE, size=16, color=C["text_sec"]),
                ft.Text(T("add_account"), size=12, weight="w500", color=C["text_sec"]),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
            height=40, border_radius=12, bgcolor=C["card_light"],
            alignment=ft.alignment.Alignment.CENTER,
            on_click=self._on_add_account, visible=False,
        )

        footer = ft.Row([
            ft.Text(T("cli_label"), size=10, color=C["text_muted"]),
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
                    ft.Text(T("current_account"), size=11, weight="w600", color=C["text_muted"]),
                    self.current_card,
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    ft.Text(T("saved_profiles"), size=11, weight="w600", color=C["text_muted"]),
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
        try:
            self._refresh_impl()
        except Exception as ex:
            tb = traceback.format_exc()
            print(tb, file=sys.stderr)
            self._snack(T("snack_error", msg=f"{ex}\n\n{tb[-500:]}"), C["danger"])

    def _refresh_impl(self):
        email, aid, prof = get_current()
        self._current_email = email or ""

        if email and email != "unknown":
            self.current_email_txt.value = email
            self.current_profile_txt.value = T("saved_as", name=prof) if prof else T("not_saved")
            self.current_avatar.content.value = email[0].upper()
        else:
            self.current_email_txt.value = T("not_logged_in")
            self.current_profile_txt.value = T("login_hint")
            self.current_avatar.content.value = "?"
        self.current_avatar.content.update()
        self.current_email_txt.update()
        self.current_profile_txt.update()
        self.current_card.visible = True
        self.current_card.update()

        self._refresh_profiles()

        self.add_btn.visible = True
        self.add_btn.update()

    def _refresh_profiles(self):
        self.profiles_col.controls.clear()
        for name, em in list_profiles():
            is_cur = (em == self._current_email)
            card = self._build_profile_card(name, em, is_cur)
            self.profiles_col.controls.append(card)
        self.profiles_col.update()

    def _build_profile_card(self, name, email, is_current):
        border = ft.border.Border.all(1.5, C["accent"]) if is_current else None
        is_loading = (name == self._switch_loading_name)
        switch_btn = (
            ft.ProgressRing(width=16, height=16, stroke_width=2, color=C["accent"])
            if is_loading else
            ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD_IOS,
                icon_size=14, icon_color=C["accent"],
                tooltip=T("switch_tooltip"),
                on_click=lambda e, n=name: self._on_switch(n),
            )
        )
        return ft.Container(
            content=ft.Row([
                _ak(name, 34, 13),
                ft.Column([
                    ft.Text(name, size=13, weight="w600", color=C["text"]),
                    ft.Text(email, size=10, color=C["text_muted"]),
                ], spacing=2, expand=True),
                switch_btn,
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=12, icon_color=C["text_muted"],
                    tooltip=T("delete_tooltip"),
                    on_click=lambda e, n=name: self._on_delete_ask(n),
                ),
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=12, bgcolor=C["card_light"], border=border,
        )

    # -- event handlers -----------------------------------------------------
    def _on_save(self, e):
        if not self._current_email or self._current_email == "unknown":
            self._snack(T("snack_no_account"), C["danger"])
            return
        # Check for duplicate
        for name, em in list_profiles():
            if em == self._current_email:
                self._snack(T("snack_duplicate", name=name), C["danger"])
                return
        self.save_field.value = self._current_email
        self.page.show_dialog(self.save_dlg)

    def _on_save_confirm(self, e):
        name = self.save_field.value.strip() or self._current_email
        try:
            save_profile(name)
            self.page.pop_dialog()
            self._snack(T("snack_saved", name=name))
            self.refresh()
        except Exception as ex:
            self._snack(T("snack_error", msg=str(ex)), C["danger"])

    def _on_switch(self, name):
        if is_codex_running():
            self._switch_target = name
            self.page.show_dialog(self.switch_dlg)
        else:
            self.page.run_task(self._do_switch_async, name)

    async def _do_switch_async(self, name):
        self._switch_loading_name = name
        self._refresh_profiles()
        try:
            new_email = await asyncio.to_thread(switch_profile, name)
            self._snack(T("snack_switched", email=new_email or "unknown"))
        except Exception as ex:
            tb = traceback.format_exc()
            print(tb, file=sys.stderr)
            self._snack(T("snack_error", msg=str(ex)), C["danger"])
        finally:
            self._switch_loading_name = None
            self.refresh()

    def _on_switch_confirm(self, e):
        self.page.pop_dialog()
        self.page.run_task(self._do_switch_async, self._switch_target)
        self._switch_target = None

    def _on_delete_ask(self, name):
        self._del_target = name
        self.page.show_dialog(self.del_dlg)

    def _on_delete_confirm(self, e):
        name = self._del_target
        if name:
            try:
                delete_profile(name)
                self.page.pop_dialog()
                self._snack(T("snack_deleted", name=name))
                self.refresh()
            except Exception as ex:
                self._snack(T("snack_error", msg=str(ex)), C["danger"])

    def _on_add_account(self, e):
        if is_codex_running():
            self.page.show_dialog(self.logout_codex_dlg)
        else:
            self.page.show_dialog(self.logout_dlg)

    def _on_logout_confirm(self, e):
        self.page.pop_dialog()
        try:
            logout()
            self._snack(T("snack_logged_out"))
            self.refresh()
        except Exception as ex:
            self._snack(T("snack_error", msg=str(ex)), C["danger"])

    def _snack(self, msg, bgcolor=None):
        self.page.show_dialog(ft.SnackBar(ft.Text(msg), bgcolor=bgcolor or C["accent"]))


if __name__ == "__main__":
    def _create_app(page: ft.Page):
        try:
            return App(page)
        except Exception as _ex:
            traceback.print_exc(file=sys.stderr)
    ft.run(_create_app)
