from app.models.fixture import Fixture


def apply_vat_terms(
    base_amount: float, vat_applicable: bool, vat_treatment: str | None, vat_rate_percent: float | None
) -> float:
    """Adds VAT on top of `base_amount` when the given terms call for it.

    When VAT is not applicable, or is already included in the rate ("inclusive"),
    the rate itself is the final amount and no adjustment is needed. Only
    "exclusive" terms — VAT added on top of the stated rate — change the amount.
    """
    if not vat_applicable or vat_treatment != "exclusive":
        return base_amount
    return round(base_amount * (1 + vat_rate_percent / 100), 2)


def apply_vat(base_amount: float, fixture: Fixture) -> float:
    """Same as `apply_vat_terms`, reading the terms off a Fixture."""
    return apply_vat_terms(base_amount, fixture.vat_applicable, fixture.vat_treatment, fixture.vat_rate_percent)
