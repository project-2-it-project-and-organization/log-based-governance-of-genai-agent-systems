import pytest


def test_addition():
    assert 10 + 5 == 15


def test_addition2():
    assert 10 + 3 == 13


def test_subtraction():
    assert 10 - 5 == 5


def test_sum():
    assert (0.1 + 0.2) == pytest.approx(0.3)
