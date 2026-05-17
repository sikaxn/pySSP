# Codex Memory

## 2026-04-29

- Investigated lyric display transparent mode blackout.
- Root cause was in `pyssp/ui/lyric_display.py`: transparent mode still let the top-level window and full-window hover surface paint a background, which could visually black out the display.
- Fix keeps the transparent-mode window, canvas, lyric gadget, and hover surface on explicit transparent backgrounds and enables `WA_NoSystemBackground` on the transparent child widgets involved.
- Transparent lyric outline also came from the lyric gadget retaining a `QFrame.Box` shape; transparent mode now switches it to `QFrame.NoFrame` and restores the box frame in windowed mode.
- The remaining stale-state bug appears in the live switch path when opening lyric display in windowed mode first, then toggling transparent from the toolbar. Cleanup fix: defer restoring visibility until after `setWindowFlags(...)`, `WA_TranslucentBackground`, `WA_NoSystemBackground`, root layout margins, and child widget backgrounds are all updated for transparent mode.
- Follow-up regressions after the live-switch fix: the toolbar overlay height was hard-coded too small and could crop its contents, and the current lyric text was not explicitly restored after transparent-mode widget reconfiguration. `LyricDisplayWindow` now restores `_last_text` after mode switches and sizes the toolbar from `sizeHint()`.
- Added GUI regression coverage in `tests/test_lyric_display_window.py` for transparent-mode and normal-mode background state.
- Correction from runtime testing: forcing `_refresh_lyric_display(force=True)` during the transparent toggle was a bad fix. It can blank the lyric between timestamps, so the switch path should preserve the existing rendered lyric instead of recomputing timing state immediately.
- The `UpdateLayeredWindowIndirect ... dirty=(... -7, 0)` spam points at the transparent hover toolbar painting 7px past the layered surface bounds. Transparent mode now needs a safety inset for the toolbar overlay so repaint stays inside the native window.
- Follow-up toolbar fix: in transparent mode the overlay should size to its content width and stay inside the safe inset, rather than stretching to full window width. A live probe showed `window=994`, `frame=980`, and a contained toolbar `x=7 width=680`, which avoids the oversized dirty region.
- Native-surface mismatch fix: on the real Windows backend after switching transparent, `geometry=(980x520)` but `frameGeometry=(966x513)`. The correct fix is to compute safe margins `(7,0,7,7)` from the client/frame delta, keep the canvas exactly at the frame size, remove the transparent top-level background stylesheet, and avoid full-parent `update()` calls in transparent mode.
- Toolbar alignment fix: the hover toolbar buttons were top-aligned while the hint label was vertically centered. All toolbar controls should use `Qt.AlignVCenter` so the resize/move hint lines up with the buttons.
- User reverted the broader transparent-surface experiments. Current scope is toolbar-only: keep the transparent toolbar fully inside the same `14px/10px/14px` inset used by the normal window, instead of hugging the transparent edge, and center-align the toolbar buttons with the hint label.
- Follow-up toolbar tweak: keep the left inset at `14px` but increase the transparent-mode right inset to `34px` so the right-aligned controls sit about `20px` farther left.
- Narrow transparent-surface fix: remove the old `_normalize_transparent_native_surface()` growth behavior, which was turning a `980x520` transparent window into `994x527` while the native layered surface stayed smaller. Instead compute safe margins from `geometry()` vs `frameGeometry()` after the transparent switch and keep the canvas inside them.
- Current Windows probe after the fix: transparent `geometry=(980x520)`, `frameGeometry=(966x513)`, safe margins `(7,0,7,7)`, canvas `(7,0,966,513)`, toolbar `(14,10,932,40)`. This targets the `UpdateLayeredWindowIndirect ... dirty=(994x527 -7, 0)` mismatch directly.
- Verified the transparent fullscreen round-trip in a local probe after the narrow fix: entering fullscreen produced `geometry=(1920x1080)` with the expected frameless delta, and exiting returned to the original `980x520` window size. Added a regression for this path.
- After reverting to the original transparent path, the fullscreen-specific bug is still reproducible: transparent fullscreen exits back to a larger `1008x534` window because `_normalize_transparent_native_surface()` runs once more after `showNormal()`. Minimal fix is to suppress that single normalization pass when leaving fullscreen, without changing the rest of the transparent-mode behavior.
- Simpler fullscreen fix for the current original-path run: `_toggle_fullscreen()` and `Esc` should not call `_apply_window_chrome()` at all. `showFullScreen()` / `showNormal()` already preserve the correct geometry in both windowed and transparent modes; the extra chrome reapply is what breaks fullscreen. After the fix, only refresh toolbar text/overlay positions after the state change.
- Toolbar hide follow-up: in transparent mode the overlay can disappear logically but leave stale pixels behind. Fix the hide path by computing the overlay rectangle in canvas coordinates and explicitly `update()` + `repaint()` that exposed canvas region after hiding the toolbar.
- New direction after repeated `UpdateLayeredWindowIndirect` growth logs (`980x523 -> 994x530 -> 1008x537`): stop mutating an already-open lyric window between windowed and transparent modes. The main window should recreate `LyricDisplayWindow` in the target mode before showing it, because opening directly in transparent mode is already clean while the live in-place switch keeps accumulating the wrong native surface size.

