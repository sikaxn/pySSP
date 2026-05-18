# `pyssp/ui/crash_report_dialog.py`

- Source: `pyssp/ui/crash_report_dialog.py`
- Module path: `pyssp.ui.crash_report_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `CrashReportDialog`

- Defined at `pyssp/ui/crash_report_dialog.py:26`
- Bases: QDialog

#### Internal Members

- `__init__(self, exc_type: Type[BaseException], exc_value: BaseException, exc_tb, parent = None) -> None` [constructor] (pyssp/ui/crash_report_dialog.py:27)
- `_build_ui(self) -> None` [method] (pyssp/ui/crash_report_dialog.py:35)
- `_build_report_text(self) -> str` [method] (pyssp/ui/crash_report_dialog.py:77)
- `_copy_report(self) -> None` [method] (pyssp/ui/crash_report_dialog.py:98)
- `_save_report(self) -> None` [method] (pyssp/ui/crash_report_dialog.py:104)
