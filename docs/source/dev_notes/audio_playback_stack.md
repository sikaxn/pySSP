# Audio Playback Stack (UI, Runtime, FFmpeg, Pedalboard)

This note documents how `pySSP` audio playback is layered today, and why a recent timecode reset regression appeared.

## Layering

### 1. UI layer (`pyssp/ui/main_window.py`)

- Handles button clicks, fade/crossfade mode, transport display, now-playing text, waveform widgets, and status banners.
- Calls `ExternalMediaPlayer` methods (`setMedia`, `play`, `pause`, `stop`, `setPosition`) and updates UI state.
- Tracks active button/play state via `_active_playing_keys` and `current_playing`.
- Uses `PlaybackRuntimeTracker` for monotonic playback-session ids so timecode policy can follow:
  - newest started player in normal mode
  - smallest active player id in multi-play mode

### 2. Playback engine (`pyssp/audio_engine.py`)

- `ExternalMediaPlayer` is the runtime audio core.
- Chooses source path in `setMedia`:
  - preloaded numpy frames (RAM cache) when available
  - FFmpeg streaming decoder (`FFmpegPCMStream`) when available
  - pygame decode fallback (`pygame.mixer.Sound`)
- Uses `sounddevice` output callback for final audio output.

### 3. FFmpeg support (`pyssp/ffmpeg_support.py`)

- Resolves bundled FFmpeg/FFprobe first (PyInstaller bundle), external fallback second.
- Supports duration probing, stream probing, and streaming PCM decode via subprocess pipe.
- Used for:
  - streaming playback path
  - format support expansion
  - validation fallback paths

### 4. DSP / plugin rack (`pyssp/dsp.py`)

- `RealTimeDSPProcessor` still owns built-in EQ/reverb behavior.
- Optional Pedalboard integration now provides a plugin rack path for VST-style processing when `pedalboard` is installed.
- This keeps the output driver path on `sounddevice` while reducing dependence on `pygame` for future DSP expansion.

### 5. pygame role

- Still used as decode fallback and for some frame extraction paths.
- RAM preload decode can be configured to use FFmpeg first (with pygame fallback), depending on setting.

### 6. Waveform/UI responsiveness

- Waveform generation runs async (`waveformPeaksAsync`), polled by timers in UI.
- Disk waveform cache avoids recomputing low-res visualization repeatedly.

## Timecode reset regression root cause

Observed issue:

- After playback ends, timecode did not jump back to `00:00:00:00`.
- With slot offset (example `01:00:00:00`) and ending near `01:00:30:00`, display could jump to `00:00:30:00`.

Why:

1. Engine end state keeps position at duration (non-zero).
2. Follow-timecode sampling path still reads player position after stop/end.
3. Slot offset is only applied while `current_playing` still resolves to a slot.
4. Once `current_playing` is cleared, follow path can keep absolute end position but lose slot offset context.

Result:

- End-of-track residual position (`~30s`) can be displayed without offset, producing `00:00:30:00`.

Mitigation implemented:

- In follow mode, if playback is no longer active, output timecode returns `0` directly.
- This guarantees end-of-playback reset to `00:00:00:00` regardless of offset.

## Target direction

- Keep the audio engine alive on its own thread at all times.
- Let the UI send commands to the engine instead of owning playback state.
- Create per-play audio player sessions rather than treating `player` / `player_b` as the long-term state model.
- Move timecode follow policy beside engine session tracking so UI display becomes a subscriber, not the source of truth.
