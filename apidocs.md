# pySSP Web Remote API

Base URL: `http://<host-ip>:<port>`

The Web Remote service is controlled from **Options -> Web Remote**:
- Enable/disable Web Remote
- Set listening port
- View the LAN URL to open in browser

All responses are JSON.

- Success shape:
```json
{
  "ok": true,
  "result": {}
}
```
- Error shape:
```json
{
  "ok": false,
  "error": {
    "code": "error_code",
    "message": "Human readable error"
  }
}
```

## Core Control

- `GET /`
  - Browser UI with clickable groups, pages, and buttons plus transport controls.

- `GET/POST /api/health`
- `GET/POST /api/play/<button_id>`
  - Example: `/api/play/a-1-1`
- `GET/POST /api/pause`
  - Pauses active playback. Returns an error if nothing is playing.
- `GET/POST /api/resume`
  - Resumes paused playback. Returns an error if nothing is paused.
- `GET/POST /api/stop`
  - Same behavior as clicking `STOP` in the UI (fade rules apply).
- `GET/POST /api/forcestop`
  - Immediate stop without fade.
- `GET/POST /api/rapidfire`
- `GET/POST /api/playnext`
  - Returns error if not currently playing or no next track is available.

## Toggle/Mode Endpoints

Mode values: `enable`, `disable`, `toggle`

- `GET/POST /api/talk/<mode>`
- `GET/POST /api/playlist/<mode>`
- `GET/POST /api/playlist/shuffle/<mode>`
  - Returns error if playlist is not enabled.
- Alias routes:
  - `GET/POST /api/playlist/enableshuffle`
  - `GET/POST /api/playlist/disableshuffle`
- `GET/POST /api/multiplay/<mode>`
- `GET/POST /api/fadein/<mode>`
- `GET/POST /api/fadeout/<mode>`
- `GET/POST /api/crossfade/<mode>`

## Navigation/Reset

- `GET/POST /api/goto/<target>`
  - Accepted target formats:
    - `<group>` (example: `a`)
    - `<group>-<page>` (example: `a-1`)
    - `<group>-<page>-<button>` (example: `a-1-1`)
- `GET/POST /api/resetpage/current`
- `GET/POST /api/resetpage/all`

## Query Endpoints

- `GET /api/query`
  - Returns current high-level app state.
  - Includes `playing_tracks` array with active song title(s), button id(s), and remaining time (`remaining`, `remaining_ms`).
- `GET /api/query/button/<button_id>`
  - Example: `/api/query/button/a-1-1`
- `GET /api/query/pagegroup/<group>`
  - Example: `/api/query/pagegroup/a`
  - Each page entry includes `page_name` and `page_color`.
- `GET /api/query/page/<group>-<page>`
  - Example: `/api/query/page/a-1`
  - Includes page metadata (`page_name`, `page_color`) and `buttons` array with each button state (assigned/locked/marker/missing/played/is_playing/title).
  - Marker buttons include `marker_text` so the web remote can display place marker text.

## ID Format

- Button ID format: `<group>-<page>-<button>`
- Group: `A`..`J` (also `Q` for cue page)
- Page: `1..18` (`Q` supports only page `1`)
- Button: `1..48`

## Example Calls

```bash
curl http://192.168.1.10:5050/
curl http://192.168.1.10:5050/api/play/a-1-1
curl http://192.168.1.10:5050/api/talk/toggle
curl http://192.168.1.10:5050/api/resume
curl http://192.168.1.10:5050/api/playlist/enable
curl http://192.168.1.10:5050/api/playlist/shuffle/enable
curl http://192.168.1.10:5050/api/playnext
curl http://192.168.1.10:5050/api/query
```
