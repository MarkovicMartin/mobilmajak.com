"""Skórování slov nad extracted_text. Bez jazykového modelu.

Odpověď má tvar, který později může vyplnit model:
{"answer": str, "sources": [{"document_id", "title", "excerpt", "score", "download_path"}]}
"""
import re
import unicodedata

from .models import KnowledgeDocument

EMPTY_ANSWER = 'V knowledge base nic neodpovídá tomuto dotazu.'
MAX_HITS = 5
EXCERPT_RADIUS = 140

_TOKEN_RE = re.compile(r'[0-9a-z]{2,}')
_STOP = frozenset({
    'a', 'i', 'o', 'u', 'k', 's', 'z', 'v', 've', 'na', 'do', 'od', 'po', 'za', 'pro',
    'se', 'si', 'je', 'to', 'ta', 'ten', 'ti', 'jak', 'co', 'ne', 'ano', 'nebo', 'ale',
    'the', 'and', 'or', 'of', 'to',
})


def fold(text: str) -> str:
    decomposed = unicodedata.normalize('NFD', (text or '').casefold())
    return ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')


def tokenize(question: str) -> list[str]:
    tokens = _TOKEN_RE.findall(fold(question))
    meaningful = [token for token in tokens if token not in _STOP]
    return meaningful or tokens


def build_answer(question: str) -> dict:
    hits = rank_excerpts(question)
    if not hits:
        return {'answer': EMPTY_ANSWER, 'sources': []}
    lines = [f"„{hit['title']}“ — {hit['excerpt']}" for hit in hits]
    return {
        'answer': '\n\n'.join(lines),
        'sources': [
            {
                'document_id': hit['document_id'],
                'title': hit['title'],
                'excerpt': hit['excerpt'],
                'score': hit['score'],
                'download_path': f"/api/knowledge/documents/{hit['document_id']}/download/",
            }
            for hit in hits
        ],
    }


def rank_excerpts(question: str) -> list[dict]:
    tokens = tokenize(question)
    if not tokens:
        return []
    phrase = ' '.join(tokens)
    ranked = []
    documents = KnowledgeDocument.objects.filter(aktivni=True).exclude(extracted_text='').only(
        'id', 'nazev', 'extracted_text',
    )
    for document in documents:
        folded = fold(document.extracted_text)
        score = 0
        for token in tokens:
            score += folded.count(token)
        if phrase and phrase in folded:
            score += 5
        if score <= 0:
            continue
        ranked.append({
            'document_id': document.id,
            'title': document.nazev,
            'excerpt': _excerpt(document.extracted_text, tokens),
            'score': score,
        })
    ranked.sort(key=lambda item: (-item['score'], item['title'].casefold(), item['document_id']))
    return ranked[:MAX_HITS]


def _excerpt(text: str, tokens: list[str]) -> str:
    haystack = text.casefold()
    positions = []
    for token in tokens:
        index = haystack.find(token)
        if index >= 0:
            positions.append(index)
    if not positions:
        snippet = text.strip()
        if len(snippet) > EXCERPT_RADIUS * 2:
            return snippet[: EXCERPT_RADIUS * 2].rstrip() + '…'
        return snippet
    start = max(0, min(positions) - 60)
    end = min(len(text), max(positions) + EXCERPT_RADIUS)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = '…' + snippet
    if end < len(text):
        snippet = snippet + '…'
    return snippet
