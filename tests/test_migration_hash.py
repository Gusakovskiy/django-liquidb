import pytest

from liquidb.models import _create_migration_hash


@pytest.mark.parametrize(
    'state_1, state_2,expected',
    [
        (
                [('first_app', '0001'), ('second_app', '0002')],
                [('second_app', '0002'), ('first_app', '0001')],
                True,
        ),
        (
                [],
                [],
                True,
        ),
        (
                [('first_app', '0001'), ('second_app', '0002')],
                [('first_app', '0001'), ('second_app', '0002')],
                True,
        ),
        (
                [('first_app', '0001'), ('second_app', '0002'), ('third_app', '0003')],
                [('first_app', '0001'), ('second_app', '0002')],
                False,
        ),
        (
                [('first_app', '0001'), ('second_app', '0002')],
                [('second_app', '0002')],
                False,
        ),
        (
                [('first_app', '0001'), ('second_app', '0002')],
                [],
                False,
        ),
        (
                [('second_app', '0002')],
                [('first_app', '0001')],
                False,
        ),
    ]
)
def test_hash_function(state_1, state_2, expected):
    s1 = _create_migration_hash(state_1)
    s2 = _create_migration_hash(state_2)
    result = s1 == s2
    assert result is expected


