import re

UTR_RE = re.compile(r"^[A-Za-z0-9]{6,30}$")


def normalize_utr(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).upper()


def is_valid_utr(value: str) -> bool:
    return bool(UTR_RE.fullmatch(normalize_utr(value)))
