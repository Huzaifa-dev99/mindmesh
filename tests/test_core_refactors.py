import os
import unittest
from datetime import datetime, timezone


REQUIRED_ENV = {
    "S3_ENDPOINT_URL": "http://127.0.0.1:9000",
    "S3_BUCKET": "test-bucket",
    "S3_PREFIX": "pdf/",
    "CHUNK_SIZE": "1000",
    "CHUNK_OVERLAP": "200",
    "QDRANT_URL": "http://127.0.0.1:6333",
    "QDRANT_COLLECTION_NAME": "documents",
    "QDRANT_DISTANCE": "COSINE",
    "EMBEDDING_MODEL_NAME": "sentence-transformers/all-MiniLM-L6-v2",
    "EMBEDDING_DIMENSION": "384",
    "CONTENT_PAYLOAD_KEY": "page_content",
    "METADATA_PAYLOAD_KEY": "metadata",
    "GROQ_MODEL": "llama-3.1-8b-instant",
    "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
    "GROQ_MAX_TOKENS": "1024",
}

for name, value in REQUIRED_ENV.items():
    os.environ.setdefault(name, value)

from app.core.serialization import serialize_datetime
from app.core.storage import document_file_type, list_document_objects, list_pdf_objects
from app.services.ai_settings import _normalize_base_url
from app.services.document_storage import _next_version, _safe_document_filename, _safe_pdf_filename, parse_tags
from app.services.preprocessing import _page_number
from app.services.retrieval import _retrieval_filter


class FakePaginator:
    def paginate(self, **kwargs):
        return [
            {
                "Contents": [
                    {"Key": "pdf/a.pdf"},
                    {"Key": "pdf/b.PDF"},
                    {"Key": "docs/c.docx"},
                    {"Key": "slides/d.pptx"},
                    {"Key": "notes/e.txt"},
                    {"Key": "pdf/readme.txt"},
                    {"Key": "pdf/image.png"},
                ]
            }
        ]


class FakeS3Client:
    def get_paginator(self, name):
        self.paginator_name = name
        return FakePaginator()


class CoreRefactorTests(unittest.TestCase):
    def test_base_url_normalization_handles_malformed_local_urls(self):
        self.assertEqual(
            _normalize_base_url(
                "openai",
                "https://http://127.0.0.1:1234//v1/chat/completions",
            ),
            "http://127.0.0.1:1234/v1",
        )

    def test_parse_tags_deduplicates_and_trims(self):
        self.assertEqual(parse_tags("HR, policy, HR, , onboarding"), ["HR", "policy", "onboarding"])

    def test_safe_pdf_filename_normalizes_extension(self):
        self.assertEqual(_safe_pdf_filename("../Employee Handbook.pdf"), "Employee Handbook.pdf")

    def test_safe_document_filename_preserves_supported_extension(self):
        self.assertEqual(_safe_document_filename("../Employee Handbook.docx"), "Employee Handbook.docx")

    def test_document_file_type_maps_supported_extensions(self):
        self.assertEqual(document_file_type("deck.pptx"), "pptx")

    def test_next_version_ignores_non_numeric_versions(self):
        self.assertEqual(_next_version([{"document_version": "01"}, {"document_version": "draft"}]), "02")

    def test_serialize_datetime_returns_iso_format(self):
        value = datetime(2026, 5, 18, 10, 30, tzinfo=timezone.utc)
        self.assertEqual(serialize_datetime(value), "2026-05-18T10:30:00+00:00")

    def test_list_document_objects_filters_supported_document_keys(self):
        objects = list_document_objects(FakeS3Client(), bucket="test-bucket", prefix="pdf/")
        self.assertEqual(
            [item["Key"] for item in objects],
            ["pdf/a.pdf", "pdf/b.PDF", "docs/c.docx", "slides/d.pptx", "notes/e.txt", "pdf/readme.txt"],
        )

    def test_list_pdf_objects_keeps_backward_compatible_name(self):
        objects = list_pdf_objects(FakeS3Client(), bucket="test-bucket", prefix="pdf/")
        self.assertEqual(len(objects), 6)

    def test_docling_page_number_extraction(self):
        metadata = {
            "dl_meta": {
                "doc_items": [
                    {"prov": [{"page_no": 3}]},
                    {"prov": [{"page_no": 2}]},
                ]
            }
        }
        self.assertEqual(_page_number(metadata), 2)

    def test_retrieval_filter_supports_documents_and_tags(self):
        qdrant_filter = _retrieval_filter(document_ids=["doc-1"], tags=["policy"])
        self.assertEqual(len(qdrant_filter.must), 2)


if __name__ == "__main__":
    unittest.main()
