# Commercial Ship Management (v2)

Domain glossary for the ground-up rewrite of the shipman commercial ship management system: a tool for a tanker owner/operator to run the commercial side of the business (chartering, voyage economics, accounts, reporting). Technical management (crewing, PMS, drydocking) is explicitly out of scope.

## Language

**Owner/Operator**:
The business role this system serves: a company that owns or long-term charters-in vessels and trades them commercially itself (as opposed to managing vessels commercially on behalf of a separate principal, or acting purely as a broker).
_Avoid_: Ship manager (implies third-party technical/commercial management for others), broker

**Fleet**:
The set of tankers this operator trades, running Arctic–Baltic range routes. Daily reports from these vessels are received in Russian; the system must support an English/Russian UI toggle.

**TCE (Time Charter Equivalent)**:
The industry-standard daily-rate measure used to compare voyage economics across charter types. `TCE (USD/day) = (Voyage Revenue − Voyage Expenses) / Voyage Duration in Days`. Adopted as-is from Baltic Exchange/industry convention — see [research_commercial_shipmanagement.md](research_commercial_shipmanagement.md).

**Disbursement Account (DA)**:
An itemized statement of port-call costs prepared by the port agent (pilotage, towage, mooring, agency fee, husbandry, etc.), tracked per port call in two stages:
- **PDA (Proforma DA)**: the agent's pre-call cost *estimate*, used to fund an advance.
- **FDA (Final DA)**: the agent's post-call *actual* costs, reconciled against the PDA.
DAs are a distinct, reconciled entity — not folded into general payment records.
_Avoid_: Port costs, agency invoice (too generic — use PDA/FDA to be explicit about which stage)

**Fixture**:
A concluded charter agreement. This project supports three fixture types: **Voyage Charter**, **Time Charter Out**, and **COA**. Time Charter In is explicitly out of scope — this operator does not charter tonnage in from other owners.

**Voyage Charter**:
Fixture for a single voyage between load and discharge ports; freight paid per tonne or lump sum; owner bears voyage costs (bunkers, port costs). The primary fixture type for this fleet.

**Voyage**:
The operator-defined unit of operational tracking under a Fixture. It may span multiple port-to-port passages as a single continuous record (e.g. multi-port loading then multi-port discharging, or an entire Time Charter Out employment period), or the operator may split successive passages into separate records — this is a deliberate per-fixture choice, not a system-enforced rule. Daily reports, costs, and DAs attach to whichever granularity the operator has chosen for that stretch of activity.

**Voyage Estimate**:
A pre-fixture projection for a candidate voyage — projected freight/hire revenue minus projected bunker consumption, port costs, and days — used to decide whether to accept a fixture. Once a fixture is concluded, its estimate becomes the baseline the eventual Voyage P&L is reconciled against. Modeled as its own stage, distinct from (and prior to) a concluded Fixture.

**Time Charter Out**:
Fixture letting one of the fleet's own tankers to a charterer for a period; charterer pays daily/monthly hire and bears voyage costs; owner bears running costs.

**COA (Contract of Affreightment)**:
Term contract to carry a series of cargoes over a period, without committing specific vessels in advance to each lift.

**Cargo**:
This fleet carries clean/product cargoes (refined products) exclusively — not crude or chemical. Cargo quantity/quality conventions follow clean-product norms, not crude (API/VEF) or chemical (grade segregation) conventions.

**Vetting**:
A tanker-specific commercial gate: charterers require a vessel to hold current inspection approval (e.g. SIRE-style) before they'll fix it. Tracked per vessel with full inspection history — inspection date, inspecting body/charterer, expiry, observations/findings — since an expired or failed vetting status can make a vessel commercially unfixable regardless of price.

**Claim**:
A post-fixture dispute over amount owed (cargo quantity/quality, demurrage, off-hire) tracked separately from routine DA/payment records, with its own status (open/negotiating/settled) and amount — kept out of the clean P&L/payment timeline while unresolved.

**Ice Class / Escort Fee**:
Ice class is a vessel attribute (structured field). Icebreaker/escort assistance is tracked as a distinct voyage cost line, since it's commercially material on Arctic routes. NSR permits and seasonal routing restrictions are captured as free-text notes, not structured workflow data.

**PDA / FDA itemization**:
PDA is recorded as a lump-sum estimate (matches how agents issue it — a funding estimate, not a breakdown). FDA is itemized by cost line (pilotage, towage, agency fee, etc.), since reconciliation and disputes happen at the line-item level in practice.
