import re
import unicodedata

STOPWORDS = {
    "a", "o", "os", "as", "um", "uma", "de", "da", "do", "das", "dos", "e", "em",
    "para", "por", "com", "na", "no", "nas", "nos", "que", "qual", "quais", "se",
    "sua", "seu", "the", "of", "to", "me", "eu", "sobre", "ao", "retorne",
    "retornar", "mostre", "mostrar", "produto", "item",
}

SKU_RE = re.compile(r"\b[a-z]{2,}\d{3,}\b", re.I)
ID_RE = re.compile(r"\b(?:[a-z]{2,}\d{3,}|\d{4,}(?:\.\d+)?)\b", re.I)
QA_RE = re.compile(
    r"\b(?:pergunta|questao|questão|exercicio|exercício|item)\s*(?:n[oº°]?\.?\s*)?(\d+)\b",
    re.I,
)
QA_SPLIT_RE = re.compile(
    r"(?=(?:^|\n)\s*(?:pergunta|quest[aã]o|exerc[ií]cio)\s*\d+\b)",
    re.I,
)
NUMBERED_SPLIT_RE = re.compile(r"(?=(?:^|\n)\s*\d{1,3}\s*[\.\)]\s+\S)")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower().strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


def significant_tokens(text: str) -> list[str]:
    return [tok for tok in tokenize(text) if tok not in STOPWORDS and len(tok) > 1]


def extract_skus(text: str) -> list[str]:
    return [m.group(0).upper() for m in SKU_RE.finditer(text or "")]


def extract_record_ids(text: str) -> list[str]:
    seen: list[str] = []
    for match in ID_RE.finditer(text or ""):
        value = match.group(0).upper().rstrip("0").rstrip(".") if "." in match.group(0) else match.group(0).upper()
        raw = match.group(0).upper()
        for item in (raw, value):
            if item and item not in seen:
                seen.append(item)
    return seen


def extract_question_numbers(text: str) -> list[str]:
    return [m.group(1) for m in QA_RE.finditer(text or "")]


def has_word(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalize(needle))}(?![a-z0-9])", normalize(haystack)) is not None


def is_heading_text(text: str) -> bool:
    compact = " ".join((text or "").split())
    if not compact or len(compact) > 90:
        return False
    letters = [ch for ch in compact if ch.isalpha()]
    if len(letters) < 4:
        return False
    upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
    if upper_ratio >= 0.75:
        return True
    lowered = normalize(compact)
    prefixes = (
        "explicacao",
        "conclusao",
        "enunciado",
        "objetivo",
        "resultados",
        "teste",
        "informacoes",
        "resposta",
        "codigo",
        "ferramenta",
        "cenario",
        "pergunta",
        "questao",
    )
    return any(lowered.startswith(prefix) for prefix in prefixes)
