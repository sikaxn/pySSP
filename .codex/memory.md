# Codex Memory

## 2026-04-29

- Investigated lyric display transparent mode blackout.
- Root cause was in `pyssp/ui/lyric_display.py`: transparent mode still let the top-level window and full-window hover surface paint a background, which could visually black out the display.
- Fix keeps the transparent-mode window, canvas, lyric gadget, and hover surface on explicit transparent backgrounds and enables `WA_NoSystemBackground` on the transparent child widgets involved.
- Transparent lyric outline also came from the lyric gadget retaining a `QFrame.Box` shape; transparent mode now switches it to `QFrame.NoFrame` and restores the box frame in windowed mode.
- Added GUI regression coverage in `tests/test_lyric_display_window.py` for transparent-mode and normal-mode background state.
