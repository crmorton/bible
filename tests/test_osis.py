import pytest
from bible_api.db import parse_ref

@pytest.mark.parametrize(
    "input_ref,expected",
    [
        ("osis:Matt.5.8", {"book": "Matt", "c_start": 5, "v_start": 8, "c_end": 5, "v_end": 8}),
        ("osis:Matt.5.1-Matt.5.16", {"book": "Matt", "c_start": 5, "v_start": 1, "c_end": 5, "v_end": 16}),
        ("osis:Matt.9.35-Matt.10.15", {"book": "Matt", "c_start": 9, "v_start": 35, "c_end": 10, "v_end": 15}),
        ("osis:Ps.121-Ps.123", {"book": "Ps", "c_start": 121, "v_start": 1, "c_end": 123, "v_end": 999}),
        ("John 3:16", {"book": "John", "c_start": 3, "v_start": 16, "c_end": 3, "v_end": 16}),
    ],
)
def test_osis_parsing(input_ref, expected):
    """Verify OSIS and standard reference parsing via parse_ref."""
    result = parse_ref(input_ref)
    assert result == expected
