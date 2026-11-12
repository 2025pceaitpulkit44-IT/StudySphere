import re


def chunk_text(text: str, max_words: int = 220, overlap_words: int = 40) -> list[str]:
    """Split text into overlapping, paragraph-aware chunks.

    Paragraphs are kept whole where possible; oversized paragraphs are split on sentences, then on
    words. Each new chunk starts with the last `overlap_words` words of the previous one so an idea
    that straddles a boundary is still retrievable. A chunk is at most max_words + overlap_words long.
    """
    if not text or not text.strip():
        return []

    units: list[str] = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()):
        if len(para.split()) <= max_words:
            units.append(para)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            words = sentence.split()
            if len(words) <= max_words:
                units.append(sentence)
            else:
                units.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))

    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for unit in units:
        n = len(unit.split())
        if current and count + n > max_words:
            chunks.append("\n\n".join(current))
            tail = " ".join(chunks[-1].split()[-overlap_words:]) if overlap_words else ""
            current, count = ([tail], len(tail.split())) if tail else ([], 0)
        current.append(unit)
        count += n
    if current:
        chunks.append("\n\n".join(current))
    return chunks
