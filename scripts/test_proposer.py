import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import proposer


class ProposerTest(unittest.TestCase):
    def test_writes_signet_and_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            signets = Path(tmp).resolve()
            (signets / "deja.md").write_text("---\nextra:\n  url: https://deja.org/\n---\n")
            (signets / "cafe-creme.md").write_text("---\n---\n")
            payload = {
                "titre": 'Café\n"crème"',
                "url": "https://example.org/?a=1&b=2",
                "categorie": "design",
                "francophone": True,
                "tags": ["css", "Ada-George-Sand", "2024", "css"],
                "description": "Utile. <script>alert(1)</script>",
            }
            with patch.object(proposer, "SIGNETS", signets), patch.object(proposer, "ROOT", signets.parent), redirect_stdout(StringIO()):
                proposer.main(payload)
                for bad in ({"url": "javascript:alert(1)"}, {"url": "http://www.deja.org"}, {"categorie": "francophone"}, {"titre": " "}):
                    with self.assertRaises(ValueError, msg=bad):
                        proposer.main(payload | bad)

            self.assertEqual(
                (signets / "cafe-creme-2.md").read_text(),
                '---\ntitle: "Café \\"crème\\""\nextra:\n  url: "https://example.org/?a=1&b=2"\n'
                'taxonomies:\n  category: [design, francophone]\n  tags: ["css", "ada-george-sand", "2024"]\n'
                "---\n\nUtile. &lt;script>alert(1)&lt;/script>\n",
            )


if __name__ == "__main__":
    unittest.main()
