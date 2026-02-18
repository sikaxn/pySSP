# companion-module-pyssp

Bitfocus Companion module for controlling `pySSP` using the pySSP Web Remote HTTP API.

## Features

- Configure IP address and port (HTTP only)
- Player Control action includes:
- Pause/resume/stop/force stop/play next/rapid fire
- Talk/playlist/shuffle/multi-play enable-disable-toggle
- Fade in/out/crossfade enable-disable-toggle
- Reset current/all pages
- Play audio with 3 fields:
- Group (`A` to `J`)
- Page (auto-populated from group)
- Audio (auto-populated from page)
- Navigation action uses API `goto` with group-specific page dropdowns
- Poll `/api/query` and expose state as Companion variables
- Dynamic presets generated from discovered Group/Page/Audio availability


The module manifest is at `companion/manifest.json` and the runtime entrypoint is `src/index.js`.
