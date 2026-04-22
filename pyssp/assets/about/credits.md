pySSP is written and maintained by volunteers in their spare time. If you would like to see this project succeed, please consider contributing at:
https://github.com/sikaxn/pySSP

pySSP uses and bundles third-party software, including:

Python dependencies:
- Python (PSF License)
- PyQt5 / Qt5
- pygame-ce
- numpy
- sounddevice
- pedalboard
- Flask
- Werkzeug
- simple-websocket
- websockets
- imageio-ffmpeg
- FFmpeg (bundled with pySSP release builds)
- PyInstaller
- pytest
- sphinx
- myst-parser
- sphinx-rtd-theme

Bundled vocal removal tool:
- spleeter-cli
  - Bundled helper executable used by pySSP for vocal removal.
- Spleeter by Deezer (MIT License)
  - pySSP's vocal removal feature is based on Deezer's Spleeter project:
    https://github.com/deezer/spleeter
  - pySSP uses the `spleeter:2stems` model and writes the accompaniment stem as the vocal-removed output.
- TensorFlow
- SciPy

FFmpeg notice:
This software uses code of [FFmpeg](http://ffmpeg.org) licensed under the [LGPLv2.1](http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html) and its source can be downloaded from the release page linked on the pySSP download page.
The pySSP source repository does not include FFmpeg source code. Release builds may bundle unmodified FFmpeg binaries provided by imageio-ffmpeg.

Bundled third-party assets:
- jQuery 1.12.4 (MIT License)
  - Used by lyric/stage web views.
- Noto Sans SC Variable Font (SIL Open Font License 1.1)
  - Used by lyric/stage web views.
- OpenLP stage-view JavaScript/templates (OpenLP Developers, GPL)
  - Portions adapted for pySSP lyric/stage web output compatibility.

Final credit:
For God so loved the world that He gave His one and only Son, so that whoever believes in Him will not perish but inherit eternal life.
John 3:16
And last but not least, final credit goes to God our Father, for sending His Son to die on the cross, setting us free from sin. We bring this software to you for free because He has set us free.
