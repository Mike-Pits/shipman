---
status: accepted
---

# RUB remains the reporting/aggregation currency (reverses ADR-0002)

[ADR-0002](0002-usd-as-reporting-currency.md) proposed switching the base/reporting currency from RUB to USD, reasoning that industry-standard commercial shipping reports (freight, hire, TCE) are conventionally USD-denominated. During SRS review, the operator corrected this directly: RUB is the reporting/aggregation currency for this business, with USD fully tracked as the secondary currency for display and for USD-denominated transactions — the reverse of what ADR-0002 assumed, and matching v1's original convention. ADR-0002 is superseded by this decision; USD-denominated figures (e.g. freight, TCE-in-USD-per-day as an industry-comparable figure) remain fully available via the currency toggle (SRS_v2 §7.1), just not as the storage/aggregation base.
