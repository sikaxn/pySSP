from pyssp import audio_engine


def test_mp3_leading_junk_fallback(monkeypatch, tmp_path):
    path = tmp_path / "broken.mp3"
    path.write_bytes((b"\x00" * 32) + b"\xFF\xFB\x90\x64" + b"\x00" * 64)

    calls = []

    class DummySound:
        def get_raw(self):
            return b"\x00\x00"

        def get_length(self):
            return 0.1

    def fake_sound(*args, **kwargs):
        calls.append((args, kwargs))
        if args and isinstance(args[0], str):
            raise Exception("Unrecognized audio format")
        stream = kwargs.get("file")
        assert stream is not None
        head = stream.read(2)
        assert head == b"\xFF\xFB"
        return DummySound()

    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "Sound", fake_sound)

    sound = audio_engine._load_sound_with_fallback(str(path))
    assert isinstance(sound, DummySound)
    assert len(calls) == 2
