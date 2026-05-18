# Media Runtime Rewrite

This note tracks the first compatibility-first landing of the media backend rewrite.

## What Changed

- New runtime package: `pyssp.engine`
- New owner object: `pyssp.engine.runtime.MediaRuntime`
- New FFmpeg subsystem wrapper: `pyssp.engine.ffmpeg.FFmpegEngineServices`
- New internal contracts:
  - `TransportSnapshot`
  - `EngineDiagnosticsSnapshot`
  - `MediaProbeResult`
  - `FFmpegDecodeRequest`
  - `RuntimeCommand`
  - `RuntimeEvent`
  - `DestinationSceneConfig`

## Current Cutover

- `AudioService` no longer owns player lifecycle directly.
- `MediaRuntime` now owns:
  - playback session registry
  - transport reference selection
  - runtime session snapshots
  - FFmpeg service access
  - runtime diagnostics
- `ExternalMediaPlayer` is still the v1 execution node behind the runtime.
- `AudioPlayerProxy` remains the UI-facing compatibility layer.
- `MainWindow` has started consuming engine-owned state for:
  - timecode reference-session lookup
  - audio-engine insight runtime metadata
  - system-information runtime diagnostics export

## Why This Shape

This keeps the existing app behavior intact while establishing the new engine boundary in a live code path.

The key rule for the rewrite is now explicit:

- the UI controls playback
- the runtime owns playback state

## Remaining Work

- move more transport/timecode policy from `MainWindow` to `MediaRuntime`
- move NDI ownership fully behind runtime-controlled destination services
- add destination-scene composition and transition control
- consolidate player-specific meter/tap behavior into true engine buses
- redesign settings and display/video menu layout around runtime concepts
