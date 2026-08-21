import difflib
import io

from docx import Document


def extract_paragraphs(content: bytes) -> list[str]:
    document = Document(io.BytesIO(content))
    return [p.text for p in document.paragraphs]


def diff_paragraphs(paragraphs1: list[str], paragraphs2: list[str]) -> list[dict]:
    matcher = difflib.SequenceMatcher(a=paragraphs1, b=paragraphs2)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in paragraphs1[i1:i2]:
                result.append({"type": "equal", "text": line})
        elif tag == "delete":
            for line in paragraphs1[i1:i2]:
                result.append({"type": "delete", "text": line})
        elif tag == "insert":
            for line in paragraphs2[j1:j2]:
                result.append({"type": "insert", "text": line})
        elif tag == "replace":
            for line in paragraphs1[i1:i2]:
                result.append({"type": "delete", "text": line})
            for line in paragraphs2[j1:j2]:
                result.append({"type": "insert", "text": line})
    return result
