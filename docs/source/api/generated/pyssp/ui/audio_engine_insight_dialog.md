# `pyssp/ui/audio_engine_insight_dialog.py`

- Source: `pyssp/ui/audio_engine_insight_dialog.py`
- Module path: `pyssp.ui.audio_engine_insight_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `AudioEngineInsightDialog`

- Defined at `pyssp/ui/audio_engine_insight_dialog.py:23`
- Bases: QDialog

#### Public Members

- `refresh(self) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:84)

#### Internal Members

- `__init__(self, snapshot_provider: Callable[[], dict], parent = None) -> None` [constructor] (pyssp/ui/audio_engine_insight_dialog.py:24)
- `_on_keep_legacy_toggled(self, checked: bool) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:103)
- `_player_identity(self, player: dict) -> str` [method] (pyssp/ui/audio_engine_insight_dialog.py:108)
- `_merge_legacy_players(self, snapshot: dict) -> dict` [method] (pyssp/ui/audio_engine_insight_dialog.py:114)
- `_rebuild_player_list(self) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:146)
- `_on_player_changed(self, row: int) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:165)
- `_show_player_details(self, row: int) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:168)
- `_populate_detail_table(self, rows: List[tuple]) -> None` [method] (pyssp/ui/audio_engine_insight_dialog.py:181)
