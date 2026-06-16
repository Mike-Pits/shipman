We are now ready to build the Reports tab. This is the module where all the data are entered — daily reports, voyages, charter parties, payments, and bunker costs—will be transformed into actionable intelligence. The goal is to make this tab as flexible as possible, allowing you to generate a wide variety of reports.

Based on industry standards, here is a comprehensive list of report types that a shipping company needs to manage its fleet effectively. They are organized into logical categories.

### I. Operational Performance Reports (The "How Are We Sailing?" Reports)

These reports focus on the physical performance of the vessels.

*   **Voyage Summary Report:**
    *   **Description:** A detailed breakdown of a single voyage. It should include the voyage number, vessel name, ports of call, dates (sailing, arrival, etc.), total distance sailed, total fuel consumed (IFO & MGO), average speed, and a link to the daily reports.
    *   **Primary Source:** `voyages`, `daily_reports`.
*   **Fleet Distance & Speed Analysis:**
    *   **Description:** A report showing the total distance sailed and average speed for each vessel over a selected period (e.g., month, quarter, year). This is useful for tracking operational activity.
    *   **Primary Source:** `daily_reports`.
*   **Fuel Consumption Report (by Vessel & Period):**
    *   **Description:** A comprehensive report on fuel consumption. It should display total IFO and MGO consumed by each vessel over a period. This is critical for budgeting and identifying inefficiencies.
    *   **Primary Source:** `daily_reports` (consumption fields).
*   **Laden vs. Ballast Performance:**
    *   **Description:** A comparison of a vessel's speed and fuel consumption when it is laden (carrying cargo) vs. in ballast (empty). This helps in understanding the operational efficiency under different conditions.
    *   **Primary Source:** `daily_reports` (distance, consumption, and the `is_laden` flag from `voyages`).

### II. Commercial & Financial Reports (The "Are We Making Money?" Reports)

These reports focus on the financial performance of the vessels and the company.

*   **Voyage P&L (Profit & Loss) Report:**
    *   **Description:** The most critical commercial report. It calculates the profit or loss for a single voyage. It should show:
        *   **Revenue:** Freight earned, demurrage.
        *   **Voyage Costs:** Bunkers, port charges, canal dues, agents fees, etc.
        *   **Net Voyage Result:** Revenue - Voyage Costs.
    *   **Primary Source:** `voyages`, `payments` (income & expense), `bunker_replenishments`.
*   **Time Charter Equivalent (TCE) Report:**
    *   **Description:** The industry standard for measuring a vessel's daily revenue performance. It represents the average daily revenue a vessel earns after deducting voyage expenses. The formula is:
        `TCE (USD/day) = (Voyage Revenue - Voyage Expenses) / Voyage Duration in Days`.
    *   This report should calculate and display the TCE for each voyage and also allow for a fleet-wide average.
    *   **Primary Source:** `voyages`, `payments`.
*   **Fleet P&L Summary:**
    *   **Description:** A high-level summary of the financial performance of the entire fleet over a selected period. It aggregates the revenue, costs, and net profit for all vessels.
    *   **Primary Source:** `payments`, `voyages`.
*   **Payment Status Report:**
    *   **Description:** A report to monitor outstanding payments. It should display all invoices (income and expenses) with their due dates and current status (Pending, Paid, Overdue).
    *   **Primary Source:** `payments`.

### III. Vessel Utilization & Efficiency Reports (The "Are We Using Our Assets Wisely?" Reports)

These reports focus on how effectively the vessels are being used.

*   **Vessel Utilization Report:**
    *   **Description:** A breakdown of how a vessel's time is spent during a voyage or over a period. It should show the percentage of time spent:
        *   Underway (Sailing)
        *   In Port (Loading/Discharging)
        *   Waiting (At Anchor, Idle)
    *   **Primary Source:** `daily_reports` (distance, speed, port name), `voyages`.
*   **Bunker Replenishment Report:**
    *   **Description:** A summary of all bunker fuel purchases. It should include the date, port, supplier, quantity (IFO/MGO), price per MT, total cost, and the vessel it was purchased for.
    *   **Primary Source:** `bunker_replenishments`.
*   **Cargo Summary Report:**
    *   **Description:** A report showing the total cargo carried by each vessel or the entire fleet over a period. This is useful for understanding cargo throughput.
    *   **Primary Source:** `voyages` (cargo quantity).
*   **Demurrage & Despatch Report:**
    *   **Description:** A report detailing demurrage (charges for exceeding laytime) and despatch (savings for using less laytime) earned or incurred on voyages. This is a critical commercial KPI.
    *   **Primary Source:** `charter_parties` (laytime allowed, demurrage rate), `timesheet_events`, `payments`.

### IV. Environmental & Compliance Reports (The "Are We Compliant?" Reports)

