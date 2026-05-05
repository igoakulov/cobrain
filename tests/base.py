import os
import unittest
from pathlib import Path

TEST_VAULT = Path("test-vault").resolve()
START_DIR = Path.cwd()


class TestCase(unittest.TestCase):
    def setUp(self):
        (TEST_VAULT / ".cobrain").mkdir(parents=True, exist_ok=True)
        (TEST_VAULT / "topics").mkdir(parents=True, exist_ok=True)
        (TEST_VAULT / "sources" / "x" / "junk").mkdir(parents=True, exist_ok=True)
        (TEST_VAULT / "sources" / "chats" / "junk").mkdir(parents=True, exist_ok=True)
        (TEST_VAULT / ".cobrain" / "config").write_text(
            "x_oauth2_client_id=\nx_oauth2_client_secret=\n"
        )
        (TEST_VAULT / ".cobrain" / "vault.yaml").write_text("topics: []")

        os.chdir(TEST_VAULT)

    def tearDown(self):
        os.chdir(START_DIR)
        if (TEST_VAULT / ".cobrain" / "vault.yaml").exists():
            (TEST_VAULT / ".cobrain" / "vault.yaml").write_text("topics: []")
        for f in (TEST_VAULT / "sources" / "x").glob("*.yaml"):
            f.unlink()
        for f in (TEST_VAULT / "sources" / "chats").glob("*.md"):
            f.unlink()
