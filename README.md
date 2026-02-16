# pySSP

PyQt5 recreation of the Sports Sounds Pro interface and core page/button workflow.

This is an experiment. At this moment it is not good for production use.

![](images/main%20window.png)

## Run

```bash
pip install -r requirements.txt
python main.py
```

Note: playback uses `pygame.mixer`.

## Current features

- 10 groups (`A` through `J`)
- 18 pages per group
- 48 sound buttons per page (6x8)
- Load Sports Sounds Pro `.set` files from `File > Open Set...`
- Persistent app settings in `%APPDATA%\pySSP\settings.ini` (auto-created)
- Menu layout and top control panel shell
- Right-click sound button actions:
  - Add/Replace sound
  - Remove sound
  - Highlight toggle
  - Lock toggle
  - Place marker toggle
  - Copy-to-cue toggle
  - Verify sound file
- Button color states:
  - Teal: empty
  - Gray: assigned
  - Light blue: highlighted
  - Lime: currently playing
  - Red: played
  - Purple: missing file
  - Yellow: locked
  - Black: place marker
  - Blue: copied to cue
- Basic playback with elapsed/remaining/total timers
