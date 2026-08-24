---
status: superseded by ADR-0003
---

# USD, not RUB, is the base/reporting currency

v1 stored every monetary value in RUB, converting USD amounts to RUB at entry. For v2, that's reversed: every payment stores its original currency and amount, plus a USD-equivalent computed from the historical exchange rate on that transaction's date; USD is the currency reports and TCE aggregate in, with RUB retained as a fully-tracked secondary currency for display and for RUB-denominated transactions (still common for Baltic/Russian port costs). This follows industry convention — freight, hire, and TCE are conventionally USD-denominated in commercial shipping — and v1's RUB-based convention was itself an artifact of the old general-cargo/bulk setup rather than a deliberate commercial-reporting choice. Reversing the base currency after data exists would require a data migration, so it's recorded here rather than left as a silent difference from v1.
