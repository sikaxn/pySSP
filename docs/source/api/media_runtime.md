# Media Runtime API

`pyssp.engine` is the first explicit home for the rewritten backend architecture.

## Current Runtime Entry Points

- `pyssp.engine.runtime.MediaRuntime`
- `pyssp.engine.ffmpeg.FFmpegEngineServices`
- `pyssp.engine.types.TransportSnapshot`
- `pyssp.engine.types.EngineDiagnosticsSnapshot`
- `pyssp.engine.types.MediaProbeResult`

## Current Role

- Own playback session lifecycle above legacy player objects
- Own runtime transport snapshots and diagnostics
- Expose FFmpeg as a first-class engine subsystem
- Provide the compatibility seam used by `pyssp.audio_service`

## Current Limitation

This is a v1 foundation step, not the full end-state graph engine yet.

- audio rendering still executes inside `ExternalMediaPlayer`
- UI workflows are still being migrated
- video destinations are modeled conceptually but not fully moved into runtime services yet
