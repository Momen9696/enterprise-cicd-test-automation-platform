import pytest


@pytest.mark.smoke
def test_cart_subtotal():
    assert round(19.99 + 5.01, 2) == 25.00


@pytest.mark.smoke
def test_sku_reserved():
    sku = "HK-204"
    assert sku.startswith("HK-")


@pytest.mark.regression
def test_discount_code():
    assert round(100 * 0.9, 2) == 90.0


@pytest.mark.regression
def test_free_shipping_threshold():
    assert 75 >= 50
