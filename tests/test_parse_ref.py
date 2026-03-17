import pytest

from bible_api.db import parse_ref


@pytest.mark.parametrize(
    "input_ref,expected",
    [
        ("John 3:16", {"book": "John", "c_start": 3, "v_start": 16, "c_end": 3, "v_end": 16}),
        ("osis:John.3.16", {"book": "John", "c_start": 3, "v_start": 16, "c_end": 3, "v_end": 16}),
        ("osis:Psalm.23", {"book": "Psalm", "c_start": 23, "v_start": 1, "c_end": 23, "v_end": 999}),
    ],
)
def test_parse_ref_basic(input_ref, expected):
    result = parse_ref(input_ref)
    assert result == expected


def test_parse_ref_invalid():
    assert parse_ref("NotAReference") is None
