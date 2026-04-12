import unittest

from PyQt5.QtWidgets import QApplication, QGroupBox, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from pyssp.i18n import LANG_EN, LANG_ZH_CN, localize_widget_tree, translate_text


class TestI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_translate_known_text(self):
        self.assertEqual(translate_text("Options", LANG_ZH_CN), "选项")
        self.assertEqual(translate_text("Main Transport Display", LANG_ZH_CN), "主时间线显示")
        self.assertEqual(translate_text("Stage Display", LANG_ZH_CN), "舞台显示")
        self.assertEqual(translate_text("Stage Display Setting", LANG_ZH_CN), "舞台显示设置")
        self.assertEqual(translate_text("Show Stage Display", LANG_ZH_CN), "显示舞台显示")
        self.assertEqual(translate_text("Send Alert", LANG_ZH_CN), "发送通知")
        self.assertEqual(translate_text("Open Lyric Display", LANG_ZH_CN), "打开歌词显示")
        self.assertEqual(translate_text("Web Lyric Display", LANG_ZH_CN), "网页歌词显示")
        self.assertEqual(translate_text("Overhead", LANG_ZH_CN), "顶投")
        self.assertEqual(translate_text("Banner", LANG_ZH_CN), "横幅")
        self.assertEqual(translate_text("vMix Overlay", LANG_ZH_CN), "vMix 叠加")
        self.assertEqual(translate_text("Gadgets", LANG_ZH_CN), "组件")
        self.assertEqual(translate_text("Lock Screen", LANG_ZH_CN), "锁屏")
        self.assertEqual(translate_text("Lock / Unlock", LANG_ZH_CN), "锁定 / 解锁")
        self.assertEqual(translate_text("Require password for unlock", LANG_ZH_CN), "解锁时需要密码")
        self.assertEqual(translate_text("Automation lock is active.", LANG_ZH_CN), "自动化锁定已启用。")
        self.assertEqual(translate_text("Allow While Auto Locked", LANG_ZH_CN), "自动化锁定时允许")
        self.assertEqual(
            translate_text("Type sure to unlock to continue.", LANG_ZH_CN),
            "请输入 sure to unlock 以继续。",
        )

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

    def test_force_language_property_overrides_requested_language(self):
        root = QWidget()
        root.setProperty("_i18n_force_language", LANG_EN)
        layout = QVBoxLayout(root)
        button = QPushButton("Close")
        layout.addWidget(button)

        localize_widget_tree(root, LANG_ZH_CN)

        self.assertEqual(button.text(), "Close")


if __name__ == "__main__":
    unittest.main()
