import pytest
from fener.value_comparison import equal_prices


def price(amount, quantity=1000000, **extras):
    return {"amount": amount, "quantity": quantity, "currency": "USD", "unit": "tokens", **extras}


@pytest.mark.parametrize(
    "left,right,equal",
    [
        (price("0.2"), price("0.2000000"), True),
        (price("0.0000002", 1), price("0.2"), True),
        (price("0"), price("0.000"), True),
        (price("0.200000000000000001"), price("0.200000000000000002"), False),
        (price("0.2"), price("0.2", currency="EUR"), False),
        (price("0.2"), price("0.2", unit="images"), False),
        (price("NaN"), price("NaN"), False),
        (price("0.2", 0), price("0.2"), False),
    ],
)
def test_equivalent_rates_preserve_real_changes(left, right, equal):
    assert equal_prices(left, right) is equal
