from __future__ import annotations

from dataclasses import replace

from .hybrid import RetrievalResult
from .text import meaningful_tokens, tokenize
from finzanjir_ai.knowledge.index import KnowledgeIndex


_IDENTITY_QUERY_HINTS = (
    "FINZANJIR moliyaviy xavfsizlik firibgarlik zanjiri",
    "FINZANJIR maqsad vazifa himoya bank",
    "moliyaviy xavflarni aniqlash fuqarolar mablag'ini himoya qilish",
)

# Search hints only: the canonical author layer must supply every biographical fact.
_AUTHOR_QUERY_HINTS = (
    "Salamat Smaylov FINZANJIR muallifi yaratuvchisi asoschisi",
    "muallif tarjimai holi hayoti ta'lim qiziqishlari astronomiya kimyo",
    "FINZANJIR g'oyasi yaratilish sababi muallif motivatsiyasi",
)


# Curated local rewrites for citizen/funds protection questions. These are
# retrieval hints only; the answer must still be supported by retrieved records.
_CITIZEN_PROTECTION_QUERY_HINTS = (
    "fuqarolarning qonuniy mablag'lari va tranzaksiyalariga asossiz zarar yetmasligi",
    "shubhali pul oqimlarini aniqlash va tahlil qilish",
    "moliyaviy firibgarlik xavfini erta aniqlash va fuqarolar mablag'ini himoya qilish",
    "false positive false negative qonuniy operatsiyalarni xato belgilash",
    "signal Risk Case vakolatli inson ko'rigi va fuqaro murojaati",
    "bank bilan qonuniy hamkorlik ma'lumotlarni minimallashtirish",
)


_MULTI_CARD_FRAUD_QUERY_HINTS = (
    "pulni bir nechta bank kartasi orqali o'tkazish zanjiri",
    "aloqador kartalar hisoblar va pul oqimlarini Cross-Match orqali bog'lash",
    "Cross-Match Fraud Graph orqali aloqador obyektlar konteksti",
    "bir nechta tranzaksiya va kartalar orasidagi takroriy harakatlar",
    "shubhali pul oqimi bo'yicha signal Risk Case dalillar va vakolatli ko'rib chiqish",
    "card to card transaction chain multiple accounts linked entities fraud graph",
)


_SIGNAL_PROCESS_QUERY_HINTS = (
    "signal aniqlangandan keyin Evidence Risk Score Case va audit bosqichlari",
    "Transaction → Signal → Evidence → Risk → Threshold → Case → HumanDecision → AuditEvent",
    "signal aniqlangandan keyin Evidence tekshiruvi Risk Score va Threshold baholash",
    "shubhali signalni dalillar bilan tekshirish risk darajasini baholash va Case ochish",
    "Case escalation threshold bajarilgandan keyin vakolatli Human Review",
    "vakolatli mutaxassis inson ko'rigi va bankning qaror qabul qilish tartibi",
    "bankning qaror qabul qilish tartibi",
    "bankning qonuniy qarori va vakolatli bank jarayoni HumanDecision",
    "AuditEvent qaror tarixi va fuqaro feedback qayta ko'rib chiqish",
    "FINZANJIR signalni bankka ko'rib chiqish uchun yuboradi bank vakolatini almashtirmaydi",
    "risk indikatori avtomatik bloklash buyrug'i yoki aybdorlik isboti emas",
    "source validation normalization context signal evidence risk threshold case human review bank decision audit feedback",
)


