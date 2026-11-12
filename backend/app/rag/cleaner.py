import re
import unicodedata

_PAGE_NUMBER = re.compile(r"(page\s*)?\d{1,4}(\s*(/|of)\s*\d{1,4})?", re.IGNORECASE)


def clean_text(raw: str) -> str:
    """Normalise extracted text: strip control chars, repair PDF line-wrapping, drop bare page numbers."""
    t = unicodedata.normalize("NFKC", raw)  # also folds ligatures such as "ﬁ" -> "fi"
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)  # re-join words hyphenated across lines

    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")]
    lines = [ln for ln in lines if not _PAGE_NUMBER.fullmatch(ln)]
    t = "\n".join(lines)

    # Unwrap hard line breaks inside a sentence, but keep bullets, headings and code lines intact.
    t = re.sub(r"(?<=[^\n.:;!?])\n(?=[a-z])", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
