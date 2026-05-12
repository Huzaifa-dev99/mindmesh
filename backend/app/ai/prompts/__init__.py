"""
Prompt management module.

This module handles prompt templates and management for different AI use cases.
It provides structured prompt engineering capabilities for consistent AI interactions.

Architecture:
- Template-based prompt generation
- Context-aware prompt building
- Prompt versioning and optimization
- Domain-specific prompt libraries (journaling, knowledge, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PromptType(Enum):
    """Types of prompts for different use cases."""
    JOURNAL_ANALYSIS = "journal_analysis"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    INSIGHT_GENERATION = "insight_generation"
    SEARCH_QUERY = "search_query"
    SUMMARIZATION = "summarization"


@dataclass
class PromptTemplate:
    """Template for AI prompts."""
    template: str
    variables: List[str]
    description: str
    version: str = "1.0"


class PromptBuilder(ABC):
    """Abstract base class for prompt builders."""

    @abstractmethod
    def build_prompt(self, **kwargs) -> str:
        """Build a complete prompt from template and variables."""
        pass


class JournalAnalysisPromptBuilder(PromptBuilder):
    """
    Prompt builder for journal entry analysis.

    Generates prompts for analyzing journal entries and extracting insights.
    """

    def __init__(self):
        self.template = PromptTemplate(
            template="""
            Analyze the following journal entry and provide insights:

            Entry: {entry_text}
            Date: {entry_date}
            Mood: {mood}

            Please provide:
            1. Key themes and topics
            2. Emotional patterns
            3. Potential insights or reflections
            4. Suggested actions or next steps

            Analysis:
            """,
            variables=["entry_text", "entry_date", "mood"],
            description="Analyzes journal entries for themes and insights",
            version="1.0"
        )

    def build_prompt(self, entry_text: str, entry_date: str, mood: str) -> str:
        """Build journal analysis prompt."""
        # TODO: Implement template substitution
        # TODO: Add context validation
        # TODO: Handle optional variables
        return self.template.template.format(
            entry_text=entry_text,
            entry_date=entry_date,
            mood=mood
        )


class KnowledgeExtractionPromptBuilder(PromptBuilder):
    """
    Prompt builder for knowledge extraction.

    Generates prompts for extracting structured knowledge from text.
    """

    def __init__(self):
        self.template = PromptTemplate(
            template="""
            Extract structured knowledge from the following text:

            Text: {input_text}
            Context: {context}

            Please identify:
            1. Key concepts and entities
            2. Relationships between concepts
            3. Important facts and insights
            4. Potential connections to existing knowledge

            Structured Knowledge:
            """,
            variables=["input_text", "context"],
            description="Extracts structured knowledge from text",
            version="1.0"
        )

    def build_prompt(self, input_text: str, context: str = "") -> str:
        """Build knowledge extraction prompt."""
        # TODO: Implement template substitution
        return self.template.template.format(
            input_text=input_text,
            context=context
        )


class PromptManager:
    """
    Manager for prompt templates and builders.

    This class manages different prompt builders and provides a unified
    interface for generating prompts for various AI use cases.
    """

    def __init__(self):
        self.builders: Dict[str, PromptBuilder] = {}
        self.templates: Dict[str, PromptTemplate] = {}
        # TODO: Initialize default builders

    def register_builder(self, name: str, builder: PromptBuilder):
        """Register a prompt builder."""
        self.builders[name] = builder

    def get_builder(self, name: str) -> Optional[PromptBuilder]:
        """Get a registered prompt builder."""
        return self.builders.get(name)

    def build_prompt(self, builder_name: str, **kwargs) -> str:
        """Build a prompt using a registered builder."""
        builder = self.get_builder(builder_name)
        if not builder:
            raise ValueError(f"Prompt builder '{builder_name}' not found")
        return builder.build_prompt(**kwargs)


# Global prompt manager instance
prompt_manager = PromptManager()