## 2026-05-04

- Added phase-1 Companion Satellite support to pySSP.
- Main UI integration:
  - top-level `Companion` menu after `Tools`
  - `Open Virtual Satellite`
  - `Open Companion Satellite Options`
- Companion Satellite runtime must stay on its own worker thread so socket I/O, keepalive, and reconnect logic do not burden the UI thread.
- Companion Satellite options currently include:
  - host
  - port
  - enabled-at-startup checkbox
  - grid columns / rows
  - render mode
  - serial suffix
- Startup model was simplified from multiple behavior modes to one checkbox:
  - `companion_satellite_enabled = True` means start satellite automatically on pySSP startup
  - no separate connect-on-open/manual/open mode remains in the UI
- Default Companion Satellite layout is `8 columns x 4 rows`.
- Default serial suffix should be machine-specific from MAC address; effective serial remains `pyssp:<suffix>`.
- If serial suffix is blank or defaults are restored, fall back to the MAC-derived suffix.
- Companion Satellite options page includes a warning that duplicate serial numbers across clients can cause Companion-side issues.
- Main window has a bottom status-bar Companion indicator placed immediately after the RAM indicator.
- The bottom indicator always shows `SAT`; only the color changes by connection state. Tooltip carries detailed state text.
- Virtual Satellite window should be a separate top-level window, not embedded over the main pySSP window.
- Virtual Satellite window was intentionally simplified:
  - removed visible grid-size label
  - removed visible connection status text
  - removed start / stop / reconnect buttons
  - kept the surface itself plus an options shortcut
- Companion Satellite render modes:
  - `bitmap`: use Companion-provided bitmap and size each virtual key to the bitmap size
  - `styled`: pySSP renders its own button appearance
- In `styled` mode, each button should show its axis/coordinate label as `X<col> Y<row>`.
- `styled` is the clearer user-facing name for pySSP-rendered buttons; avoid vague labels like `custom`.

## 2026-05-16

- NDI backend was migrated from `ndi-python` / `NDIlib` to `cyndilib`.
- Relevant current files for NDI are:
  - `pyssp/ndi_support.py`
  - `pyssp/ndi_output.py`
  - `pyssp/ui/main_window/video_display.py`
  - `pyssp/ui/options_dialog/page_builders/video_display.py`
  - `pyssp/ui/main_window/ui_build.py`
  - `pyssp/ui/system_info_dialog.py`
  - tests: `tests/test_ndi_support.py`, `tests/test_ndi_output.py`, plus NDI-related assertions in `tests/test_options_dialog_ui.py` and `tests/test_main_window_import_compat.py`
- Existing user-facing NDI features that must be preserved during the backend swap:
  - independent NDI output pipeline
  - source name setting, default `pyssp-video`
  - route follows Video Control
  - resolution presets/custom size
  - fps selector
  - audio enable
  - audio tap mode `pre_fader` / `post_fader`
  - diagnostics in About, System Information, and Audio Engine Insight
