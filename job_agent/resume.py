from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "you",
    "your",
    "will",
    "this",
    "have",
    "has",
    "using",
    "used",
    "work",
    "worked",
    "experience",
    "years",
}


@dataclass
class ResumeProfile:
    path: Path
    raw_text: str
    normalized_text: str
    top_terms: list[str] = field(default_factory=list)
    token_set: set[str] = field(default_factory=set)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\+\#\.\-/]{1,}", text.lower())


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"Unsupported resume format: {path.suffix}")


def load_resume_profile(path: Path) -> ResumeProfile:
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    raw_text = _extract_text(path)
    normalized_text = _normalize_text(BeautifulSoup(raw_text, "html.parser").get_text(" "))
    tokens = [token for token in _tokenize(normalized_text) if token not in STOP_WORDS and len(token) > 2]
    counter = Counter(tokens)
    top_terms = [term for term, _ in counter.most_common(80)]
    return ResumeProfile(
        path=path,
        raw_text=raw_text,
        normalized_text=normalized_text,
        top_terms=top_terms,
        token_set=set(top_terms),
    )
