import pytest

from bible_api.db import parse_ref

@pytest.mark.parametrize(
    "ref",
    [
        "osis:Matt.5.8",
        "osis:Matt.5.1-Matt.5.16",
        "osis:Matt.9.35-Matt.10.15",
        "osis:Ps.121-Ps.123",
        "John 3:16",
    ],
)
def test_parse_ref_returns_dict(ref):
    parsed = parse_ref(ref)
    assert isinstance(parsed, dict)
    assert parsed.get("book") is not None
    assert parsed.get("c_start") is not None
    assert parsed.get("v_start") is not None
    assert parsed.get("c_end") is not None
    assert parsed.get("v_end") is not None
