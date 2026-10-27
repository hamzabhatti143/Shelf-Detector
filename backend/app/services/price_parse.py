# backend/app/services/price_parse.py
import re
from typing import Optional

# koi bhi currency symbol/letters ignore; sirf number token dhoondho
_NUM_RE = re.compile(r"\d[\d.,]*")


def _groups_ok(txt: str, sep: str) -> bool:
    parts = txt.split(sep)
    return all(parts) and 1 <= len(parts[0]) <= 3 and all(len(p) == 3 for p in parts[1:])


def parse_amount(raw: str) -> Optional[float]:
    """Number sirf tab jab separators unambiguous hon, warna None."""
    s = raw.strip().rstrip(".,")
    if not re.fullmatch(r"\d[\d.,]*", s):
        return None
    if s.isdigit():
        return float(s)

    last = max(s.rfind("."), s.rfind(","))
    dec_sep = s[last]
    other = "," if dec_sep == "." else "."
    head, tail = s[:last], s[last + 1:]

    if other in head:  # mixed: 1,234.50 / 1.234,5
        if dec_sep in head:
            return None
        if len(tail) in (1, 2) and _groups_ok(head, other):
            return float(head.replace(other, "") + "." + tail)
        return None
    if dec_sep in head:  # repeated: 1,234,567
        if len(tail) == 3 and _groups_ok(s, dec_sep):
            return float(s.replace(dec_sep, ""))
        return None
    if len(tail) in (1, 2):  # 12.50
        return float(f"{head}.{tail}")
    return None  # 1,150 / 1.150 ambiguous -> None


def extract_price(text: str) -> Optional[float]:
    """Price-area text se pehla unambiguous number. Currency ignore."""
    tokens = _NUM_RE.findall(text)
    if len(tokens) != 1:       # 0 ya 2+ numbers: guess nahi karte
        return None
    return parse_amount(tokens[0])


if __name__ == "__main__":
    cases = {
        "Rs. 420": 420, "$12.50": 12.5, "£3.99": 3.99, "€ 7": 7,
        "Rz. 680": 680, "420": 420, "Rs. 1150": 1150,
        "Rs. 1,150": None, "Lays)": None, "Rs 10 Rs 20": None,
    }
    for t, want in cases.items():
        got = extract_price(t)
        print("OK  " if got == want else "FAIL", repr(t), got)