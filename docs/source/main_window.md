# Main Window

The main window is the primary workspace for loading a set and triggering sounds.

![Main Window](images/main_ui.png)

## Main Areas

- Menu bar: `File`, `Setup`, `Display`, `Timecode`, `Tools`, `Logs`, `Help`.
- Group buttons: `A` to `J`.
- Page list/controls: page selection for the active group.
- Sound grid: 48 sound buttons per page.
- Transport and mode controls: playback and behavior buttons.
- Fade and level controls: fade modes, volume, and seek.

## Control Buttons (What Each One Does)

| Button | What it does |
| --- | --- |
| `Cue` | Toggles Cue mode (switches to Cue page behavior). |
| `Multi-Play` | Allows multiple sounds to play at the same time. |
| `DSP` | Opens the DSP window for processing settings. |
| `Go To Playing` | Jumps view to the page/group containing the currently playing sound. |
| `Loop` | Toggles looping behavior for playback/playlist context. |
| `Next` | Plays the next item (enabled when next item is available). |
| `Button Drag` | Enables drag/reorder mode for sound buttons; normal playback is blocked while active. |
| `Pause` | Pauses active playback; resumes when pressed again. |
| `Rapid Fire` | Quickly retriggers playback from the selected/current sound button. |
| `Shuffle` | Toggles shuffle mode (used with playlist flow). |
| `Reset Page` | Resets current page play-state markers/toggles to default state. |
| `STOP` | Stops playback. If stop fade is active, pressing again forces immediate stop. |
| `Talk` | Toggles talk mode behavior (for live mic/talk workflow). |
| `Play List` | Enables/disables playlist mode for page progression. |
| `Search` | Opens search/find window. |

## Fade Buttons

| Button | What it does |
| --- | --- |
| `Fade In` | Fades in when starting playback. |
| `X` | Enables crossfade behavior (fade out + fade in transition). |
| `Fade Out` | Fades out on stop/switch operations. |

## Navigation Buttons

- Group buttons `A`-`J`: switch the active group.
- Page controls/list: switch the active page in that group.
- Sound buttons: click to trigger assigned audio for that slot.

Detailed page and sound button behavior is documented in **Group, Page, and Sound Button**.

## Menus

### File Menu

![File Menu](images/file_menu.png)

Core actions:
- New/Open/Save set files.
- Backup and restore settings/hotkey/midi mappings.
- Exit.

### Tools Menu

![Tools Menu](images/tools_menu.png)

Common tools:
- Duplicate and verification checks.
- Display file/library paths.
- Export/listing utilities.
