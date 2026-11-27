"""Evidence selection and current FAQ indexing coverage."""

from pathlib import Path

from chatbot.knowledge.answering import answerable_items
from chatbot.knowledge.chunking import ChunkingConfig, chunk_document
from chatbot.knowledge.document_loader import load_document
from chatbot.models import FAQCitation, FAQItem


def item(heading: str, content: str, score: float = 0.7) -> FAQItem:
    return FAQItem(
        content=content,
        score=score,
        citation=FAQCitation(source_file="faq.md", document_title="FAQ", heading=heading),
    )


def test_answerable_items_keep_relevant_ranked_evidence() -> None:
    irrelevant = item("How can I book?", "Book through the website.")
    relevant = item("How can I cancel?", "A Booked booking can be cancelled.")
    assert answerable_items("How can I cancel my booking?", [irrelevant, relevant]) == [relevant]
    assert answerable_items("Can massage cure arthritis?", [irrelevant, relevant]) == []
    assert answerable_items("What is the refund policy?", [relevant]) == []


def test_answerable_items_limit_citations() -> None:
    matches = [item("Couple booking", "Couples can book together.") for _ in range(4)]
    assert len(answerable_items("Can I book for a couple?", matches)) == 2


def test_unknown_couples_facilities_can_use_explicitly_unknown_faq() -> None:
    evidence = item(
        "Do you have private couples rooms?",
        "Room type and couples facilities are not documented.",
    )
    assert answerable_items("Do you have private couples rooms?", [evidence]) == [evidence]


def test_current_faq_chunks_only_documented_information() -> None:
    root = Path(__file__).resolve().parents[3]
    document = load_document(root / "docs/knowledge/faq.md")
    chunks = chunk_document(document, ChunkingConfig())
    assert document.document_id == "general-faq"
    assert document.category == "faq"
    assert len(chunks) == 7
    assert all(chunk.document_id == "general-faq" for chunk in chunks)
    text = "\n".join(chunk.content for chunk in chunks).casefold()
    assert "cancellation fee or notice-period policy is not documented" in text
    assert "room type and couples facilities are not documented" in text
    assert "medical guidance" in text
