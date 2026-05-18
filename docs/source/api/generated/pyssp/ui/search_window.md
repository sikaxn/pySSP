# `pyssp/ui/search_window.py`

- Source: `pyssp/ui/search_window.py`
- Module path: `pyssp.ui.search_window`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `SearchWindow`

- Defined at `pyssp/ui/search_window.py:21`
- Bases: QDialog

#### Public Members

- `set_handlers(self, search_handler: Callable[[str], List[dict]], goto_handler: Callable[[dict], None], play_handler: Callable[[dict], None]) -> None` [method] (pyssp/ui/search_window.py:70)
- `focus_query(self) -> None` [method] (pyssp/ui/search_window.py:80)
- `set_double_click_action(self, action: str) -> None` [method] (pyssp/ui/search_window.py:84)
- `run_search(self) -> None` [method] (pyssp/ui/search_window.py:90)
- `go_to_selected(self) -> bool` [method] (pyssp/ui/search_window.py:110)
- `play_selected(self) -> bool` [method] (pyssp/ui/search_window.py:120)
- `activate_selected_by_setting(self) -> bool` [method] (pyssp/ui/search_window.py:130)
- `select_result_delta(self, delta: int) -> bool` [method] (pyssp/ui/search_window.py:135)
- `eventFilter(self, obj, event) -> bool` [method] (pyssp/ui/search_window.py:167)

#### Internal Members

- `__init__(self, parent = None, language: str = 'en') -> None` [constructor] (pyssp/ui/search_window.py:22)
- `_on_item_double_clicked(self, _item) -> None` [method] (pyssp/ui/search_window.py:147)
- `_selected_match(self) -> Optional[dict]` [method] (pyssp/ui/search_window.py:150)
- `_return_to_main_window(self) -> None` [method] (pyssp/ui/search_window.py:159)
