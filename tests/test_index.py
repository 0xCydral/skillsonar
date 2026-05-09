"""Tests for index utilities (no Ollama dependency)."""

from __future__ import annotations

import unittest

from opencode_router import index


class TestCosine(unittest.TestCase):
    def test_identical_vectors(self) -> None:
        self.assertAlmostEqual(index.cosine([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors(self) -> None:
        self.assertAlmostEqual(index.cosine([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_opposite_vectors(self) -> None:
        self.assertAlmostEqual(index.cosine([1.0, 0.0], [-1.0, 0.0]), -1.0)

    def test_zero_vector(self) -> None:
        self.assertEqual(index.cosine([0.0, 0.0], [1.0, 0.0]), 0.0)

    def test_different_magnitudes(self) -> None:
        # Cosine should ignore magnitude
        self.assertAlmostEqual(index.cosine([2.0, 0.0], [5.0, 0.0]), 1.0)


if __name__ == "__main__":
    unittest.main()
