"""Keep the vendor release used by PR validation and publishing in sync."""

import re
import unittest
from pathlib import Path


class WorkflowReleaseTest(unittest.TestCase):
    def test_tak_release_matches(self) -> None:
        workflows = Path(__file__).resolve().parents[1] / ".github/workflows"
        releases = []
        for name in ("pull_request.yml", "push_to_main.yml"):
            path = workflows / name
            matches = re.findall(r"^  TAK_RELEASE: (\S+)$", path.read_text(), re.M)
            self.assertEqual(len(matches), 1, f"Expected one TAK_RELEASE in {path}")
            releases.append(matches[0])
        self.assertEqual(releases[0], releases[1])


if __name__ == "__main__":
    unittest.main()
