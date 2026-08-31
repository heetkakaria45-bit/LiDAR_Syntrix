"""
Smoke test for synthetic scene generation interface.
"""

import unittest

from src.common.interfaces import ISyntheticSceneGenerator
from src.common.mocks import MockSyntheticSceneGenerator
from src.common.types import PointCloudFrame


class TestSyntheticSceneSmoke(unittest.TestCase):
    """Verifies synthetic scene generation contract."""

    def test_mock_synthetic_generator_smoke(self) -> None:
        generator: ISyntheticSceneGenerator = MockSyntheticSceneGenerator()
        scene = generator.generate_scene("flat_road", num_points=400)

        self.assertIsInstance(scene, PointCloudFrame)
        self.assertEqual(scene.points.shape[1], 3)
        self.assertGreater(scene.num_points, 0)


if __name__ == "__main__":
    unittest.main()
