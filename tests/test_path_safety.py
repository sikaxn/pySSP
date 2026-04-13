from pyssp.path_safety import is_safe_file_path, unsafe_path_reason


def test_safe_windows_path_is_allowed():
    path = r"C:\Audio\crowd_01.wav"
    assert unsafe_path_reason(path) is None
    assert is_safe_file_path(path) is True


def test_shell_injection_delimiter_is_rejected():
    path = "test.wav; rm -rf /"
    reason = unsafe_path_reason(path)
    assert reason is not None
    assert "disallowed character ';'" in reason
    assert is_safe_file_path(path) is False


def test_newline_path_is_rejected():
    reason = unsafe_path_reason("song.wav\nnext.wav")
    assert reason == "Path contains a newline character."


def test_null_byte_path_is_rejected():
    reason = unsafe_path_reason("song.wav\x00")
    assert reason == "Path contains a null byte."

