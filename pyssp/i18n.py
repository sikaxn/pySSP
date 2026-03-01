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
        "Lock Screen": "锁屏",
        "Hotkey": "快捷键",
        "Midi Control": "MIDI 控制",
        "Colour": "颜色",
        "Display": "显示",
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
        "Main Transport Display": "主时间线显示",
        "Display Progress Bar": "显示进度条",
        "Display Waveform": "显示波形",
        "If Main Transport uses Waveform display, it is recommended to enable Audio Preload for better performance.": "如果主时间线使用波形显示，建议启用音频预加载以获得更好的性能。",
        "Show transport text on progress display": "在进度显示上显示传输文本",
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
        "Show Display": "显示舞台屏",
        "Stage Display Setting": "舞台显示设置",
        "Stage display setting": "舞台显示设置",
        "Send Alert": "发送通知",
        "Timecode Panel": "时间码面板",
        "Duplicate Check": "重复检查",
        "Verify Sound Buttons": "验证声音按钮",
        "Disable Play List on All Pages": "禁用所有页面播放列表",
        "Display Page Library Folder Path": "显示页面库文件夹路径",
        "Display .set File and Path": "显示 .set 文件及路径",
        "Export Page and Sound Buttons to Excel": "导出页面和声音按钮到 Excel",
        "List Sound Buttons": "列出声音按钮",
        "List Sound Button Hot Key": "列出声音按钮快捷键",
        "List Sound Device MIDI Mapping": "列出声音设备 MIDI 映射",
        "View Log": "查看日志",
        "About": "关于",
        "Help": "帮助",
        "Lock / Unlock": "锁定 / 解锁",
        "Get the Latest Version": "获取最新版本",
        "Tips": "小贴士",
        "Register": "注册",
        "Exit": "退出",
        "Open on startup": "启动时打开",
        "Previous": "上一个",
        "Next": "下一个",
        "No tips available.": "没有可用的小贴士。",
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
        "Loop List": "循环列表",
        "Loop Single": "单曲循环",
        "Next": "下一首",
        "Button Drag": "按钮拖拽",
        "Pause": "暂停",
        "Rapid Fire": "连发",
        "Shuffle": "随机",
        "Reset Page": "重置页面",
        "STOP": "停止",
        "Play List": "播放列表",
        "Playback Candidate Rules:": "播放候选规则：",
        "Control": "控制",
        "Play unplayed only": "仅播放未播放",
        "Play any (ignore red) available": "播放任意可用（忽略红色）",
        "When Loop is enabled in Play List:": "播放列表启用循环时：",
        "When Play List/Next/Rapid Fire hits audio load error (purple):": "播放列表/下一首/连发遇到音频加载错误（紫色）时：",
        "Stop playback": "停止播放",
        "Keep playing": "继续播放",
        "Audio Load Failed:": "音频加载失败：",
        "Talk*": "讲话闪避*",
        "Add Sound Button": "添加声音按钮",
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
        "Paste Sound Button": "粘贴声音按钮",
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
        "Midi Setting": "MIDI 设置",
        "System Rotary": "系统旋钮",
        "Quick Action Key": "快速触发键",
        "Sound Button Hot Key": "声音按钮快捷键",
        "Unassigned": "未分配",
        "Select one or more MIDI input devices. pySSP will listen on all selected devices.": "选择一个或多个 MIDI 输入设备。pySSP 会监听所有已选设备。",
        "Method of Unlock": "解锁方式",
        "Click 3 random points": "点击 3 个随机位置",
        "Click one button in a fixed position": "点击固定位置的一个按钮",
        "Slide to unlock": "滑动解锁",
        "Web Remote always keeps working while the lock screen is active.": "锁屏启用时，网页遥控始终可用。",
        "Allow While Locked": "锁定时允许",
        "These settings apply to the regular lock screen.": "这些设置适用于普通锁屏。",
        "Allow closing pySSP while locked": "锁定时允许关闭 pySSP",
        "Allow standard hotkeys while locked": "锁定时允许标准快捷键",
        "Allow Quick Action keys while locked": "锁定时允许快速触发键",
        "Allow Sound Button hotkeys while locked": "锁定时允许声音按钮快捷键",
        "Allow MIDI control while locked": "锁定时允许 MIDI 控制",
        "Allow While Auto Locked": "自动化锁定时允许",
        "Allow closing pySSP while auto locked": "自动化锁定时允许关闭 pySSP",
        "Allow MIDI control while auto locked": "自动化锁定时允许 MIDI 控制",
        "Keyboard shortcuts except Unlock are all disabled while automation lock is active.": "自动化锁定启用时，除解锁外，所有键盘快捷键都会被禁用。",
        "Password": "密码",
        "Require password for unlock": "解锁时需要密码",
        "Password has been set. Start typing to change it.": "密码已设置。如需修改，直接开始输入即可。",
        "Password:": "密码:",
        "Verify Password:": "确认密码:",
        "Re-enter new password to change it.": "重新输入新密码以进行修改。",
        "Warning: this password is stored as plain text in the settings file.": "警告：此密码会以明文形式保存在设置文件中。",
        "After Restart": "重新启动后",
        "Start unlocked": "启动时保持未锁定",
        "Start locked again if pySSP closed while locked": "如果 pySSP 在锁定时关闭，则启动后再次锁定",
        "Password is required when changing the password.": "修改密码时必须输入密码。",
        "Password and Verify Password must match.": "密码与确认密码必须一致。",
        "Password is required when password unlock is enabled.": "启用密码解锁时必须设置密码。",
        "Password has been set. Start typing in Password to change it.": "密码已设置。如需修改，请在密码框中直接输入。",
        "No password has been set yet.": "尚未设置密码。",
        "Type a new password and verify it to save the change.": "输入新密码并确认后即可保存修改。",
        "Password fields are ignored until you start typing.": "在你开始输入之前，密码栏位会被忽略。",
        "Password unlock is disabled.": "密码解锁已禁用。",
        "Screen Locked": "屏幕已锁定",
        "Click all 3 targets to unlock.": "点击全部 3 个目标点以解锁。",
        "Click the unlock button to continue.": "点击解锁按钮以继续。",
        "Slide all the way to unlock.": "将滑块拖到底以解锁。",
        "Unlock": "解锁",
        "Unlock the screen before closing pySSP.": "关闭 pySSP 前请先解锁屏幕。",
        "Lock screen is active.": "锁屏已启用。",
        "Lock screen released.": "锁屏已解除。",
        "Automation lock is active.": "自动化锁定已启用。",
        "Automation lock released.": "自动化锁定已解除。",
        "Automation lock released by Web Remote.": "自动化锁定已通过网页遥控解除。",
        "Unlock pySSP": "解锁 pySSP",
        "Type unlock and press Enter to unlock.": "输入 unlock 并按回车以解锁。",
        "Enter password and press Enter to unlock.": "输入密码并按回车以解锁。",
        "Press Enter to unlock.": "按回车以解锁。",
        "Type sure to unlock and press Enter to unlock remote automation control.": "输入 sure to unlock 并按回车，以解除远程自动化控制锁定。",
        "Type sure to unlock to continue.": "请输入 sure to unlock 以继续。",
        "Password is also required.": "还需要输入密码。",
        "Type unlock to continue.": "请输入 unlock 以继续。",
        "Password is incorrect.": "密码错误。",
        "Automation lock is active. pySSP is expected to be controlled remotely. Unlock only for troubleshooting when you are sure.": "自动化锁定已启用。当前预期 pySSP 由远程控制。仅可在排障且你确定需要时才解锁。",
        "Disconnected MIDI device selected:": "已选 MIDI 设备已断开：",
        "Device used for MTC can't be used for MIDI control:": "用于 MTC 的设备不能用于 MIDI 控制：",
        "MIDI input disconnected:": "MIDI 输入已断开：",
        "MIDI control will resume automatically when reconnected.": "设备重新连接后，MIDI 控制将自动恢复。",
        "MIDI input reconnected:": "MIDI 输入已重新连接：",
        "MIDI control restored.": "MIDI 控制已恢复。",
        "Configure MTC output in Audio Device / Timecode.": "请在“音频设备 / 时间码”中配置 MTC 输出。",
        "Enable System Rotary MIDI Control": "启用系统旋钮 MIDI 控制",
        "Group Rotary:": "分组旋钮:",
        "Page Rotary:": "页面旋钮:",
        "Sound Button Rotary:": "声音按钮旋钮:",
        "Volume Control:": "音量控制:",
        "Jog Control:": "Jog 控制:",
        "Volume Mode:": "音量模式:",
        "Relative (rotary encoder)": "相对（旋钮编码器）",
        "Absolute (slider/fader)": "绝对（滑杆/推子）",
        "Volume Relative Step:": "音量相对步进:",
        "Jog Relative Step:": "Jog 相对步进:",
        "Sensitivity:": "灵敏度:",
        "Learn": "学习",
        "Rotary learns Control Change (CC) by control number. For direction, pySSP uses CC value.": "旋钮学习按控制号识别 Control Change (CC)。方向由 CC 值判断。",
        "Enable MIDI Quick Action": "启用 MIDI 快速触发",
        "Enable Sound Button MIDI Hot Key": "启用声音按钮 MIDI 热键",
        "Sound Button MIDI Hot Key has highest priority": "声音按钮 MIDI 热键优先级最高",
        "System MIDI Hotkey and Quick Action have highest priority": "系统 MIDI 热键和快速触发优先级最高",
        "Assign per-button MIDI hotkeys in Edit Sound Button.": "在“编辑声音按钮”中为每个按钮分配 MIDI 热键。",
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
        "Paused": "已暂停",
        "Not Playing": "未播放",
        "Stage Display": "舞台显示",
        "Current Time": "当前时间",
        "Alert": "通知",
        "Elapsed": "已播放",
        "Remaining": "剩余",
        "Progress": "进度",
        "Now Playing": "当前播放",
        "Next Playing": "下一播放",
        "Song Name": "歌曲名称",
        "Next Song": "下一首",
        "Progress Bar": "进度条",
        "Gadgets": "组件",
        "Preview": "预览",
        "Gadget": "组件",
        "Visible / Edit": "显示 / 编辑",
        "Hide Text": "隐藏文字",
        "Hide Border": "隐藏边框",
        "Orientation": "方向",
        "Layer": "层级",
        "Horizontal": "水平",
        "Vertical": "垂直",
        "Up": "上移",
        "Down": "下移",
        "Show for Edit": "编辑时显示",
        "Hide for Edit": "编辑时隐藏",
        "Now/Next Text Source:": "当前/下一文本来源:",
        "Drag to reorder rows. Check items to show on the stage display window.": "拖拽可调整行顺序。勾选要在舞台显示窗口显示的项目。",
        "Drag and resize gadgets in the preview. Toggle visibility, then save to apply to Stage Display.": "在预览中拖拽并调整组件大小。切换可见性后保存，以应用到舞台显示。",
        "Next Song is shown when playlist mode is enabled on the active page.": "当当前页面启用播放列表时显示“下一首”。",
        "Alert gadget is always hidden on live Stage Display until an alert is sent.": "实时舞台显示中的通知组件默认始终隐藏，直到发送通知后才会显示。",
        "Alert Message": "通知内容",
        "Type alert text to show on Stage Display": "输入要在舞台显示中显示的通知文本",
        "Keep on screen until cleared": "保持显示直到清除",
        "Seconds": "秒",
        "Send": "发送",
        "Clear Alert": "清除通知",
        "Please enter alert text.": "请输入通知文本。",
        "Filename": "文件名",
        "Note": "备注",
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
        "Audio Preload": "音频预加载",
        "Behavior": "行为",
        "Enable audio preload cache": "启用音频预加载缓存",
        "Preload current page first": "优先预加载当前页面",
        "Auto-free cache when other apps use RAM (FIFO)": "当其他应用占用内存时自动释放缓存（FIFO）",
        "Pause audio preload during playback": "播放期间暂停音频预加载",
        "RAM Limit": "内存上限",
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
        "Port": "端口",
        "Open URL:": "打开 URL:",
        "WEB REMOTE PORT CONFLICT:": "网页遥控端口冲突：",
        "is already in use.": "已被占用。",
        "Change port, disable Web Remote, or close the program using this port.": "请更改端口、禁用网页遥控，或关闭占用该端口的程序。",
        "Restart pySSP to resolve the issue.": "重启 pySSP 以解决该问题。",
        "WEB REMOTE ERROR: Could not start Web Remote service.": "网页遥控错误：无法启动网页遥控服务。",
        "pySSP Already Running": "pySSP 已在运行",
        "Another instance of pySSP is already running.": "另一个 pySSP 实例已在运行。",
        "Close the existing instance, then launch pySSP again.": "请先关闭已运行实例，然后重新启动 pySSP。",
        "SportsSoundsPro Detected": "检测到 SportsSoundsPro",
        "pySSP and SportsSoundsPro are both working on .set files, which might cause issues.": "pySSP 和 SportsSoundsPro 同时处理 .set 文件，可能会引发问题。",
        "Choose Quit to close pySSP now, or Continue to run both.": "选择“退出”可立即关闭 pySSP，或选择“继续”以同时运行。",
        "Quit": "退出",
        "Continue": "继续",
        "Cleanstart Warning": "清理启动警告",
        "Cleanstart will reset all settings to defaults. Continue?": "清理启动会将所有设置重置为默认值。是否继续？",
        "Cleanstart Failed": "清理启动失败",
        "Could not remove settings.ini for cleanstart.": "无法删除用于清理启动的 settings.ini。",
        "Mode:": "模式:",
        "System Default": "系统默认",
        "Follow playback device setting": "跟随播放设备设置",
        "Use system default": "使用系统默认",
        "None (mute output)": "无（静音输出）",
        "Detected ": "检测到 ",
        " output device(s).": " 个输出设备。",
        "No explicit device list detected. System Default will be used.": "未检测到明确设备列表。将使用系统默认。",
        "Hotkey conflict detected. Fix duplicates before saving.": "检测到快捷键冲突。保存前请修复重复项。",
        "MIDI conflict detected. Fix duplicates before saving.": "检测到 MIDI 冲突。保存前请修复重复项。",
        "Quick Action": "快速触发",
        "and": "和",
        "more": "更多",
        "Active Button Color": "活动按钮颜色",
        "Inactive Button Color": "非活动按钮颜色",
        "Color": "颜色",
        "Sound Button Text Color": "声音按钮文字颜色",
        "Select Sound Files": "选择声音文件",
        "Backup pySSP Settings": "备份 pySSP 设置",
        "Restore pySSP Settings": "恢复 pySSP 设置",
        "Backup Keyboard Hotkey Bindings": "备份键盘快捷键绑定",
        "Restore Keyboard Hotkey Bindings": "恢复键盘快捷键绑定",
        "Backup MIDI Bindings": "备份 MIDI 绑定",
        "Restore MIDI Bindings": "恢复 MIDI 绑定",
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
        "System RAM: ": "系统内存: ",
        " | Reserved: ": " | 预留: ",
        " | Max Cache Limit: ": " | 最大缓存上限: ",
        "Selected Cache Limit: ": "所选缓存上限: ",
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
