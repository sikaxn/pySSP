# `pyssp/system_info_probe.py`

- Source: `pyssp/system_info_probe.py`
- Module path: `pyssp.system_info_probe`
- API entries: `13`

## Module Docstring

No module docstring.

## Functions

### Public

- `build_decoder_report() -> List[str]` [function] (pyssp/system_info_probe.py:258)
- `run_decoder_probe_process() -> List[str]` [function] (pyssp/system_info_probe.py:390)
- `main(argv: List[str] | None = None) -> int` [function] (pyssp/system_info_probe.py:394)

### Internal

- `_dedupe(values: List[str]) -> List[str]` [function] (pyssp/system_info_probe.py:20)
- `_asset_root() -> str` [function] (pyssp/system_info_probe.py:35)
- `_iter_existing_dirs(paths: Sequence[str]) -> Iterable[str]` [function] (pyssp/system_info_probe.py:50)
- `_iter_search_roots(pygame_module) -> Iterable[str]` [function] (pyssp/system_info_probe.py:57)
- `_resolve_sdl_mixer_library_path(pygame_module) -> Tuple[str, List[str]]` [function] (pyssp/system_info_probe.py:123)
- `_load_sdl_mixer_ctypes(pygame_module)` [function] (pyssp/system_info_probe.py:151)
- `_write_pcm_wav(path: str) -> None` [function] (pyssp/system_info_probe.py:202)
- `_write_pcm_aiff(path: str) -> None` [function] (pyssp/system_info_probe.py:210)
- `_functional_sample_paths() -> Dict[str, str]` [function] (pyssp/system_info_probe.py:218)
- `_probe_functional_support(pygame_module) -> Tuple[Dict[str, bool], Dict[str, str]]` [function] (pyssp/system_info_probe.py:228)
