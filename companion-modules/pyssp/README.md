# companion-module-pyssp

Bitfocus Companion module for controlling `pySSP` using the pySSP Web Remote HTTP API.

## Features

- Configure IP address and port (HTTP only)
- Player Control action includes:
- Pause/resume/stop/force stop/play next/rapid fire
- Play selected, play selected/pause, mute
- Talk/playlist/shuffle/multi-play enable-disable-toggle
- Fade in/out/crossfade enable-disable-toggle
- Reset current/all pages
- Group/page/sound-button next/prev
- Lock, automation lock, unlock
- Play audio with 3 fields:
- Group (`A` to `J`, plus `Q` for cue)
- Page (auto-populated from group)
- Audio (auto-populated from page)
- Navigation action uses API `goto` with group-specific page dropdowns
- Volume set action (`/api/volume/<level>`)
- Seek action by percent or time string
- Stage alert send/clear actions
- Poll `/api/query` and expose state as Companion variables
- Query variables include cue/fade/lock/current-playing/web-remote state
- Dynamic presets generated from discovered Group/Page/Audio availability


The module manifest is at `companion/manifest.json` and the runtime entrypoint is `src/index.js`.
