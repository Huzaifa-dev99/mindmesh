import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.schemas.search import SearchResult
from app.services.agents import (
    PromptTemplate,
    RetrievedContext,
    SupervisorAgent,
    build_chat_history_summary,
    build_retrieval_query,
)


def test_chat_history_summary_uses_recent_role_labeled_messages():
    now = datetime.now(timezone.utc)
    messages = [
        SimpleNamespace(role="user", content="Older detail", created_at=now - timedelta(minutes=2)),
        SimpleNamespace(role="assistant", content="Previous answer", created_at=now - timedelta(minutes=1)),
    ]

    summary = build_chat_history_summary(messages)

    assert "user: Older detail" in summary
    assert "assistant: Previous answer" in summary


def test_retrieval_query_includes_question_and_chat_history():
    query = build_retrieval_query("What is the renewal risk?", "user: We discussed Acme renewal.")

    assert "What is the renewal risk?" in query
    assert "We discussed Acme renewal." in query


@pytest.mark.asyncio
async def test_supervisor_uses_notes_and_documents_context_with_chat_history():
    note_citation = SearchResult(
        source_type="note",
        source_id=uuid.uuid4(),
        score=0.82,
        title="Renewal note",
        snippet="Acme renewal risk is high.",
    )
    document_citation = SearchResult(
        source_type="document",
        source_id=uuid.uuid4(),
        score=0.76,
        title="Contract.pdf",
        snippet="The renewal date is June 30.",
    )
    fake_llm = FakeLLM()
    supervisor = SupervisorAgent.__new__(SupervisorAgent)
    supervisor.notes_agent = FakeKnowledgeAgent(
        RetrievedContext("notes", "[N1] Renewal note\nAcme renewal risk is high.", [note_citation], 0.82)
    )
    supervisor.documents_agent = FakeKnowledgeAgent(
        RetrievedContext("documents", "[D1] Contract.pdf\nThe renewal date is June 30.", [document_citation], 0.76)
    )
    supervisor.web_agent = None
    supervisor.llm = fake_llm
    supervisor.prompt = PromptTemplate.from_template(
        "History: {chat_history_summary}\nQuestion: {question}\nNotes: {notes_context}\nDocs: {documents_context}"
    )

    result = await supervisor.answer(
        uuid.uuid4(),
        "What should I do about the renewal?",
        5,
        uuid.uuid4(),
        "user: We were planning the Acme renewal.",
    )

    prompt = fake_llm.messages[0]["content"]
    assert result.route == "workspace"
    assert result.citations == [note_citation, document_citation]
    assert result.metadata["notes_context_count"] == 1
    assert result.metadata["documents_context_count"] == 1
    assert "We were planning the Acme renewal" in prompt
    assert "Acme renewal risk is high" in prompt
    assert "The renewal date is June 30" in prompt


class FakeKnowledgeAgent:
    def __init__(self, context: RetrievedContext):
        self.context = context

    async def retrieve_context(self, user_id, query, limit, conversation_id, chat_history_summary):
        assert "renewal" in query.lower()
        assert "Acme renewal" in chat_history_summary
        return self.context


class FakeLLM:
    def __init__(self):
        self.messages = []

    async def complete(self, messages, temperature=0.2):
        self.messages = messages
        return "Use the note risk and the document renewal date."
