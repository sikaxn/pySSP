# pySSP

This module controls pySSP over the pySSP Web Remote HTTP API.

Configuration:

- Host/IP (`host`)
- Port (`port`)
- Poll interval

Actions:

- Internal - Refresh Presets/Lists:
  - Re-queries pySSP pages/buttons and rebuilds dynamic audio/navigation presets
- Player Control:
  - Pause, Resume, Stop, Force Stop, Play Next, Rapid Fire
  - Talk enable/disable/toggle
  - Playlist enable/disable/toggle
  - Shuffle enable/disable/toggle
  - Multi-play enable/disable/toggle
  - Fade In/Out enable/disable/toggle
  - Crossfade enable/disable/toggle
  - Reset current/all pages
- Navigation - Go To Page (`/api/goto/<group>-<page>`)
- Play Audio with 3 fields:
  - Group (`A` to `J`)
  - Page (auto-populated from selected group)
  - Audio (auto-populated from selected page)

Presets:

- Pause
- Resume
- Stop
- Play Next
- Dynamic audio presets generated from discovered Group/Page/Audio availability

Variables:

- `current_group`
- `current_page`
- `is_playing`
- `talk_active`
- `playlist_enabled`
- `shuffle_enabled`
- `multi_play_enabled`
- `playing_count`
- `playing_button_ids`
- `playing_titles`
- `base_url`
- `last_error`
