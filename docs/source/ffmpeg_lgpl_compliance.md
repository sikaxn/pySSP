# FFmpeg LGPL Compliance Checklist (Release Process)

Use this checklist when distributing a `pySSP` build that includes FFmpeg binaries.

## 1) Build policy

- Build FFmpeg without `--enable-gpl` and without `--enable-nonfree`.
- Do not include GPL codecs/libraries (for example `libx264`) in distributed FFmpeg binaries.
- Keep FFmpeg executable/library names recognizable (do not obfuscate names).

## 2) Linking/distribution model

- Prefer dynamic linking if you distribute FFmpeg libraries (`.dll`, `.so`, `.dylib`).
- Current `pySSP` release build scripts collect FFmpeg from the `imageio-ffmpeg` package (`--collect-data "imageio_ffmpeg"`).
- The `pySSP` source repository does not include FFmpeg source code.
- Release artifacts may include unmodified FFmpeg binaries from `imageio-ffmpeg`.
- Current build scripts do not automatically reject GPL/nonfree FFmpeg binaries. Release maintainers must verify the bundled FFmpeg `-version` configuration before shipping.
- If you change or replace bundled FFmpeg binaries in downstream distribution, you are responsible for LGPL compliance artifacts below.

## 3) Source publication requirements

- Publish the exact FFmpeg source matching your shipped binaries.
- Include a `changes.diff` created from the FFmpeg source tree:
  - `git diff > changes.diff`
- Include FFmpeg build instructions/configure flags used for shipped binaries.
- Distribute FFmpeg source as `.tar.*` or `.zip`.
- Host FFmpeg source on the same site/server as your binary download.

## 4) User-facing notices

- Website download page text:
  - `This software uses code of <a href=http://ffmpeg.org>FFmpeg</a> licensed under the <a href=http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>LGPLv2.1</a> and its source can be downloaded <a href=link_to_your_sources>here</a>`
- About box text must include:
  - `This software uses libraries from the FFmpeg project under the LGPLv2.1`
- EULA/installer terms must include:
  - FFmpeg LGPLv2.1 notice
  - Statement that you do not own FFmpeg
  - No reverse-engineering prohibition that conflicts with LGPL rights
- Apply the same legal changes across all translated EULA variants.

## 5) Final verification before release

- Confirm no GPL FFmpeg components are present in shipped FFmpeg binaries.
- Confirm source archive link is live on the same host as your app download.
- Confirm About dialog and installer EULA include FFmpeg notices.
- Confirm spelling is exactly `FFmpeg`.
