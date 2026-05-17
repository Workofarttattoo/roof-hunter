"""Unit tests for verification_image_sources (mocked HTTP)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from verification_image_sources import VerificationImageResult, fetch_best_verification_image  # noqa: E402


class VerificationImageSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._paths_to_clean: list[Path] = []

    def tearDown(self) -> None:
        for p in self._paths_to_clean:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

    @patch("verification_image_sources.fetch_google_static_satellite")
    @patch("verification_image_sources.fetch_oam_thumbnail_chip")
    def test_stops_after_oam(self, mock_oam, mock_g):
        dest = Path(__file__).resolve().parent / "oam_out.png"
        self._paths_to_clean.append(dest)
        mock_oam.return_value = VerificationImageResult(
            path=dest,
            source_id="oam_thumbnail",
            source_url="https://example/meta",
            license_note="CC-BY",
            content_type="image/png",
        )

        out = Path(__file__).resolve().parent / "_tmp_x.png"
        r = fetch_best_verification_image(1.0, 2.0, out_path=out)
        self.assertIsNotNone(r)
        self.assertEqual(r.source_id, "oam_thumbnail")
        mock_g.assert_not_called()

    @patch("verification_image_sources.fetch_google_static_satellite")
    @patch("verification_image_sources.fetch_oam_thumbnail_chip")
    def test_falls_back_google(self, mock_oam, mock_g):
        mock_oam.return_value = None
        dest = Path(__file__).resolve().parent / "g_out.png"
        self._paths_to_clean.append(dest)
        mock_g.return_value = VerificationImageResult(
            path=dest,
            source_id="google_static_satellite",
            source_url="google_static_maps:z20:640px@1.00000,2.00000",
            license_note="Google ToS",
            content_type="image/jpeg",
        )

        out_y = Path(__file__).resolve().parent / "_tmp_y.png"
        r = fetch_best_verification_image(1.0, 2.0, out_path=out_y)
        self.assertIsNotNone(r)
        self.assertEqual(r.source_id, "google_static_satellite")
        mock_g.assert_called_once()


if __name__ == "__main__":
    unittest.main()
