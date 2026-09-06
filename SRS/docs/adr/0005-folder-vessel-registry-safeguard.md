---
status: accepted
---

# Folder↔vessel registry as the IMAP misattribution safeguard

`poll-imap` takes an IMAP folder (a runtime setting) and a `vessel_id` (a request parameter) as two independently-chosen inputs, with nothing structurally keeping them in sync between polls. This is exactly what caused a real incident: 44 genuine historical daily reports for one vessel (SP Dikson) were ingested while a different vessel was selected in the operator's dropdown, silently misattributing weeks of real operational history until caught and corrected through the audited reassignment path.

Two designs were considered: cross-checking the vessel name mentioned in each message's free-text preamble against the registered vessel, or remembering which vessel each folder was last polled for. The content-matching approach was rejected as the primary mechanism — the same fleet's own data shows a vessel referred to under inconsistent transliterations ("NP Dudinka" vs. "СП Дудинка"), which is precisely the kind of mismatch that would make text matching produce both false alarms and missed real mismatches. The operator's own workflow — one IMAP folder per vessel per year — makes a **folder↔vessel registry** the structural fix instead: `imap_folder_vessel_mappings` records the vessel each folder is associated with, established on a folder's first poll. A subsequent poll of a known folder under a *different* vessel is blocked with a 409 identifying the previously-associated vessel, and only proceeds if the caller explicitly passes `confirm_vessel_change: true` — at which point the mapping updates to the new vessel. `GET /daily-reports/imap-folder-mapping/{folder}` lets the operator check a folder's registered vessel proactively, before polling.

The [Vessel Naming Policy](../../CONTEXT.md) (register Russian-flagged vessels under a single consistent Russian name/spelling) was adopted alongside this — not because the registry depends on it, but because it removes the specific failure mode that ruled out content-based matching, keeping that option available as a future second layer of defense if ever needed.
