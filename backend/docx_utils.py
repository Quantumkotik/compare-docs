import difflib
import io

from docx import Document


def extract_paragraphs(content: bytes) -> list[str]:
    document = Document(io.BytesIO(content))
    return [p.text for p in document.paragraphs]


def diff_paragraphs(paragraphs1: list[str], paragraphs2: list[str]) -> list[dict]:
    """Align old/new paragraphs into side-by-side rows.

    Each row has an optional "left" (old, highlighted red when changed) and
    an optional "right" (new, highlighted green when changed) cell, so the
    frontend can render two columns that line up paragraph by paragraph.
    """
    matcher = difflib.SequenceMatcher(a=paragraphs1, b=paragraphs2)
    rows = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for old_text, new_text in zip(paragraphs1[i1:i2], paragraphs2[j1:j2]):
                rows.append({
                    "left": {"type": "equal", "text": old_text},
                    "right": {"type": "equal", "text": new_text},
                })
        elif tag == "delete":
            for old_text in paragraphs1[i1:i2]:
                rows.append({"left": {"type": "delete", "text": old_text}, "right": None})
        elif tag == "insert":
            for new_text in paragraphs2[j1:j2]:
                rows.append({"left": None, "right": {"type": "insert", "text": new_text}})
        elif tag == "replace":
            old_texts = paragraphs1[i1:i2]
            new_texts = paragraphs2[j1:j2]
            for k in range(max(len(old_texts), len(new_texts))):
                left = {"type": "delete", "text": old_texts[k]} if k < len(old_texts) else None
                right = {"type": "insert", "text": new_texts[k]} if k < len(new_texts) else None
                rows.append({"left": left, "right": right})
    return rows
