import pytest

@pytest.mark.unit
def test_basic():
    """A basic test to verify that our test setup works."""
    assert True

@pytest.mark.unit
def test_math():
    """A simple math test."""
    assert 1 + 1 == 2
    assert 2 * 2 == 4

@pytest.mark.unit
def test_string():
    """A simple string test."""
    assert "hello" + " world" == "hello world"
    assert "hello".upper() == "HELLO"

@pytest.mark.unit
def test_list():
    """A simple list test."""
    assert [1, 2, 3] + [4, 5] == [1, 2, 3, 4, 5]
    assert sorted([3, 1, 2]) == [1, 2, 3]

@pytest.mark.unit
def test_dict():
    """A simple dictionary test."""
    d = {"a": 1, "b": 2}
    assert d["a"] == 1
    assert "a" in d
    assert "c" not in d 