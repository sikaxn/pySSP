from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QWidget,
)

LANG_EN = "en"
LANG_ZH_CN = "zh_cn"
SOURCE_TEXT_ROLE = Qt.UserRole + 5000

_TRANSLATIONS = {
    LANG_ZH_CN: {
        "Python SSP": "Python SSP 狐狸版",
        "Options": "选项",
        "General": "常规",
        "Language": "语言",
        "Hotkey": "快捷键",
        "Colour": "颜色",
        "Fade": "淡入淡出",
        "Playback": "播放",
        "Audio Device / Timecode": "音频设备 / 时间码",
        "Talk": "讲话闪避",
        "Web Remote": "网页遥控",
        "Restore Defaults (This Page)": "恢复默认（当前页面）",
        "Button Title Max Chars:": "按钮标题最大字符数:",
        "Show set load/save popup messages": "显示集合加载/保存弹窗消息",
        "Notifications:": "通知:",
        "Enable playback log file (SportsSoundsProLog.txt)": "启用播放日志文件 (SportsSoundsProLog.txt)",
        "Log File:": "日志文件:",
        "Reset ALL on Start-up": "启动时重置全部",
        "Startup:": "启动:",
        ".set Save Encoding": ".set 保存编码",
        "GBK note: if song title, notes, file path, etc include Chinese characters, GBK has better compatibility with original SSP.": "GBK 说明：如果歌曲标题、备注、文件路径等包含中文字符，GBK 与原版 SSP 的兼容性更好。",
        "Clicking on a Playing Sound will:": "点击正在播放的声音将:",
        "Play It Again": "重新播放",
        "Stop It": "停止播放",
        "Search Double-Click will:": "搜索结果双击将:",
        "Find (Highlight)": "定位（高亮）",
        "Play and Highlight": "播放并高亮",
        "UI Language": "界面语言",
        "App language (requires reopen dialogs/windows to fully refresh).": "应用语言（需要重新打开对话框/窗口以完全刷新）。",
        "English": "English",
        "Chinese (Simplified)": "简体中文",
        "Find Sound File": "查找声音文件",
        "Keywords": "关键词",
        "Type words from title or file path": "输入标题或文件路径中的关键词",
        "Search": "搜索",
        "Enter keywords and click Search.": "输入关键词并点击搜索。",
        "Enter at least one keyword.": "请至少输入一个关键词。",
        "Go To Selected": "跳转到所选",
        "Play": "播放",
        "Close": "关闭",
        "Set Cue Points": "设置 Cue 点",
        "Preview": "预览",
        "Stop": "停止",
        "Total 00:00:00": "总计 00:00:00",
        "Elapsed 00:00:00": "已播放 00:00:00",
        "Remaining 00:00:00": "剩余 00:00:00",
        "In 00:00:00": "入点 00:00:00",
        "Out 00:00:00": "出点 00:00:00",
        "Set Start Cue": "设置起始 Cue",
        "Set End Cue": "设置结束 Cue",
        "Reset": "重置",
        "Start": "开始",
        "End": "结束",
        "Clear Cue": "清除 Cue",
        "Cancel": "取消",
        "Save": "保存",
        "Invalid start cue timecode. Use mm:ss or mm:ss:ff.": "起始 Cue 时间码无效。请使用 mm:ss 或 mm:ss:ff。",
        "Invalid end cue timecode. Use mm:ss or mm:ss:ff.": "结束 Cue 时间码无效。请使用 mm:ss 或 mm:ss:ff。",
        "Could not load audio preview: ": "无法加载音频预览: ",
        "Edit Sound Button": "编辑声音按钮",
        "Browse": "浏览",
        "File": "文件",
        "Caption": "标题",
        "Notes": "备注",
        "Clear": "清除",
        "Sound Button Hot Key": "声音按钮快捷键",
        "Use custom playback volume": "使用自定义播放音量",
        "Playback Volume": "播放音量",
        "Select Sound File": "选择声音文件",
        "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)": "音频文件 (*.wav *.mp3 *.ogg *.flac *.m4a);;所有文件 (*.*)",
        "Optional: A-O, Q-Z, 0-9, F1-F12 (except F10)": "可选：A-O、Q-Z、0-9、F1-F12（不含 F10）",
        "DSP": "DSP",
        "10-Band EQ": "10 段均衡器",
        "EQ On": "均衡器开",
        "EQ Off": "均衡器关",
        "Presets:": "预设:",
        "Flat": "平坦",
        "Rock": "摇滚",
        "Country": "乡村",
        "Jazz": "爵士",
        "Classical": "古典",
        "Reverb": "混响",
        "Tempo": "速度",
        "Pitch": "音高",
        "Timecode": "时间码",
        "Timecode Mode": "时间码模式",
        "All Zero": "全零",
        "Follow Media/Audio Player": "跟随媒体/音频播放器",
        "System Time": "系统时间",
        "Pause Sync (Freeze While Playback Continues)": "暂停同步（播放继续时冻结）",
        "Current Output": "当前输出",
        "New Set": "新建集合",
        "Open Set": "打开集合",
        "Save Set": "保存集合",
        "Save Set At": "另存集合",
        "Timecode Settings": "时间码设置",
        "Timecode Panel": "时间码面板",
        "Duplicate Check": "重复检查",
        "Verify Sound Buttons": "验证声音按钮",
        "Disable Play List on All Pages": "禁用所有页面播放列表",
        "Display Page Library Folder Path": "显示页面库文件夹路径",
        "Display .set File and Path": "显示 .set 文件及路径",
        "Export Page and Sound Buttons to Excel": "导出页面和声音按钮到 Excel",
        "List Sound Buttons": "列出声音按钮",
        "List Sound Button Hot Key": "列出声音按钮快捷键",
        "View Log": "查看日志",
        "About": "关于",
        "Help": "帮助",
        "Register": "注册",
        "pySSP is free software. No registration is required.": "这是免费软件，如果你花了钱，请邮件piracy@studenttechsupport.com\n警告各位卖家：你敢拿去卖我就敢把你告到死。咱们走着瞧。",
        "Open Folder": "打开文件夹",
        "Export Complete": "导出完成",
        "Export Failed": "导出失败",
        "No rows to export.": "没有可导出的行。",
        "Audio Device": "音频设备",
        "Go To Playing": "跳转到正在播放",
        "No sound is currently playing.": "当前没有正在播放的声音。",
        "Locked": "已锁定",
        "This sound button is locked.": "此声音按钮已锁定。",
        "Create Page": "创建页面",
        "Create the page first before adding sound buttons.": "添加声音按钮前请先创建页面。",
        "Missing File": "文件缺失",
        "File Check": "文件检查",
        "Sound file exists.": "声音文件存在。",
        "Adjust Volume Level": "调整音量级别",
        "Playback In Progress": "播放进行中",
        "Playback is in progress. Quit anyway?": "播放正在进行。仍要退出吗？",
        "Unsaved Changes": "未保存的更改",
        "This set has unsaved changes. Save before closing?": "此集合有未保存更改。关闭前是否保存？",
        "Set Saved": "集合已保存",
        "Save Set Failed": "保存集合失败",
        "Open Set Failed": "打开集合失败",
        "Cue": "Cue",
        "Multi-Play": "多重播放",
        "Go To Playing": "跳转到正在播放",
        "Loop": "循环",
        "Next": "下一首",
        "Button Drag": "按钮拖拽",
        "Pause": "暂停",
        "Rapid Fire": "连发",
        "Shuffle": "随机",
        "Reset Page": "重置页面",
        "STOP": "停止",
        "Play List": "播放列表",
        "Talk*": "讲话闪避*",
        "Add Page": "添加页面",
        "Rename Page": "重命名页面",
        "Delete Page": "删除页面",
        "Copy Page": "复制页面",
        "Paste Page": "粘贴页面",
        "Import Page...": "导入页面...",
        "Export Page...": "导出页面...",
        "Change Page Color...": "更改页面颜色...",
        "Clear Page Color": "清除页面颜色",
        "Page Button Color": "页面按钮颜色",
        "Enter page name:": "输入页面名称:",
        "Page name:": "页面名称:",
        "Delete page and all sound buttons?": "删除页面及所有声音按钮？",
        "Cue It": "加入 Cue",
        "Set Cue Points...": "设置 Cue 点...",
        "Copy Sound Button": "复制声音按钮",
        "Paste": "粘贴",
        "Highlight On": "高亮开",
        "Highlight Off": "高亮关",
        "Lock On": "锁定开",
        "Lock Off": "锁定关",
        "Mark as Played (Red) On": "标记为已播放（红色）开",
        "Mark as Played (Red) Off": "标记为已播放（红色）关",
        "Change Button Colour": "更改按钮颜色",
        "Clear Button Colour": "清除按钮颜色",
        "Clear Cue": "清除 Cue",
        "Cue Page": "Cue 页面",
        "(Blank Page)": "（空白页面）",
        "Page ": "页面 ",
        "Play List is already disabled on all pages.": "所有页面的播放列表已是禁用状态。",
        "Play List has been disabled on all pages.": "所有页面的播放列表已被禁用。",
        "Sports Sounds Pro Page Library folder:\n": "Sports Sounds Pro 页面库文件夹:\n",
        "No duplicate sound buttons found.": "未发现重复的声音按钮。",
        "No invalid sound button paths found.": "未发现无效的声音按钮路径。",
        "No sound buttons assigned.": "未分配任何声音按钮。",
        "No sound button hot keys assigned.": "未分配任何声音按钮快捷键。",
        "Group - ": "分组 - ",
        "Group - Cue": "分组 - Cue",
        "Page - ": "页面 - ",
        "Page - Cue": "页面 - Cue",
        "NOW PLAYING:": "正在播放:",
        "NOW PLAYING: ": "正在播放: ",
        "button": "按钮",
        "Total Time": "总时长",
        "Elapsed": "已播放",
        "Remaining": "剩余",
        "Left": "左",
        "Right": "右",
        "Volume": "音量",
        "Fade In": "淡入",
        "Fade Out": "淡出",
        "Fade in on start": "开始时淡入",
        "Fade out on stop/switch": "停止/切换时淡出",
        "Cross fade (fade out + fade in)": "交叉淡化（淡出 + 淡入）",
        "TIMECODE ENABLED: Multi-Play is not designed for timecode. Unexpected behaviour could happen.": "时间码已启用：多重播放并非为时间码设计，可能出现异常行为。",
        "BUTTON DRAG MODE ENABLED: Playback is not allowed. ": "按钮拖拽模式已启用：不允许播放。",
        "Drag a sound button with the mouse, drag over Group/Page targets, then drop on a destination button.": "用鼠标拖动声音按钮，拖到分组/页面目标后，再放到目标按钮上。",
        "Playback is not allowed while Button Drag is enabled.": "启用按钮拖拽时不允许播放。",
        "Stop fade in progress. Click Stop again to force stop (skip fade).": "正在执行停止淡出。再次点击停止可强制停止（跳过淡出）。",
        "Web Remote is ": "网页遥控状态：",
        "LTC: ": "LTC: ",
        "MTC: ": "MTC: ",
        "Timecode: ": "时间码: ",
        "Enabled": "启用",
        "Disabled": "禁用",
        "Freeze Timecode (relative to actual audio file)": "冻结时间码（相对于实际音频文件）",
        "Freeze Timecode (relative to cue set point)": "冻结时间码（相对于 Cue 设定点）",
        "Follow Media/Audio Player (relative to actual audio file)": "跟随媒体/音频播放器（相对于实际音频文件）",
        "Follow Media/Audio Player (relative to cue set point)": "跟随媒体/音频播放器（相对于 Cue 设定点）",
        "File": "文件",
        "Setup": "设置",
        "Tools": "工具",
        "Logs": "日志",
        "Export": "导出",
        "Page Name": "页面名称",
        "Page name is required.": "页面名称为必填项。",
        "Delete Button": "删除按钮",
        "Delete this button?": "删除此按钮？",
        "Button Drag": "按钮拖拽",
        "Replace": "替换",
        "Swap": "交换",
        "Insert Place Marker": "插入位置标记",
        "Edit Place Marker": "编辑位置标记",
        "Page note text is required.": "页面备注文本为必填项。",
        "File not found:\n": "找不到文件:\n",
        "Export Page Failed": "导出页面失败",
        "Page Exported": "页面已导出",
        "Exported page to:\n": "页面已导出到:\n",
        "Import Page Failed": "导入页面失败",
        "Could not open folder:\n": "无法打开文件夹:\n",
        "Could not export file:\n": "无法导出文件:\n",
        "Exported:\n": "已导出:\n",
        "Saved set file:\n": "已保存集合文件:\n",
        "Could not save set file:\n": "无法保存集合文件:\n",
        "Could not load set file:\n": "无法加载集合文件:\n",
        "No log file yet.\n": "暂无日志文件。\n",
        "Could not open log file:\n": "无法打开日志文件:\n",
        "Could not start Web Remote service:\n": "无法启动网页遥控服务:\n",
        "Sports Sounds Pro Page Library folder:\n": "Sports Sounds Pro 页面库文件夹:\n",
        "Page Library Folder Path": "页面库文件夹路径",
        "Display .set File and Path": "显示 .set 文件及路径",
        "Export Page and Sound Buttons": "导出页面和声音按钮",
        "Yes": "是",
        "No": "否",
        "Discard": "不保存",
        "OK": "确定",
        "Press key": "按下按键",
        "System Hotkey": "系统快捷键",
        "Quick Action Key": "快速触发键",
        "Sound Button Hot Key": "声音按钮快捷键",
        "Each operation supports two hotkeys. You can clear either key.": "每个操作支持两个快捷键。可清除任一按键。",
        "Enable Quick Action Key (assign broadcast short key)": "启用快速触发键（分配广播短键）",
        "Button ": "按钮 ",
        "Enable Sound Button Hot Key": "启用声音按钮快捷键",
        "Priority": "优先级",
        "Sound Button Hot Key has highest priority": "声音按钮快捷键优先级最高",
        "System Hotkey and Quick Action Key have highest priority": "系统快捷键和快速触发键优先级最高",
        "Go To Playing after trigger": "触发后跳转到正在播放",
        "Sound Button States": "声音按钮状态",
        "Playing": "正在播放",
        "Played": "已播放",
        "Unplayed": "未播放",
        "Highlight": "高亮",
        "Lock": "锁定",
        "Error": "错误",
        "Place Marker": "位置标记",
        "Empty": "空",
        "Copied To Cue": "已复制到 Cue",
        "Indicators": "指示器",
        "Cue Indicator": "Cue 指示器",
        "Volume Indicator": "音量指示器",
        "Sound Button Text:": "声音按钮文字:",
        "Group Buttons": "分组按钮",
        "Active Group:": "当前分组:",
        "Inactive Group:": "非当前分组:",
        "Fader Trigger": "推子触发",
        "Allow fader on Quick Action key active": "快速触发键激活时允许推子",
        "Allow fader on Sound Button hot key active": "声音按钮快捷键激活时允许推子",
        "Fade on Pause": "暂停时淡出",
        "Fade on Resume (when paused)": "恢复时淡入（暂停状态）",
        "Fade on Stop": "停止时淡出",
        "During fade, click Stop again to force stop (skip fade).": "淡出期间再次点击停止可强制停止（跳过淡出）。",
        "Note: These options work only when the matching Fade In/Fade Out control is active.": "注意：这些选项仅在对应淡入/淡出控制开启时生效。",
        "Fade Timing": "淡入淡出时长",
        "Fade In Seconds:": "淡入秒数:",
        "Fade Out Seconds:": "淡出秒数:",
        "Fade out when done playing": "播放结束时淡出",
        "Length from end to start Fade Out:": "距结尾多长时间开始淡出:",
        "Cross Fade Seconds:": "交叉淡化秒数:",
        "Max Multi-Play Songs:": "多重播放最大歌曲数:",
        "When max songs is reached during Multi-Play:": "多重播放达到最大歌曲数时:",
        "Disallow more play": "禁止继续播放",
        "Stop the oldest": "停止最早的",
        "Main Player Timeline / Jog Display:": "主播放器时间线 / 拖动显示:",
        "Relative to Cue Set Points": "相对 Cue 设定点",
        "Relative to Actual Audio File": "相对实际音频文件",
        "When jog is outside cue area (Audio File mode):": "拖动在 Cue 区域外时（音频文件模式）:",
        "Stop immediately": "立即停止",
        "Ignore cue and play until end or stopped": "忽略 Cue，播放到结束或手动停止",
        "Play to next cue or stop (before start: stop at start; after stop: play to end)": "播放到下一个 Cue 或停止（起点前：停在起点；终点后：播到结尾）",
        "Play to stop cue (before start: stop at stop cue; after stop: play to end)": "播放到结束 Cue（起点前：停在结束 Cue；终点后：播到结尾）",
        "Audio Playback": "音频播放",
        "Playback Device:": "播放设备:",
        "Refresh": "刷新",
        "Timecode Display Timeline": "时间码显示时间线",
        "SMPTE Timecode (LTC)": "SMPTE 时间码 (LTC)",
        "Output Device:": "输出设备:",
        "Frame Rate:": "帧率:",
        "Sample Rate:": "采样率:",
        "Bit Depth:": "位深:",
        "MIDI Timecode (MTC)": "MIDI 时间码 (MTC)",
        "None (disabled)": "无（禁用）",
        "MIDI Output Device:": "MIDI 输出设备:",
        "Idle Behavior:": "空闲行为:",
        "Keep stream alive (no dark)": "保持流活动（不黑屏）",
        "Allow dark when idle": "空闲时允许黑屏",
        "Talk Volume Level:": "讲话音量级别:",
        "Talk Fade Seconds:": "讲话淡入淡出秒数:",
        "Blink Talk Button": "闪烁讲话按钮",
        "Talk Button:": "讲话按钮:",
        "Use Talk level as % of current volume": "将讲话级别作为当前音量百分比",
        "Lower to Talk level only": "仅降低到讲话级别",
        "Set exactly to Talk level": "精确设为讲话级别",
        "Talk Volume Behavior": "讲话音量行为",
        "Enable Web Remote (Flask API)": "启用网页遥控（Flask API）",
        "Web Remote:": "网页遥控:",
        "Port:": "端口:",
        "Open URL:": "打开 URL:",
        "Mode:": "模式:",
        "System Default": "系统默认",
        "Follow playback device setting": "跟随播放设备设置",
        "Use system default": "使用系统默认",
        "None (mute output)": "无（静音输出）",
        "Detected ": "检测到 ",
        " output device(s).": " 个输出设备。",
        "No explicit device list detected. System Default will be used.": "未检测到明确设备列表。将使用系统默认。",
        "Hotkey conflict detected. Fix duplicates before saving.": "检测到快捷键冲突。保存前请修复重复项。",
        "Quick Action": "快速触发",
        "and": "和",
        "more": "更多",
        "Active Button Color": "活动按钮颜色",
        "Inactive Button Color": "非活动按钮颜色",
        "Color": "颜色",
        "Sound Button Text Color": "声音按钮文字颜色",
    }
}

