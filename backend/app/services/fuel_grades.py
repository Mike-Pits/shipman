"""Canonical fuel-grade names.

Grade names are free text typed in several places (vessel consumption tables, voyage fuel
prices). Operators switching keyboard layouts produce visually identical but distinct strings —
Latin "MGO" vs Cyrillic "МГО", different dash characters, stray whitespace, mixed case. Folding
them to one canonical Latin form lets consumption and prices merge correctly.
"""

import re

_CYRILLIC_TO_LATIN = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E", "Ж": "ZH",
    "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O",
    "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "KH", "Ц": "TS",
    "Ч": "CH", "Ш": "SH", "Щ": "SHCH", "Ъ": "", "Ы": "Y", "Ь": "", "Э": "E", "Ю": "YU",
    "Я": "YA",
}
_DASHES = re.compile("[‐‑‒–—―−]")


def normalize_grade(grade: str | None) -> str:
    if grade is None:
        return ""
    folded = re.sub(r"\s+", " ", str(grade).strip()).upper()
    folded = _DASHES.sub("-", folded)
    return "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in folded)
