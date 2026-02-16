"""
Unit tests for the Python LLM layer.

Tests embeddings and inference WITHOUT requiring the Rust kernel
(kernel_client and orchestrator are tested in integration).
"""

import math
import unittest

from .embeddings import EmbeddingEngine
from .inference import LLMInference


class TestEmbeddingEngine(unittest.TestCase):
    """Test the local hash-based embedding engine."""

    def setUp(self):
        self.engine = EmbeddingEngine(dim=64, backend="local")

    def test_backend_is_local(self):
        self.assertEqual(self.engine.backend, "local")

    def test_embed_returns_correct_dim(self):
        vec = self.engine.embed("hello world")
        self.assertEqual(len(vec), 64)

    def test_embed_is_deterministic(self):
        a = self.engine.embed("test input")
        b = self.engine.embed("test input")
        self.assertEqual(a, b)

    def test_embed_is_normalized(self):
        vec = self.engine.embed("some text here")
        norm = math.sqrt(sum(v * v for v in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_different_inputs_different_vectors(self):
        a = self.engine.embed("hello")
        b = self.engine.embed("goodbye")
        self.assertNotEqual(a, b)

    def test_similar_inputs_closer(self):
        """Similar texts should have higher cosine similarity than dissimilar."""
        a = self.engine.embed("the cat sat on the mat")
        b = self.engine.embed("the cat sat on the rug")
        c = self.engine.embed("quantum physics equations")

        def cosine(x, y):
            dot = sum(xi * yi for xi, yi in zip(x, y))
            nx = math.sqrt(sum(xi * xi for xi in x))
            ny = math.sqrt(sum(yi * yi for yi in y))
            return dot / (nx * ny) if nx > 0 and ny > 0 else 0

        sim_ab = cosine(a, b)
        sim_ac = cosine(a, c)
        # Similar sentences should be closer than dissimilar
        self.assertGreater(sim_ab, sim_ac)

    def test_embed_batch(self):
        texts = ["hello", "world", "test"]
        results = self.engine.embed_batch(texts)
        self.assertEqual(len(results), 3)
        for vec in results:
            self.assertEqual(len(vec), 64)

    def test_empty_string(self):
        vec = self.engine.embed("")
        self.assertEqual(len(vec), 64)
        # Empty string should produce a zero or near-zero vector
        # (no ngrams to hash)

    def test_custom_dim(self):
        engine = EmbeddingEngine(dim=32, backend="local")
        vec = engine.embed("test")
        self.assertEqual(len(vec), 32)


class TestLLMInference(unittest.TestCase):
    """Test the mock LLM inference backend."""

    def setUp(self):
        self.llm = LLMInference(backend="mock")

    def test_backend_is_mock(self):
        self.assertEqual(self.llm.backend, "mock")

    def test_generate_returns_string(self):
        result = self.llm.generate("hello world")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_generate_reason_keyword(self):
        result = self.llm.generate("please reason about this")
        self.assertIn("Analysis", result)

    def test_generate_summarize_keyword(self):
        result = self.llm.generate("summarize the findings")
        self.assertIn("Summary", result)

    def test_generate_contradiction_keyword(self):
        result = self.llm.generate("there is a contradiction here")
        self.assertIn("Contradiction", result)

    def test_generate_generic(self):
        result = self.llm.generate("hello")
        self.assertIn("Processed", result)

    def test_chat_returns_string(self):
        messages = [
            {"role": "user", "content": "analyze this pattern"},
        ]
        result = self.llm.chat(messages)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_chat_empty_messages(self):
        result = self.llm.chat([])
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
