import pytest


@pytest.mark.regression
def test_tax_rounding_legacy():
    """Intentional failure used by the platform failure-handling test."""
    actual = 10.00
    expected = 10.01
    assert actual == expected
