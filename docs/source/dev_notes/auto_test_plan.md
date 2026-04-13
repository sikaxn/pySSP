# pySSP Auto-Test Implementation Plan

This file is maintained under `docs/source/dev_notes/` as part of the Development Notes hierarchy.

## Why this plan exists

We currently have regressions caused by missing automated checks on important code paths.
`openlp` uses a strong `pytest` workflow, explicit test docs, and CI-first execution. This plan mirrors that approach for `pySSP`.

## Current baseline (2026-04-13)

- Existing suite size: `92` tests.
- Current local result: `72 passed`, `20 failed`.
- Failing areas:
  - `tests/test_options_dialog_ui.py` (constructor drift)
  - `tests/test_system_info_dialog.py` (async worker behavior mismatch)
  - `tests/test_set_loader.py` (lyric-path normalization expectation mismatch)
  - `tests/test_lyrics.py` (offset behavior mismatch)
  - `tests/test_library_archive.py` (platform path expectation mismatch)

## Enforcement strategy

1. Run a required **core regression suite** in CI now.
2. Run full suite in CI as **advisory** until red tests are fixed.
3. Move tests from advisory scope to core scope as soon as they are stable.
4. When full suite is green consistently, make full suite required.

This keeps CI useful immediately while we burn down existing red tests.

## Phase plan

### Phase 0: Baseline and guardrails (now)

- Add root `pytest.ini` with shared config.
- Add CI workflow:
  - Required `core-regression` job (stable tests only).
  - Advisory `full-suite` job with coverage report.
- Document all known failing tests and owners.

### Phase 1: Burn down known failures

- Fix or re-baseline each known failing test, one area at a time:
  - `OptionsDialog` signature drift and defaults.
  - `SystemInformationDialog` async completion synchronization.
  - `set_loader` and `lyrics` expected behavior alignment.
  - `library_archive` platform path behavior.
- Rule: no new features merged if they add new failing tests.

### Phase 2: Expand function coverage (priority order)

1. `set_loader.py`
   - malformed page sections
   - edge case cue parsing
   - timecode offset formatting/parsing
2. `settings_store.py`
   - normalize/clamp helpers
   - parser conversions for legacy keys
   - round-trip save/load invariants
3. `timecode.py`
   - frame/time conversions
   - LTC bit encoding invariants
4. `audio_format_support.py`, `path_safety.py`, `version.py`
   - pure function parameterized tests
5. `web_remote.py`
   - API dispatch error-path tests
   - invalid payload/path tests
6. `library_archive.py`
   - member path sanitization and rewrite behavior
7. UI contracts (`ui/*.py`)
   - constructor defaults
   - signal/slot behavior for key toggles
   - platform-independent widget logic

### Phase 3: Coverage ratchet

- Start with advisory coverage report only.
- After red tests are resolved:
  - set minimum `--cov-fail-under=45`
  - raise by +5 every 2-3 sprints to target `70+`
- Do not increase threshold on the same PR that introduces large new modules unless tests are included.

## Test design conventions (from openlp style)

- Use `pytest` + fixtures + parametrization.
- Favor pure-function tests first for deterministic fast coverage.
- Use monkeypatch/mocks for IO, subprocess, and device layers.
- Keep GUI tests offscreen (`QT_QPA_PLATFORM=offscreen`).
- Keep each bug fix PR with:
  - one regression test first
  - implementation fix second

## CI scope today

- Required:
  - all tests except current known failing files:
    - `tests/test_options_dialog_ui.py`
    - `tests/test_system_info_dialog.py`
    - `tests/test_set_loader.py`
    - `tests/test_lyrics.py`
    - `tests/test_library_archive.py`
- Advisory:
  - full `pytest tests --cov=pyssp`

## Development notes log

### 2026-04-13

- Added `pytest.ini` at repo root.
- Added `.github/workflows/tests.yml` with required core and advisory full suite.
- Added this plan file as the central engineering note for test expansion.
- Added seeded UI monkey testing (`pytest -m monkey`) for `OptionsDialog`.
- Added dummy media + lyric integration tests and settings-combination matrix tests
  (`tests/test_media_and_settings_combinations.py`) to validate behavior changes under option combinations.
- Added media-format matrix tests (`tests/test_media_format_matrix.py`) covering repo sample
  `.wav/.mp3/.ogg/.flac`, generated extra audio formats, and video-with-audio vs video-without-audio detection.
- Fixed `media_has_audio_stream()` fallback parsing so ffmpeg output is interpreted correctly when ffprobe is unavailable.
- Expanded monkey testing to include pairwise settings-combination coverage across major
  options dimensions (`tests/test_monkey_options_dialog.py`) in addition to seeded random user-flow actions.
- Added full-application monkey coverage (`tests/test_monkey_main_window.py`) that exercises
  `MainWindow` user flows (add sound, group/page navigation, playback-control toggles, rapid-fire behavior)
  under pairwise settings combinations with dummy media/lyric files.