class QueryExpander:
    """Local alias expansion that avoids firing on generic one-word overlaps."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def expand(self, query: str) -> tuple[str, ...]:
        original = query.strip()
        if not original:
            return ()

        expanded: list[str] = [original]
        raw_terms = set(tokenize(original))
        query_terms = set(meaningful_tokens(original))

        # Recognize colloquial citizen/funds protection questions and search
        # the canonical project concepts they refer to, even when the wording
        # does not repeat the corpus terminology.
        funds_terms = {
            "pul", "pulni", "pulini", "pulimni", "puldan", "pulga",
            "mablag", "mablaglar", "money", "fund", "funds",
        }
        protection_terms = {"himoya", "himoyalash", "asrash", "saqlash", "xavfsizlik", "xavfsiz", "protect", "protection"}
        card_terms = {"karta", "kartani", "kartasini", "kartalar", "kartadan", "card", "cards"}
        fraud_terms = {"firibgar", "firibgarlik", "firibgarlar", "fraud", "scam", "aldov"}
        has_funds = bool(raw_terms & funds_terms)
        has_card = bool(raw_terms & card_terms)
        has_fraud = bool(raw_terms & fraud_terms)
        is_citizen_protection = has_funds and bool(raw_terms & protection_terms)
        if is_citizen_protection:
            expanded.extend(_CITIZEN_PROTECTION_QUERY_HINTS)
        if has_card and (has_fraud or has_funds):
            expanded.extend(_MULTI_CARD_FRAUD_QUERY_HINTS)

        signal_terms = {"signal", "shubhali", "indikator", "risk"}
        process_terms = {"keyin", "song", "so'ng", "paydo", "topilsa", "topilgach", "bosqich", "bank"}
        if bool(raw_terms & signal_terms) and bool(raw_terms & process_terms):
            expanded.extend(_SIGNAL_PROCESS_QUERY_HINTS)

        # A broad identity question has little lexical content after stopword
        # removal. Do not let a detailed "how does it protect money?" question
        # fall back to broad mission/identity hints.
        if "finzanjir" in raw_terms and not is_citizen_protection and (
            len(query_terms) <= 1
            or bool(raw_terms & {"nima", "maqsad", "kerak", "loyiha"})
        ):
            expanded.extend(_IDENTITY_QUERY_HINTS)

        author_terms = {
            "muallif", "muallifi", "yaratuvchi", "asoschi", "biografiya",
            "tarjimai", "hayoti", "qiziqishlari", "motivatsiya", "yaratgan",
            "salamat", "smaylov", "ona", "onasi", "onasining", "mother", "мать", "анасы",
        }
        if raw_terms & author_terms:
            expanded.extend(_AUTHOR_QUERY_HINTS)

        alias_record_ids: dict[str, set[str]] = {}
        for record in self.index.records:
            for alias in record.aliases:
                for token in set(meaningful_tokens(alias)):
                    alias_record_ids.setdefault(token, set()).add(record.record_id)

        for record in self.index.records:
            for alias in record.aliases:
                alias_terms = set(meaningful_tokens(alias))
                if not alias_terms:
                    continue
                overlap = len(query_terms & alias_terms)
                exact_phrase = alias.casefold().strip() in original.casefold()
                unique_specific_term = (
                    len(query_terms) == 1
                    and "finzanjir" not in query_terms
                    and len(alias_record_ids.get(next(iter(query_terms)), set())) == 1
                    and bool(query_terms & alias_terms)
                )
                if exact_phrase or overlap >= 2 or unique_specific_term:
                    expanded.extend(record.aliases)
                    break

        return tuple(dict.fromkeys(term for term in expanded if term))


class Reranker:
    """Small, bounded alias-aware rerank bonus; no unbounded exact-match boost."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index

    def rerank(self, query: str, results: tuple[RetrievalResult, ...]) -> tuple[RetrievalResult, ...]:
        normalized_query = " ".join(tokenize(query))
        query_terms = set(meaningful_tokens(query))
        scored = []
        for result in results:
            record = self.index.get_record(result.record_id)
            bonus = 0.0
            if record:
                for alias in record.aliases:
                    normalized_alias = " ".join(tokenize(alias))
                    alias_terms = set(meaningful_tokens(alias))
                    if normalized_alias and (
                        normalized_alias in normalized_query
                        or normalized_query in normalized_alias
                    ):
                        bonus = max(bonus, 0.20)
                    elif len(query_terms & alias_terms) >= 2 and alias_terms:
                        overlap = len(query_terms & alias_terms) / len(alias_terms)
                        bonus = max(bonus, min(0.12, 0.12 * overlap))
            scored.append(replace(result, score=min(1.0, result.score + bonus)))
        return tuple(sorted(scored, key=lambda item: (-item.score, item.record_id)))
