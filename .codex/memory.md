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