_PREFIX_TRANSLATIONS = {
    LANG_ZH_CN: {
        "Total ": "总计 ",
        "Elapsed ": "已播放 ",
        "Remaining ": "剩余 ",
        "In ": "入点 ",
        "Out ": "出点 ",
        "Now Playing: ": "正在播放: ",
        "Button: ": "按钮: ",
        "Could not export file:\n": "无法导出文件:\n",
        "Could not load set file:\n": "无法加载集合文件:\n",
        "Could not save set file:\n": "无法保存集合文件:\n",
        "Saved set file:\n": "已保存集合文件:\n",
        "Exported:\n": "已导出:\n",
        "Exported page to:\n": "页面已导出到:\n",
        "File not found:\n": "找不到文件:\n",
        "Could not open folder:\n": "无法打开文件夹:\n",
        "No log file yet.\n": "暂无日志文件。\n",
        "Could not open log file:\n": "无法打开日志文件:\n",
        "Could not start Web Remote service:\n": "无法启动网页遥控服务:\n",
    }
}


def normalize_language(value: str) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if raw in {"zh", "zh_cn", "zh_hans", "cn"}:
        return LANG_ZH_CN
    return LANG_EN


def set_current_language(value: str) -> str:
    global _current_language
    _current_language = normalize_language(value)
    return _current_language


