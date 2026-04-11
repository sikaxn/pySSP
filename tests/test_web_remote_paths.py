import pytest

from pyssp.web_remote import _normalize_asset_relpath


def test_normalize_asset_relpath_accepts_nested_relative_path():
    assert _normalize_asset_relpath(r"css\app/main.css") == "css/app/main.css"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/etc/passwd",
        "../secret.txt",
        "a/../../secret.txt",
        r"..\..\secret.txt",
        "ok/\x00bad.txt",
    ],
)
def test_normalize_asset_relpath_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        _normalize_asset_relpath(value)

