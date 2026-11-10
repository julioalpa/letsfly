import os
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from config.env import load_dotenv


class LoadDotenvTests(SimpleTestCase):
    def setUp(self):
        self._saved = dict(os.environ)
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".env"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)
        self.tmp.cleanup()

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def test_loads_plain_quoted_and_export_lines(self):
        os.environ.pop("ENV_TEST_A", None)
        os.environ.pop("ENV_TEST_B", None)
        os.environ.pop("ENV_TEST_C", None)
        self.write('# comentario\nENV_TEST_A=abc123\nexport ENV_TEST_B="con espacios"\nENV_TEST_C=\'x\'\n')
        load_dotenv(self.path)
        self.assertEqual(os.environ["ENV_TEST_A"], "abc123")
        self.assertEqual(os.environ["ENV_TEST_B"], "con espacios")
        self.assertEqual(os.environ["ENV_TEST_C"], "x")

    def test_existing_environment_wins(self):
        os.environ["ENV_TEST_A"] = "desde-shell"
        self.write("ENV_TEST_A=desde-archivo\n")
        load_dotenv(self.path)
        self.assertEqual(os.environ["ENV_TEST_A"], "desde-shell")

    def test_missing_file_is_ignored(self):
        load_dotenv(Path(self.tmp.name) / "no-existe")  # no debe lanzar error
