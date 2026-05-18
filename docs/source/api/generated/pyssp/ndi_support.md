# `pyssp/ndi_support.py`

- Source: `pyssp/ndi_support.py`
- Module path: `pyssp.ndi_support`
- API entries: `12`

## Module Docstring

No module docstring.

## Constants

### Public

- `NDI_DOWNLOAD_URL` [constant] (pyssp/ndi_support.py:13)
  Detail: Value: 'https://ndi.video/tools/'
- `NDI_RUNTIME_DOWNLOAD_URL` [constant] (pyssp/ndi_support.py:14)
  Detail: Value: 'https://ndi.link/NDIRedistV6'

## Functions

### Public

- `probe_ndi_capability(force_refresh: bool = False) -> NDICapabilityStatus` [function] (pyssp/ndi_support.py:208)
- `ndi_status_lines(status: NDICapabilityStatus | None = None) -> List[str]` [function] (pyssp/ndi_support.py:248)

### Internal

- `_existing_paths(candidates: List[str]) -> List[str]` [function] (pyssp/ndi_support.py:46)
- `_env_dir(var_name: str) -> str` [function] (pyssp/ndi_support.py:68)
- `_macos_bundle_framework_candidates() -> List[str]` [function] (pyssp/ndi_support.py:81)
- `_runtime_candidates() -> tuple[str, List[str]]` [function] (pyssp/ndi_support.py:94)
- `_sdk_candidates() -> List[str]` [function] (pyssp/ndi_support.py:130)
- `_runtime_library_file_candidates(root: str) -> List[str]` [function] (pyssp/ndi_support.py:156)
- `_resolve_runtime_library_path(runtime_paths: List[str], sdk_paths: List[str]) -> str` [function] (pyssp/ndi_support.py:187)

## Classes

### `NDICapabilityStatus`

- Defined at `pyssp/ndi_support.py:19`

#### Public Members

- `ready(self) -> bool` [property] (pyssp/ndi_support.py:39)
