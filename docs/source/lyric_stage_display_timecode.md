# Lyric, Stage Display, and Timecode

This page summarizes lyric workflow, stage display behavior, and how timecode works during playback.

## Lyric Workflow

When assigning audio to a sound button, pySSP can scan for matching lyric files.

![Scan Sound Button for Lyric](images/scan_sound_btn_lyric.png)

If a lyric file is found, pySSP shows the match/selection window.

![Lyric File Found Window](images/lyric_file_found_window.png)

You can edit lyric timing/text in the lyric editor, including rapid edit tools.

![Lyric Editor with Rapid Editor Expanded](images/lyric_editor_with_rapid_editor_expanded.png)

For runtime navigation, use Lyric Navigator to jump to lines/positions quickly.

![Lyric Navigator](images/lyric_navigator.png)

LRC, SRT, and automation script timestamps use positions in the original audio file. A cue-in changes where playback starts, but does not shift those timestamps. Seeking from a Lyric or Automation Script Navigator row outside the cue range follows the `When seeking outside cue area` Playback setting.

## Stage Display

Stage Display can show live playback context (for example: song name, lyric, elapsed/remaining, progress, and alerts).

![Stage Display](images/stage_display.png)

Alerts can be pushed to the Stage Display while the set is running.

![Send Alert](images/send_alert.png)

## How Timecode Works

Timecode behavior is controlled by `Audio Device / Timecode` settings and reflected in the Timecode panel.

![Timecode Panel](images/timecode_panel.png)

Core flow:

- Choose a `Timecode Mode`:
  - `All Zero`: output stays at zero.
  - `Follow Media/Audio Player`: output follows current playback position.
  - `System Time`: output follows wall-clock time.
  - `Pause Sync (Freeze While Playback Continues)`: freezes timecode while audio can continue.
- Choose `Timecode Display Timeline` reference:
  - `Relative to Cue Set Points`
  - `Relative to Actual Audio File`
- Optional per-button behavior:
  - `Enable soundbutton timecode offset` applies button-level offsets.
  - `Respect soundbutton timecode display timeline setting` lets a sound button override global timeline reference.
- Select output type/device:
  - `SMPTE Timecode (LTC)` output target plus frame/audio format.
  - `MIDI Timecode (MTC)` MIDI output and frame rate.

Stage Display time labels and timecode use their selected timeline references. Lyric and automation script matching continues to use the audio-file position.