def get_current_language() -> str:
    return _current_language


def tr(text: str, language: Optional[str] = None) -> str:
    return translate_text(text, language)


def translate_text(text: str, language: Optional[str] = None) -> str:
    if not isinstance(text, str) or not text:
        return text
    lang = normalize_language(language or _current_language)
    if lang == LANG_EN:
        return text
    table = _TRANSLATIONS.get(lang, {})
    if text in table:
        return table[text]
    for prefix, translated_prefix in _PREFIX_TRANSLATIONS.get(lang, {}).items():
        if text.startswith(prefix):
            return translated_prefix + text[len(prefix):]
    return text


def _ensure_source_property(obj, prop_name: str, current_value: str, language: str) -> str:
    source = obj.property(prop_name)
    if isinstance(source, str) and source:
        return source
    if language != LANG_EN and isinstance(current_value, str) and current_value:
        obj.setProperty(prop_name, current_value)
        return current_value
    return current_value


def _set_widget_text(widget, source: str, language: str) -> None:
    target = source if language == LANG_EN else translate_text(source, language)
    if widget.text() != target:
        widget.setText(target)


def localize_widget_tree(widget: QWidget, language: Optional[str] = None) -> None:
    lang = normalize_language(language or _current_language)
    _localize_widget(widget, lang)
    for child in widget.findChildren(QWidget):
        _localize_widget(child, lang)
    for action in widget.findChildren(QAction):
        _localize_action(action, lang)


