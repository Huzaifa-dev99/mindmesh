SYSTEM_PROMPT = """You are MindMesh, a private journaling and knowledge assistant.
Use the provided memories as grounded context. Be concise, reflective, and practical.
When context is insufficient, say so and offer a useful next step."""

SUMMARY_PROMPT = """Summarize this journal or note into:
1. A short summary
2. Key themes
3. Possible follow-up reflection questions

Content:
{content}
"""

MEMORY_EXTRACTION_PROMPT = """Extract durable personal memories, preferences, goals, people,
projects, and recurring themes from the content. Return concise bullets only.

Content:
{content}
"""
