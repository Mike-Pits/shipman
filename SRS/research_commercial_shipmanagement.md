# Research: Commercial Ship Management Software

Compiled to inform the ground-up rewrite of the shipman project. Covers domain terminology, how established vendors structure commercial ship management software, and framework tradeoffs for an OS-agnostic rewrite. Scope is deliberately limited to **commercial** management (chartering, voyage economics, accounts) — technical management (crewing, PMS, drydocking) is out of scope, matching the old project and the stated direction for the new one.

---

## 1. Domain Glossary

**Fixture** — A concluded charter agreement (the vessel is "fixed") for a cargo or period. The unit of commercial commitment that everything downstream (voyage, accounts, P&L) hangs off of.

**Voyage Charter** — Charter of a vessel for a single voyage between load and discharge ports, freight paid per tonne of cargo (or lump sum). The owner bears voyage costs (bunkers, port charges); the charterer pays freight. This is the primary business model of the old shipman project (Arctic voyage trade).

**Time Charter (TC)** — Charter of a vessel for a period of time (months/years); the charterer pays daily/monthly hire and bears voyage costs (bunkers, port charges); the owner bears running costs (crew, insurance, maintenance). "Time Charter In" = you hire a vessel; "Time Charter Out" = you let your vessel to someone else.

**COA (Contract of Affreightment)** — A contract to carry a series of cargoes over a period, not tied to specific vessels — the carrier can nominate which ship performs each lift. [Veson: IMOS Chartering supports COAs, Cargoes, Voyage Fixtures, and Time Charters as first-class fixture types.](https://veson.com/products/imos/chartering/)

**Voyage Estimate** — A pre-fixture financial projection of a candidate voyage: expected freight/hire revenue minus projected bunker consumption, port costs, canal dues, and days at the given rates, producing projected P&L/TCE — used to decide whether to accept a fixture. [Voyage estimation is the entry point of IMOS Chartering, evaluated "side-by-side" before committing to a fixture.](https://veson.com/products/imos/chartering/)

**Post-fixture / Operations** — Once fixed, this covers day-to-day voyage execution: port calls, laytime tracking, bunker monitoring, instructions to the vessel, and reconciling actuals against the estimate. [Veson's Operations module: "dynamic P&L, centralized voyage instructions, and integrated tasks and alerts."](https://veson.com/operations-module/)

**Laytime** — The contractually allowed time for the charterer to load/discharge cargo without extra charge, defined in the charter party (fixed days, or "WWD SHINC" etc. running-time formulas). [BIMCO Laytime Definitions for Charter Parties 2013 is the industry-standard reference.](https://www.shipfinex.com/blog/laytime-calculation-explained-examples-pitfalls)

**NOR (Notice of Readiness)** — The vessel's formal notice to the charterer that she has arrived and is ready to load/discharge; laytime typically starts counting a fixed number of hours after NOR is tendered (subject to charter party terms on whether she must be in berth, at anchor, or "WIPON/WIBON" — whether in port or not / whether in berth or not). [Definition and NOR-to-laytime mechanics.](https://legalclarity.org/laytime-measurement-demurrage-and-despatch-explained/)

**Demurrage** — Liquidated damages paid by the charterer to the owner when laytime is exceeded; a pre-agreed daily/hourly rate compensating the owner for lost earning capacity. [Legal classification and calculation basis.](https://legalclarity.org/laytime-measurement-demurrage-and-despatch-explained/)

**Despatch** — A reward paid by the owner to the charterer for finishing cargo ops faster than allowed laytime; conventionally half the demurrage rate but negotiable. [Despatch rate convention.](https://legalclarity.org/laytime-measurement-demurrage-and-despatch-explained/)

**SOF (Statement of Facts)** — The port agent's chronological log of all events during a port call (arrival, NOR tendering, hatches open/closed, weather delays, etc.) — the source document laytime is calculated from. [Referenced as the input document laytime/demurrage software ingests.](https://www.altexsoft.com/blog/maritime-chartering-software/)

**Disbursement Account (DA)** — An itemized statement of all costs a port agent incurs on the vessel's behalf during a port call: port/harbour dues, pilotage, towage, mooring, berth occupancy, light dues, agency fee, husbandry (crew change, medical, provisions), bunker barging, customs/quarantine, security. [Full definition and cost breakdown.](https://www.usebase.io/disbursement-account/)

- **PDA (Proforma DA)** — An *estimate* of port costs issued by the agent before the call; the principal typically remits funds against it in advance.
- **FDA (Final DA)** — The *actual* costs after the call, reconciled against the PDA (and against any advance remitted).
[PDA vs FDA distinction and reconciliation flow.](https://www.da-desk.com/what-is-a-pda-and-fda-in-shipping/)

**ROB (Remaining On Board)** — The quantity of bunker fuel (IFO/MGO/VLSFO etc.) physically remaining in a vessel's tanks at a given point — tracked continuously from daily noon reports and bunker deliveries, and reconciled at redelivery (for TC) or at voyage end.

**Bunker Procurement / Replenishment** — Purchasing and delivering fuel to the vessel; tracked by date, port, supplier, grade, quantity, price, and total cost — feeds both voyage cost and ROB tracking.

**Freight** — Revenue paid by the charterer to the owner for carrying cargo under a voyage charter, usually per tonne or lump sum.

**Hire** — Revenue paid by the charterer to the owner under a time charter, typically per day or per month, often payable in advance in fixed installments (e.g. 15 or 30 days).

**Off-hire** — A period during a time charter where the charterer is not obligated to pay hire because the vessel is unable to perform (breakdown, drydocking, deviation for owner's purposes) — deducted from hire due and tracked as its own claim/adjustment type.

**Voyage P&L (Profit & Loss)** — Revenue (freight/hire/demurrage earned) minus voyage costs (bunkers, port charges/DAs, canal dues, commissions) for a single voyage, the core commercial output document. [Commercial manager's core deliverable per fixture, reconciled against DAs and the original estimate.](https://trident-maritime.com/en/news/blog/ship-commercial-management-chartering-post-fixture-and-risk-for-vessel-owners.html)

**TCE (Time Charter Equivalent)** — The industry-standard measure that converts a voyage charter's economics into an equivalent daily time-charter rate, enabling apples-to-apples comparison across charter types. **Formula: `TCE (USD/day) = (Voyage Revenue − Voyage Expenses) / Voyage Duration in Days`**, i.e. net income after voyage costs, divided by round-trip voyage days. [Baltic Exchange TCE methodology, in use since 2008.](https://www.balticexchange.com/content/dam/balticexchange/consumer/data-services-/historicalcircular_docs/TD3C-TCE_Calculation_Process_0717.pdf) [Wikipedia definition and formula, consistent with industry usage.](https://en.wikipedia.org/wiki/Time_charter_equivalent) [Baltic Exchange launched a dedicated TCE earnings calculator in 2025 to standardize this across the market.](https://www.balticexchange.com/en/news-and-events/news/press-releases-/2025/Baltic-Exchange-launches-new-TCE-earnings-calculator-to-simplify-freight-and-emissions-analysis.html)

**Claims** — Formal disputes/adjustments arising post-fixture: cargo claims (damage/shortage), off-hire claims, demurrage disputes, deadfreight — tracked separately from routine accounting because they involve counterparty negotiation and often uncertain/pending amounts.

---

## 2. Vendor Module Structure — What "Best Practice" Looks Like

### Veson Nautical IMOS (the dominant enterprise VMS)

Structured around three connected workflow stages: **[Chartering → Operations → Finance](https://veson.com/products/imos/)**, unifying "chartering, operations, and finance workflows so teams can collaborate from one connected system."

- **Chartering module**: Estimates, COAs, Cargoes, Voyage Fixtures, Time Charters, Cargo Schedule, Scheduling, TC-Out Estimates — the pre-fixture and fixture-creation side. [Module list.](https://veson.com/products/imos/chartering/)
- **Operations module**: fleet/vessel scheduling, voyage management/monitoring, "dynamic P&L," centralized voyage instructions, tasks/alerts — the post-fixture execution side. [Module description.](https://veson.com/operations-module/)
- **Specialized modules**: bunkering, berth scheduling, lightering, pooling, claims management, layered on top per commodity segment. [Specialized modules list.](https://veson.com/products/imos/imos-modules/)

### ShipNet (mid-to-large, part of Veson group)

Markets a dedicated **[Commercial](https://shipnet.no/solutions/commercial)** solution alongside Operations, Procurement, Finance, Maintenance, and Compliance — i.e. commercial management is one pillar of a larger enterprise suite rather than a standalone product, and it explicitly targets **mid-to-large fleets** with heavy customization needs (quote-based pricing reported to start around $50k+/vessel/year). This confirms ShipNet-class tooling is oversized for a single/small fleet operator. [Target market and pricing note.](https://gitnux.org/best/ship-management-software/)

### Lean structure for a small-to-mid operator (synthesized)

Across vendors, the workflow consistently decomposes into the same **five stages** regardless of company size — only the depth of each stage scales with fleet size:

1. **Pre-fixture** — voyage estimation / cargo evaluation (candidate freight/hire vs. projected costs → go/no-go)
2. **Fixture** — recording the concluded charter party terms (voyage charter, TC, or COA) that everything downstream references
3. **Operations** — day-to-day voyage execution: port calls, noon/daily reports, laytime tracking against SOF, bunker ROB monitoring
4. **Post-fixture accounts** — DA collection/reconciliation (PDA→FDA), freight/hire invoicing, claims/off-hire adjustments
5. **Reporting** — voyage P&L, TCE, fleet-level aggregation, payment status

This maps closely onto what the old shipman project already had (voyages, daily reports, charter parties, payments, bunker, reports-with-P&L/TCE) — the gap versus industry practice is mainly stage 1 (no formal pre-fixture voyage estimation/comparison tool existed) and the DA-level PDA/FDA distinction within payments (the old project tracked payments generally, not disbursement accounts as a distinct reconciled PDA→FDA object).

---

## 3. Framework Tradeoffs for an OS-Agnostic Rewrite

Evaluated for: solo/small-team maintainability, packaging/distribution simplicity, genuine cross-platform support (Win/Mac/Linux), and fit for an internal (not public-facing) business tool.

| Option | Model | Licensing | Cross-platform | Packaging | Notes |
|---|---|---|---|---|---|
| **PySide6/Qt** | Native desktop widgets, stays in Python | **LGPLv3** — free to use in closed-source apps as long as Qt itself is dynamically linked; simpler and cheaper than PyQt's GPL/commercial split. [Licensing comparison.](https://www.pythonguis.com/faq/licensing-differences-between-pyqt6-and-pyside6/) | True native on Win/Mac/Linux | `pyside6-deploy` or PyInstaller/Nuitka to single executable | Best fit when "desktop app" is meant literally — richer, more mature widget set than Tkinter, direct upgrade path from the old app's mental model. [Positioning vs. other Python GUI libs.](https://www.pythonguis.com/faq/which-python-gui-library/) |
| **PyQt6** | Same rendering engine as PySide6 | **GPLv3**, or a paid commercial license from Riverbank if you don't want to open-source | Same as PySide6 | Same | No real advantage over PySide6 for a closed-source internal tool once licensing is considered; PySide6 is the preferred choice for this reason. [GPL vs LGPL explainer.](https://www.pythonguis.com/faq/pyqt-vs-pyside/) |
| **Flet** | Flutter-rendered UI, driven from Python | Open-source (Apache 2.0) | Desktop + web + mobile from one codebase | Single `flet build` step | Attractive if you might ever want a browser or mobile view of the same UI without a rewrite, but weaker for "serious," dense, data-grid-heavy business UI than Qt; smaller ecosystem/maturity. [Where Flet fits vs. PySide6.](https://www.pythonguis.com/faq/which-python-gui-library/) |
| **Kivy** | Custom-rendered, touch-first | MIT | Desktop + mobile | Buildozer (mobile-oriented) | Optimized for touch/mobile-style UI, not for dense tabular/business-form UI — poor fit here. |
| **FastAPI/Django + React (local web app)** | Browser UI, local (or later networked) server backend | All open-source, no licensing cost | OS-agnostic by construction (anything with a browser) | Requires running a local server process (or packaging one, e.g. via PyInstaller for the backend) | Cleanest separation of concerns (backend/API vs. UI), which directly addresses the "messy structure" complaint about the old Tkinter app; naturally extensible to multi-user/remote access later without a rewrite; more moving parts to stand up (server process, API layer, auth-readiness) than a single-binary desktop app. |
| **Tauri (Rust shell + web frontend)** | Native shell + system webview + your own JS frontend | MIT / Apache 2.0 | Win/Mac/Linux (+ iOS/Android in 2.x) | Small installers — [~3.2MB "Hello World" vs. 85MB Electron, ~380ms cold start vs. 1420ms](https://tech-insider.org/tauri-vs-electron-2026/) | Excellent packaging story, but the backend is idiomatically Rust — pairing it with a Python backend over IPC/HTTP adds real complexity for a solo Python developer; best suited if you're willing to invest in a JS/Rust frontend layer. |
| **Electron + Python backend** | Chromium shell + your own JS frontend + Python backend | MIT (Electron itself) | Win/Mac/Linux | Large installers (Chromium bundled), mature tooling (Electron Forge/Packager) | Same architectural split as Tauri without the size/perf advantage; only worth it over Tauri for its more mature ecosystem/tooling if that matters more than bundle size. [Packaging tools.](https://www.coderio.com/blog/software-development/electron-framework-complete-guide/) |

**Decision-oriented summary**: For a solo Python developer rewriting an internal single-user business tool, the real choice is between two coherent architectures — **(A) PySide6**, a direct, low-risk upgrade from Tkinter (same language, same "one process" mental model, LGPL licensing is a non-issue for closed-source internal use), or **(B) FastAPI + a browser frontend**, which costs more upfront structure (a real API layer) but buys the cleanest backend/UI separation, is OS-agnostic without any native-toolkit dependency, and leaves a clear path to multi-user access later without an architectural rewrite. Tauri/Electron only make sense if a JS-based frontend is independently desirable; they don't have a natural advantage over option (B) for a Python-heavy internal tool.

---

## Sources

- [Veson Nautical — IMOS Modules](https://veson.com/products/imos/imos-modules/)
- [Veson Nautical — IMOS Chartering](https://veson.com/products/imos/chartering/)
- [Veson Nautical — IMOS overview](https://veson.com/products/imos/)
- [Veson Nautical — Operations module](https://veson.com/operations-module/)
- [ShipNet — Commercial solutions](https://shipnet.no/solutions/commercial)
- [Ship Management Software 2026 comparison (ShipNet pricing/target market)](https://gitnux.org/best/ship-management-software/)
- [Trident Maritime — Ship Commercial Management guide](https://trident-maritime.com/en/news/blog/ship-commercial-management-chartering-post-fixture-and-risk-for-vessel-owners.html)
- [AltexSoft — Maritime Chartering Software features](https://www.altexsoft.com/blog/maritime-chartering-software/)
- [Baltic Exchange — TCE calculator launch (2025)](https://www.balticexchange.com/en/news-and-events/news/press-releases-/2025/Baltic-Exchange-launches-new-TCE-earnings-calculator-to-simplify-freight-and-emissions-analysis.html)
- [Baltic Exchange — TD3C TCE calculation methodology PDF](https://www.balticexchange.com/content/dam/balticexchange/consumer/data-services-/historicalcircular_docs/TD3C-TCE_Calculation_Process_0717.pdf)
- [Wikipedia — Time charter equivalent](https://en.wikipedia.org/wiki/Time_charter_equivalent)
- [usebase.io — Disbursement Account (DA) meaning](https://www.usebase.io/disbursement-account/)
- [usebase.io — PDA and FDA in shipping](https://www.usebase.io/pda-and-fda-in-shipping/)
- [DA-Desk — What is a PDA and FDA in shipping](https://www.da-desk.com/what-is-a-pda-and-fda-in-shipping/)
- [ShipFinex — Laytime calculation explained](https://www.shipfinex.com/blog/laytime-calculation-explained-examples-pitfalls)
- [LegalClarity — Laytime, demurrage, and despatch explained](https://legalclarity.org/laytime-measurement-demurrage-and-despatch-explained/)
- [PythonGUIs — Which Python GUI library should you use](https://www.pythonguis.com/faq/which-python-gui-library/)
- [PythonGUIs — PyQt6 vs PySide6 licensing](https://www.pythonguis.com/faq/licensing-differences-between-pyqt6-and-pyside6/)
- [PythonGUIs — PyQt vs PySide licensing (GPL vs LGPL)](https://www.pythonguis.com/faq/pyqt-vs-pyside/)
- [Tech Insider — Tauri vs Electron 2026 benchmarks](https://tech-insider.org/tauri-vs-electron-2026/)
- [Coderio — Electron Framework 2026 guide](https://www.coderio.com/blog/software-development/electron-framework-complete-guide/)