*   **Carbon Intensity Indicator (CII) Report:**
    *   **Description:** A regulatory report that calculates the vessel's carbon intensity. The formula is `CO2 emissions / (Capacity * Distance sailed)`. This is a crucial metric for the IMO's decarbonization targets.
    *   **Primary Source:** `daily_reports` (distance, consumption), `vessels` (deadweight/capacity).
*   **Energy Efficiency Operational Indicator (EEOI) Report:**
    *   **Description:** Similar to CII, this is a measure of a vessel's energy efficiency for a specific voyage or period. It is calculated as `CO2 emissions per tonne-mile`.
    *   **Primary Source:** `daily_reports`, `vessels`.

---

## Database Schema Support for Reports

The foundation for these reports is already in your database. The Reports tab will primarily query the following tables:

*   `daily_reports`: For all operational data (distance, speed, consumption, dates, etc.).
*   `voyages`: For voyage-specific details (ports, dates, cargo).
*   `charter_parties`: For commercial terms (rates, laytime).
*   `payments`: For financial data (income, expenses).
*   `bunker_replenishments`: For bunker purchase details and costs.
*   `vessels`: For vessel characteristics (capacity, type).

---

## Proposed UI/UX for the Reports Tab

The Reports tab will be the most flexible part of the application. It will be designed as a **Report Builder** to allow you to generate any of the above reports.

### Layout Concept

1.  **Report Type Selector:** A dropdown menu at the top to select the type of report (e.g., "Voyage P&L," "TCE Report," "Fuel Consumption").
2.  **Parameters Panel:** Below the selector, a dynamic panel will appear with filters and options specific to the selected report type. For example:
    *   **Date Range:** Start and end date pickers.
    *   **Vessel:** A dropdown to select a single vessel or "All Vessels."
    *   **Voyage:** A dropdown to select a specific voyage.
    *   **Currency:** A toggle to display amounts in RUB or USD (using historical exchange rates from the `exchange_rates` table).
3.  **Action Buttons:**
    *   **"Generate Report":** A button to execute the report query.
    *   **"Export to Excel":** A button to export the report data to an Excel file (using your existing `excel_exporter`).
4.  **Results Area:** A `ttk.Treeview` that displays the generated report data in a table format.

### Example: Voyage P&L Report

*   **Report Type:** Voyage P&L
*   **Parameters:**
    *   **Vessel:** Dropdown (e.g., "All," "SP Dudinka," "SP Dikson")
    *   **Date Range:** Date pickers
*   **Results Table:**
    *   Columns: Voyage # | Vessel | Charterer | Start Date | End Date | Revenue (Freight) | Voyage Costs (Bunkers, Port, etc.) | Net Result | TCE (USD/day)
    *   Totals row at the bottom.

---

## Implementation Plan

Building this flexible Reports tab is a significant undertaking. To make it manageable, it will be implemented it in phases.

### Phase 1: The Report Framework & Simple Reports (MVP)

*   **Goal:** Create the basic UI structure and implement the simplest reports that rely mostly on your existing data.
*   **Reports:**
    1.  **Voyage Summary Report:** Show data from the `voyages` and `daily_reports` tables.
    2.  **Fuel Consumption Report:** Show consumption from `daily_reports`.
    3.  **Fleet Distance & Speed Report:** Show distance and speed from `daily_reports`.
*   **Implementation Steps:**
    1.  Create the `modules/reports.py` file.
    2.  Add the "Reports" tab to `main_window.py`.
    3.  Implement the Report Builder UI (dropdown, parameters panel, generate button).
    4.  Write a `ReportEngine` class to manage database queries and data formatting.
    5.  Implement the three simple reports.

### Phase 2: Financial & Performance Reports (Full Features)

*   **Goal:** Implement the more complex reports that require joining data from multiple tables and performing calculations.
*   **Reports:**
    1.  **Voyage P&L:** Join `voyages` with `payments` (income and expense).
    2.  **TCE Report:** Calculate TCE using the P&L data.
    3.  **Fleet P&L Summary:** Aggregate P&L data across voyages.
*   **Implementation Steps:**
    1.  Extend the `ReportEngine` with complex query builders.
    2.  Implement the P&L and TCE calculation logic.
    3.  Add currency toggle functionality.

### Phase 3: Advanced & Compliance Reports (Specialized)

*   **Goal:** Implement reports that require more complex calculations or data interpretation.
*   **Reports:**
    1.  **Vessel Utilization Report:** Calculate time spent in different states.
    2.  **CII Report:** Calculate Carbon Intensity Indicator.
    3.  **Bunker Summary Report.**
*   **Implementation Steps:**
    1.  Develop the specific logic for each report.
    2.  Add support for exporting to Excel.

---