def _localize_widget(widget: QWidget, language: str) -> None:
    title = widget.windowTitle()
    if title:
        source_title = _ensure_source_property(widget, "_i18n_source_window_title", title, language)
        widget.setWindowTitle(source_title if language == LANG_EN else translate_text(source_title, language))

    if isinstance(widget, QLabel):
        source = _ensure_source_property(widget, "_i18n_source_text", widget.text(), language)
        _set_widget_text(widget, source, language)
    elif isinstance(widget, (QPushButton, QCheckBox, QRadioButton)):
        source = _ensure_source_property(widget, "_i18n_source_text", widget.text(), language)
        _set_widget_text(widget, source, language)
    elif isinstance(widget, QGroupBox):
        title = widget.title()
        source = _ensure_source_property(widget, "_i18n_source_title", title, language)
        target = source if language == LANG_EN else translate_text(source, language)
        if widget.title() != target:
            widget.setTitle(target)
    elif isinstance(widget, QMenu):
        title = widget.title()
        source = _ensure_source_property(widget, "_i18n_source_title", title, language)
        target = source if language == LANG_EN else translate_text(source, language)
        if widget.title() != target:
            widget.setTitle(target)
        menu_action = widget.menuAction()
        action_source = _ensure_source_property(menu_action, "_i18n_source_text", source, language)
        action_target = action_source if language == LANG_EN else translate_text(action_source, language)
        if menu_action.text() != action_target:
            menu_action.setText(action_target)
    elif isinstance(widget, QLineEdit):
        placeholder = widget.placeholderText()
        if placeholder:
            source = _ensure_source_property(widget, "_i18n_source_placeholder", placeholder, language)
            widget.setPlaceholderText(source if language == LANG_EN else translate_text(source, language))
    elif isinstance(widget, QComboBox):
        for i in range(widget.count()):
            source = widget.itemData(i, SOURCE_TEXT_ROLE)
            if not isinstance(source, str) or not source:
                source = widget.itemText(i)
                if language != LANG_EN:
                    widget.setItemData(i, source, SOURCE_TEXT_ROLE)
            widget.setItemText(i, source if language == LANG_EN else translate_text(source, language))
    elif isinstance(widget, QListWidget):
        for i in range(widget.count()):
            item = widget.item(i)
            if item is None:
                continue
            source = item.data(SOURCE_TEXT_ROLE)
            if not isinstance(source, str) or not source:
                source = item.text()
                if language != LANG_EN:
                    item.setData(SOURCE_TEXT_ROLE, source)
            item.setText(source if language == LANG_EN else translate_text(source, language))
    elif isinstance(widget, QTabWidget):
        for i in range(widget.count()):
            source = widget.tabBar().tabData(i)
            if not isinstance(source, str) or not source:
                source = widget.tabText(i)
                if language != LANG_EN:
                    widget.tabBar().setTabData(i, source)
            widget.setTabText(i, source if language == LANG_EN else translate_text(source, language))
    elif isinstance(widget, QDialogButtonBox):
        for button in widget.buttons():
            source = _ensure_source_property(button, "_i18n_source_text", button.text(), language)
            _set_widget_text(button, source, language)


