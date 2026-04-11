from __future__ import annotations

import glob
import os
import sys
import tempfile
import wave
import aifc
from ctypes.util import find_library
from typing import Dict, Iterable, List, Sequence, Tuple


def _dedupe(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in values:
        token = str(item or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _asset_root() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
        bundled = os.path.join(base_dir, "pyssp", "assets")
        if os.path.isdir(bundled):
            return bundled
        meipass_dir = str(getattr(sys, "_MEIPASS", "") or "").strip()
        if meipass_dir:
            candidate = os.path.join(meipass_dir, "pyssp", "assets")
            if os.path.isdir(candidate):
                return candidate
        return bundled
    return os.path.join(os.path.dirname(__file__), "assets")


def _iter_existing_dirs(paths: Sequence[str]) -> Iterable[str]:
    for path in paths:
        token = str(path or "").strip()
        if token and os.path.isdir(token):
            yield token


def _iter_search_roots(pygame_module) -> Iterable[str]:
    roots: List[str] = []
    pygame_base = os.path.dirname(getattr(pygame_module, "__file__", "") or "")
    if pygame_base:
        roots.append(pygame_base)
        roots.extend(_iter_existing_dirs([
            os.path.join(pygame_base, "SDL2.framework"),
            os.path.join(pygame_base, "SDL2_mixer.framework"),
        ]))

    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if exe_dir:
        roots.append(exe_dir)
        current = exe_dir
        seen_parents: set[str] = set()
        for _ in range(5):
            parent = os.path.dirname(current)
            if not parent or parent == current or parent in seen_parents:
                break
            seen_parents.add(parent)
            roots.append(parent)
            roots.extend(_iter_existing_dirs([
                os.path.join(parent, "Frameworks"),
                os.path.join(parent, "Contents"),
                os.path.join(parent, "Contents", "MacOS"),
                os.path.join(parent, "Contents", "Frameworks"),
                os.path.join(parent, "Contents", "Resources"),
            ]))
            current = parent

    meipass_dir = getattr(sys, "_MEIPASS", "")
    if meipass_dir:
        meipass_dir = str(meipass_dir)
        roots.append(meipass_dir)
        roots.extend(_iter_existing_dirs([
            os.path.join(meipass_dir, "Frameworks"),
            os.path.join(meipass_dir, "Contents"),
            os.path.join(meipass_dir, "Contents", "MacOS"),
            os.path.join(meipass_dir, "Contents", "Frameworks"),
            os.path.join(meipass_dir, "Contents", "Resources"),
        ]))

    # Add a shallow scan of likely child directories because PyInstaller and
    # macOS app bundles often nest SDL dylibs one level below the obvious root.
    expanded: List[str] = []
    for root in _dedupe(roots):
        expanded.append(root)
        try:
            child_names = os.listdir(root)
        except Exception:
            continue
        for child_name in child_names:
            child_path = os.path.join(root, child_name)
            if not os.path.isdir(child_path):
                continue
            lowered = child_name.lower()
            if (
                "framework" in lowered
                or lowered in {"pygame", "pygame_ce", "lib", "libs", "dlls", "resources", "macos"}
                or child_name.startswith("SDL")
            ):
                expanded.append(child_path)

    return _dedupe(expanded)


def _resolve_sdl_mixer_library_path(pygame_module) -> Tuple[str, List[str]]:
    roots = list(_iter_search_roots(pygame_module))
    explicit_names = [
        "SDL2_mixer.dll",
        "libSDL2_mixer-2.0.0.dylib",
        "libSDL2_mixer-2.6.0.dylib",
        "libSDL2_mixer-2.8.0.dylib",
        "libSDL2_mixer.dylib",
        "SDL2_mixer.framework/SDL2_mixer",
        "libSDL2_mixer.so",
    ]
    for root in roots:
        for name in explicit_names:
            candidate = os.path.join(root, name)
            if os.path.exists(candidate):
                return candidate, roots
        for pattern in [
            "*SDL2_mixer*.dll",
            "*SDL2_mixer*.dylib",
            "*SDL2_mixer*.so",
            "*SDL2_mixer*.so.*",
        ]:
            matches = glob.glob(os.path.join(root, pattern))
            if matches:
                return matches[0], roots
    return "", roots


def _load_sdl_mixer_ctypes(pygame_module):
    import ctypes

    resolved_path, search_roots = _resolve_sdl_mixer_library_path(pygame_module)
    attempts: List[str] = []

    def _try_load(name: str):
        token = str(name or "").strip()
        if not token:
            return None
        attempts.append(token)
        try:
            lib = ctypes.CDLL(token)
        except Exception:
            return None
        if hasattr(lib, "Mix_GetNumChunkDecoders") and hasattr(lib, "Mix_GetChunkDecoder"):
            return lib
        return None

    if resolved_path:
        lib = _try_load(resolved_path)
        if lib is not None:
            return lib, resolved_path, search_roots, attempts

    for candidate in [
        find_library("SDL2_mixer"),
        find_library("SDL2_mixer-2.0"),
        find_library("SDL2_mixer-2.6"),
        find_library("SDL2_mixer-2.8"),
        "SDL2_mixer",
        "libSDL2_mixer.dylib",
        "libSDL2_mixer-2.0.0.dylib",
        "libSDL2_mixer-2.6.0.dylib",
        "libSDL2_mixer-2.8.0.dylib",
    ]:
        lib = _try_load(candidate or "")
        if lib is not None:
            return lib, str(candidate), search_roots, attempts

    attempts.append("<process-global>")
    try:
        process_lib = ctypes.CDLL(None)
    except Exception:
        process_lib = None
    if process_lib is not None:
        if hasattr(process_lib, "Mix_GetNumChunkDecoders") and hasattr(process_lib, "Mix_GetChunkDecoder"):
            return process_lib, "<process-global>", search_roots, attempts

    return None, resolved_path, search_roots, attempts


def _write_pcm_wav(path: str) -> None:
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(11025)
        handle.writeframes(b"\x00\x00" * 256)


def _write_pcm_aiff(path: str) -> None:
    with aifc.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(11025)
        handle.writeframes(b"\x00\x00" * 256)


def _functional_sample_paths() -> Dict[str, str]:
    samples: Dict[str, str] = {}
    sample_root = os.path.join(_asset_root(), "system_info_probe")
    for fmt in ["wav", "mp3", "ogg", "flac"]:
        candidate = os.path.join(sample_root, f"sample.{fmt}")
        if os.path.exists(candidate):
            samples[fmt.upper()] = candidate
    return samples


def _probe_functional_support(pygame_module) -> Tuple[Dict[str, bool], Dict[str, str]]:
    support: Dict[str, bool] = {}
    details: Dict[str, str] = {}

    for fmt_name, sample_path in _functional_sample_paths().items():
        try:
            sound = pygame_module.mixer.Sound(sample_path)
            support[fmt_name] = True
            details[fmt_name] = f"loaded {os.path.basename(sample_path)} ({int(len(sound.get_raw()))} bytes raw)"
        except Exception as exc:
            support[fmt_name] = False
            details[fmt_name] = str(exc)

    with tempfile.TemporaryDirectory(prefix="pyssp_format_probe_") as temp_dir:
        wav_path = os.path.join(temp_dir, "probe.wav")
        aiff_path = os.path.join(temp_dir, "probe.aiff")
        _write_pcm_wav(wav_path)
        _write_pcm_aiff(aiff_path)
        for fmt_name, sample_path in [("WAV", wav_path), ("AIFF", aiff_path)]:
            try:
                sound = pygame_module.mixer.Sound(sample_path)
                support[fmt_name] = True
                details[fmt_name] = f"generated sample loaded ({int(len(sound.get_raw()))} bytes raw)"
            except Exception as exc:
                support[fmt_name] = False
                details[fmt_name] = str(exc)

    return support, details


def build_decoder_report() -> List[str]:
    lines: List[str] = []
    original_audio_driver = os.environ.get("SDL_AUDIODRIVER")
    original_video_driver = os.environ.get("SDL_VIDEODRIVER")
    try:
        import ctypes
        import pygame

        os.environ["SDL_AUDIODRIVER"] = "dummy"
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

        lines.append(f"pygame version: {getattr(pygame.version, 'ver', 'unknown')}")
        try:
            lines.append(f"SDL version: {pygame.get_sdl_version()}")
        except Exception as exc:
            lines.append(f"SDL version: unavailable ({exc})")

        mixer_initialized = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            mixer_initialized = True
        except Exception as exc:
            lines.append(f"pygame mixer initialized: False ({exc})")
        else:
            lines.append("pygame mixer initialized: True")

        functional_support, functional_details = _probe_functional_support(pygame)
        supported_formats = [name for name in ["WAV", "AIFF", "MP3", "OGG", "FLAC"] if functional_support.get(name)]
        unsupported_formats = [name for name in ["WAV", "AIFF", "MP3", "OGG", "FLAC"] if functional_support.get(name) is False]
        lines.append("pySSP functional playback support (tested): " + (", ".join(supported_formats) if supported_formats else "none"))
        if unsupported_formats:
            lines.append("pySSP functional playback not supported (tested): " + ", ".join(unsupported_formats))
        for fmt_name in ["WAV", "AIFF", "MP3", "OGG", "FLAC"]:
            detail = functional_details.get(fmt_name)
            if detail:
                lines.append(f"Functional probe [{fmt_name}]: {detail}")

        try:
            lines.append(f"SDL_mixer version: {pygame.mixer.get_sdl_mixer_version()}")
        except Exception as exc:
            lines.append(f"SDL_mixer version: unavailable ({exc})")

        lib, mixer_lib, search_roots, load_attempts = _load_sdl_mixer_ctypes(pygame)
        lines.append(f"SDL_mixer shared library path: {mixer_lib or 'not found'}")
        lines.append("SDL_mixer search roots: " + (" | ".join(search_roots) if search_roots else "none"))
        lines.append("SDL_mixer load attempts: " + (" | ".join(_dedupe(load_attempts)) if load_attempts else "none"))
        if lib is None:
            return lines

        lib.Mix_GetNumChunkDecoders.restype = ctypes.c_int
        lib.Mix_GetChunkDecoder.argtypes = [ctypes.c_int]
        lib.Mix_GetChunkDecoder.restype = ctypes.c_char_p

        chunk_decoders: List[str] = []
        chunk_count = int(lib.Mix_GetNumChunkDecoders())
        lines.append(f"Chunk decoders count: {chunk_count}")
        for idx in range(max(0, chunk_count)):
            raw = lib.Mix_GetChunkDecoder(idx)
            if not raw:
                continue
            decoder_name = raw.decode("utf-8", errors="replace")
            chunk_decoders.append(decoder_name)
            lines.append(f"Chunk decoder [{idx}]: {decoder_name}")

        music_decoders: List[str] = []
        if hasattr(lib, "Mix_GetNumMusicDecoders") and hasattr(lib, "Mix_GetMusicDecoder"):
            lib.Mix_GetNumMusicDecoders.restype = ctypes.c_int
            lib.Mix_GetMusicDecoder.argtypes = [ctypes.c_int]
            lib.Mix_GetMusicDecoder.restype = ctypes.c_char_p
            music_count = int(lib.Mix_GetNumMusicDecoders())
            lines.append(f"Music decoders count: {music_count}")
            for idx in range(max(0, music_count)):
                raw = lib.Mix_GetMusicDecoder(idx)
                if not raw:
                    continue
                decoder_name = raw.decode("utf-8", errors="replace")
                music_decoders.append(decoder_name)
                lines.append(f"Music decoder [{idx}]: {decoder_name}")

        lines.append("pygame-ce supported format (chunk): " + (", ".join(_dedupe(chunk_decoders)) or "none"))
        lines.append("pygame-ce supported format (music): " + (", ".join(_dedupe(music_decoders)) or "none"))
        base = os.path.dirname(getattr(pygame, "__file__", "") or "")
        codec_bins = []
        for token in ["ogg", "vorbis", "opus", "flac", "mp3", "wavpack", "xmp", "modplug", "mikmod"]:
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.dll")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.dylib")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.so")))
            codec_bins.extend(glob.glob(os.path.join(base, f"*{token}*.so.*")))
        codec_bins = _dedupe([os.path.basename(path) for path in codec_bins])
        lines.append("Detected codec shared libraries: " + (", ".join(codec_bins) if codec_bins else "none"))
        if not mixer_initialized:
            lines.append("Warning: decoder enumeration completed without an initialized mixer backend.")
    except Exception as exc:
        lines.append(f"pygame-ce supported format: unavailable ({exc})")
    finally:
        try:
            import pygame

            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass
        if original_audio_driver is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = original_audio_driver
        if original_video_driver is None:
            os.environ.pop("SDL_VIDEODRIVER", None)
        else:
            os.environ["SDL_VIDEODRIVER"] = original_video_driver
    return lines


def run_decoder_probe_process() -> List[str]:
    return build_decoder_report()


def main(argv: List[str] | None = None) -> int:
    _ = argv
    for line in build_decoder_report():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(list(sys.argv)))
