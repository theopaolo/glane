import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_images


class FetchImagesTest(unittest.TestCase):
    def test_saves_open_graph_image_and_updates_signet(self):
        with tempfile.TemporaryDirectory() as tmp:
            signets = Path(tmp).resolve() / "signets"
            images = Path(tmp).resolve() / "images"
            signets.mkdir()
            fiche = signets / "example.md"
            fiche.write_text('---\ntitle: Example\nextra:\n  url: "https://example.org/start"\n---\n')
            png = b"\x89PNG\r\n\x1a\nimage"
            with patch.object(fetch_images, "SIGNETS", signets), patch.object(fetch_images, "IMAGES", images), patch.object(
                fetch_images,
                "get",
                side_effect=[
                    ("https://example.org/redirected", b'<meta content="/cover.png" property="og:image">'),
                    ("https://example.org/cover.png", png),
                ],
            ) as get:
                fetch_images.main(str(fiche))

            self.assertEqual(get.call_args_list[1].args[0], "https://example.org/cover.png")
            self.assertEqual((images / "example.png").read_bytes(), png)
            self.assertIn('image: "/images/example.png"', fiche.read_text())
            self.assertIsNone(fetch_images.extension(b"<svg/>"))


if __name__ == "__main__":
    unittest.main()