def _localize_action(action: QAction, language: str) -> None:
    text = action.text()
    if text:
        source = _ensure_source_property(action, "_i18n_source_text", text, language)
        action.setText(source if language == LANG_EN else translate_text(source, language))
    tip = action.toolTip()
    if tip:
        source = _ensure_source_property(action, "_i18n_source_tooltip", tip, language)
        action.setToolTip(source if language == LANG_EN else translate_text(source, language))
    status_tip = action.statusTip()
    if status_tip:
        source = _ensure_source_property(action, "_i18n_source_status_tip", status_tip, language)
        action.setStatusTip(source if language == LANG_EN else translate_text(source, language))


class _AutoLocalizer(QObject):
    def eventFilter(self, obj, event):  # noqa: N802
        if _auto_localizer_state["busy"]:
            return False
        if event is None:
            return False
        if event.type() not in {QEvent.Show, QEvent.Polish, QEvent.WindowTitleChange}:
            return False
        if not isinstance(obj, QWidget):
            return False
        try:
            _auto_localizer_state["busy"] = True
            localize_widget_tree(obj, _current_language)
        finally:
            _auto_localizer_state["busy"] = False
        return False


def install_auto_localization(app: QApplication) -> None:
    if app is None:
        return
    if _auto_localizer_state["filter"] is None:
        _auto_localizer_state["filter"] = _AutoLocalizer(app)
        app.installEventFilter(_auto_localizer_state["filter"])


def apply_application_font(app: QApplication, language: Optional[str] = None) -> None:
    if app is None:
        return
    lang = normalize_language(language or _current_language)
    if _font_state["default"] is None:
        _font_state["default"] = QFont(app.font())
    if lang == LANG_EN:
        app.setFont(QFont(_font_state["default"]))
        return
    preferred = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "SimHei",
    ]
    families = {name.lower(): name for name in QFontDatabase().families()}
    chosen = None
    for name in preferred:
        if name.lower() in families:
            chosen = families[name.lower()]
            break
    if not chosen:
        return
    font = QFont(app.font())
    font.setFamily(chosen)
    app.setFont(font)


_current_language = LANG_EN
_auto_localizer_state = {"filter": None, "busy": False}
_font_state = {"default": None}
