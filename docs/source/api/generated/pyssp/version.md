# `pyssp/version.py`

- Source: `pyssp/version.py`
- Module path: `pyssp.version`
- API entries: `10`

## Module Docstring

No module docstring.

## Constants

### Public

- `DEV_VERSION` [constant] (pyssp/version.py:8)
  Detail: Value: '0.0.0 dev'
- `FALLBACK_BUILD_VERSION` [constant] (pyssp/version.py:9)
  Detail: Value: '0.0.0'

## Functions

### Public

- `get_configured_version() -> str` [function] (pyssp/version.py:26)
- `get_configured_build_id() -> str` [function] (pyssp/version.py:49)
- `get_display_version() -> str` [function] (pyssp/version.py:54)
- `get_display_build_id() -> str` [function] (pyssp/version.py:60)
- `is_beta_version(version_text: str = '') -> bool` [function] (pyssp/version.py:66)
- `get_app_title_base() -> str` [function] (pyssp/version.py:71)

### Internal

- `_candidate_version_paths() -> list[Path]` [function] (pyssp/version.py:12)
- `_read_version_payload() -> dict` [function] (pyssp/version.py:38)
