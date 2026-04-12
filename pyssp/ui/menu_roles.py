from __future__ import annotations

import sys
from typing import Optional

from PyQt5.QtWidgets import QAction


def configure_preferences_menu_actions(
    options_action: QAction,
    preferences_action: Optional[QAction] = None,
    *,
    platform_name: Optional[str] = None,
) -> None:
    current_platform = platform_name or sys.platform
    options_action.setMenuRole(QAction.NoRole)
    if preferences_action is None:
        return
    if current_platform == "darwin":
        preferences_action.setMenuRole(QAction.PreferencesRole)
    else:
        preferences_action.setMenuRole(QAction.NoRole)


def configure_about_menu_actions(
    about_action: QAction,
    application_about_action: Optional[QAction] = None,
    *,
    platform_name: Optional[str] = None,
) -> None:
    current_platform = platform_name or sys.platform
    about_action.setMenuRole(QAction.NoRole)
    if application_about_action is None:
        return
    if current_platform == "darwin":
        application_about_action.setMenuRole(QAction.AboutRole)
    else:
        application_about_action.setMenuRole(QAction.NoRole)
