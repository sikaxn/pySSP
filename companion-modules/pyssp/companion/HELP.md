# pySSP

This module controls pySSP over the pySSP Web Remote HTTP API.

pySSP is an open source alternative to Sports Sounds Pro for show playback and arena production on Windows and macOS Apple silicon. Note this module does not support the origional Sports Sounds Pro. You can download pySSP at https://pyssp.studenttechsupport.com/

Configuration:

- Host/IP (`host`)
- Port (`port`)
- Poll interval

Actions:

- Internal - Refresh Presets/Lists:
  - Re-queries pySSP pages/buttons and rebuilds dynamic audio/navigation presets
- Player Control:
  - Pause, Resume, Stop, Force Stop, Play Next, Rapid Fire
  - Play Selected, Play Selected / Pause, Mute
  - Talk enable/disable/toggle
  - Playlist enable/disable/toggle
  - Shuffle enable/disable/toggle
  - Multi-play enable/disable/toggle
  - Fade In/Out enable/disable/toggle
  - Crossfade enable/disable/toggle
  - Reset current/all pages
  - Group/page/sound-button next/prev
  - Lock, Automation Lock, Unlock
- Navigation - Go To Page (`/api/goto/<group>-<page>`)
- Play Audio with 3 fields:
  - Group (`A` to `J`, plus `Q` for cue)
  - Page (auto-populated from selected group)
  - Audio (auto-populated from selected page)
- Volume - Set Master Level
- Seek Transport by percent or time string
- Stage Alert - Send
- Stage Alert - Clear

Presets:

- Pause
- Resume
- Stop
- Play Next
- Dynamic audio presets generated from discovered Group/Page/Audio availability

Variables:

- `current_group`
- `current_page`
- `cue_mode`
- `is_playing`
- `talk_active`
- `playlist_enabled`
- `shuffle_enabled`
- `multi_play_enabled`
- `fade_in_enabled`
- `fade_out_enabled`
- `crossfade_enabled`
- `screen_locked`
- `automation_locked`
- `playing_count`
- `playing_buttons`
- `playing_button_ids`
- `current_playing`
- `playing_titles`
- `web_remote_url`
- `base_url`
- `last_error`