- Important `cyndilib` note:
  - `Sender.write_audio()` / `write_video_and_audio()` expects audio shaped `(num_channels, num_samples)`, not `(num_samples, num_channels)`
  - `AudioSendFrame.reference_level` should likely be set to `AudioReference.dBFS_smpte` for pySSP because engine audio is normalized float audio; otherwise NDI audio level will be about 20 dB low
- Current backend behavior:
  - `pyssp/ndi_output.py` now uses `cyndilib.sender.Sender`, `VideoSendFrame`, and `AudioSendFrame`
  - sender audio path transposes engine audio to `(channels, samples)` and uses `AudioReference.dBFS_smpte`
  - capability detection treats either bundled `cyndilib` runtime binaries or external NDI runtime/SDK installs as valid
- Testing note:
  - real `cyndilib` loopback should run in a subprocess during tests; importing and exercising the native backend in the same pytest process as the Qt-heavy UI suites caused Windows access-violation instability
- Packaging direction to remember:
  - `requirements.txt` now uses `cyndilib>=0.1.1`
  - `pySSP.spec` / `pySSP_debug.spec` now collect `cyndilib`
  - keep runtime/SDK detection cross-platform, not Windows-only

## 2026-05-17

- The `cyndilib` sender path is no longer considered reliable enough for pySSP production NDI output:
  - direct loopback reproduced broken stereo behavior on this machine
  - audio cadence from app-side polling still produced skips/crackle even after multiple timer fixes
- New backend direction is to bind directly to the installed NDI runtime/SDK instead of relying on a Python wrapper sender path.
- Licensing constraint to preserve:
  - do not bundle the NDI SDK/runtime with pySSP
  - pySSP should detect and use a user-installed NDI runtime/SDK on Windows and macOS
- Cross-platform requirement is explicit:
  - runtime discovery and sender backend must work for both Windows and macOS
  - do not implement a Windows-only path and “fix mac later”
- Current redesign in progress:
  - new `pyssp/ndi_runtime.py` introduces direct `ctypes` bindings for the installed runtime
  - target audio send path is `NDIlib_util_send_send_audio_interleaved_32f`
  - target video send path is direct `NDIlib_send_send_video_async_v2`
- Audio architecture direction to preserve:
  - NDI audio should move away from main-window/player-proxy polling
  - prefer engine-callback-side monitor buffers or a true mix bus so NDI hears the same result as soundcard output, including fades, crossfades, and multi-play
- Current audio path after the recent pre/post-fader work:

```text
Per player:

source / stream / utility tone
  -> tempo / pitch block handling
  -> DSP block
  -> program gain (_volume)
     this now carries slot volume, fades, vocal-shadow routing, and talk-driven program changes
  -> declick fade-in
  -> PRE-FADER branch
     -> engine pre meter store
     -> player pre output tap buffer
     -> player pre output monitor buffer
  -> master gain (_master_volume)
     this is the soundcard master/output fader stage
  -> POST-FADER branch
     -> soundcard outdata
     -> engine post meter store
     -> player post output tap buffer
     -> player post output monitor buffer
     -> declick tail / recent output history

Consumers:

Main transport meter
  -> reads aggregated engine meter store
  -> mode selectable in General:
     pre_fader or post_fader (default)

NDI audio
  -> video_display timer
  -> choose monitor mode from ndi_output_audio_tap_mode
     pre_fader or post_fader
  -> pull per-player monitor frames by player_id
  -> accumulate pending per-player buffers
  -> mix buffered chunks in UI-side NDI sender path
  -> send to NDI runtime
  -> if no audio is available, send silent keepalive frames
  -> if a player stops but buffered audio remains, keep flushing that tail
```

- Important caveat on the current NDI design:
  - NDI is closer to soundcard behavior now, but it is still not a true shared mix bus
  - it mixes per-player monitor buffers later in `video_display.py`, so the remaining architectural gap is still “per-player monitor pull” vs “single engine mix bus”
