import unittest

from PyQt5.QtWidgets import QApplication, QGroupBox, QLabel, QMenu

from pyssp.i18n import LANG_EN, LANG_ZH_CN, localize_widget_tree, translate_text


class TestI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_translate_known_text(self):
        self.assertEqual(translate_text("Options", LANG_ZH_CN), "选项")

    def test_localize_label_text(self):
        label = QLabel("Options")
        localize_widget_tree(label, LANG_ZH_CN)
        self.assertEqual(label.text(), "选项")
        localize_widget_tree(label, LANG_EN)
        self.assertEqual(label.text(), "Options")

    def test_localize_menu_title(self):
        menu = QMenu("Options")
        localize_widget_tree(menu, LANG_ZH_CN)
        self.assertEqual(menu.title(), "选项")
        localize_widget_tree(menu, LANG_EN)
        self.assertEqual(menu.title(), "Options")

    def test_localize_groupbox_title(self):
        group = QGroupBox("General")
        localize_widget_tree(group, LANG_ZH_CN)
        self.assertEqual(group.title(), "常规")
        localize_widget_tree(group, LANG_EN)
        self.assertEqual(group.title(), "General")


if __name__ == "__main__":
    unittest.main()
