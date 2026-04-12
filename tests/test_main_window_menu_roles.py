import sys
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QAction, QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.ui.menu_roles import configure_about_menu_actions, configure_preferences_menu_actions


class TestMainWindowMenuRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_configure_preferences_menu_actions_for_macos(self):
        options_action = QAction("Options")
        preferences_action = QAction("Preferences")

        configure_preferences_menu_actions(
            options_action,
            preferences_action,
            platform_name="darwin",
        )

        self.assertEqual(options_action.menuRole(), QAction.NoRole)
        self.assertEqual(preferences_action.menuRole(), QAction.PreferencesRole)

    def test_configure_preferences_menu_actions_for_non_macos(self):
        options_action = QAction("Options")
        preferences_action = QAction("Preferences")

        configure_preferences_menu_actions(
            options_action,
            preferences_action,
            platform_name="win32",
        )

        self.assertEqual(options_action.menuRole(), QAction.NoRole)
        self.assertEqual(preferences_action.menuRole(), QAction.NoRole)

    def test_configure_about_menu_actions_for_macos(self):
        about_action = QAction("About")
        application_about_action = QAction("About")

        configure_about_menu_actions(
            about_action,
            application_about_action,
            platform_name="darwin",
        )

        self.assertEqual(about_action.menuRole(), QAction.NoRole)
        self.assertEqual(application_about_action.menuRole(), QAction.AboutRole)

    def test_configure_about_menu_actions_for_non_macos(self):
        about_action = QAction("About")
        application_about_action = QAction("About")

        configure_about_menu_actions(
            about_action,
            application_about_action,
            platform_name="win32",
        )

        self.assertEqual(about_action.menuRole(), QAction.NoRole)
        self.assertEqual(application_about_action.menuRole(), QAction.NoRole)


if __name__ == "__main__":
    unittest.main()
