---
status: accepted
---

# Local web app (Python backend + browser frontend) instead of a native desktop toolkit

v1 was a Tkinter desktop app; the rewrite explicitly needed to be OS-agnostic and to fix v1's monolithic, hard-to-maintain UI/logic structure. The direct upgrade path — PySide6/Qt, staying in the native-desktop model — was considered and rejected in favor of a local web app: a Python backend (FastAPI recommended) serving a browser-based frontend on the same machine. This forces a real API boundary between backend logic and UI (addressing the structural complaint about v1), is OS-agnostic without depending on a native toolkit's platform support, and leaves a clear path to multi-user/remote access later without an architectural rewrite, at the cost of more upfront structure (a real API layer) than a single-process desktop app would need. See [`research_commercial_shipmanagement.md`](../../research_commercial_shipmanagement.md) §3 for the full framework comparison (PySide6, Flet, Kivy, Tauri, Electron) that informed this choice.
