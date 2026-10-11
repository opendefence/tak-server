"""Check release consistency and the Zarf publishing commands without a registry."""

import os
import re
import shlex
import subprocess
import sys
import tempfile
import textwrap
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

    def test_zarf_publishing(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[1] / ".github/workflows/push_to_main.yml"
        ).read_text()
        step = workflow.split("      - name: Build, sign, and publish Zarf packages\n")[
            1
        ]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        stub = r"""
        python3() { "$TEST_PYTHON" "$@"; }
        zarf() {
          printf '%q ' "$@" >> "$COMMAND_LOG"
          printf '\n' >> "$COMMAND_LOG"
          if [[ "$1 $2" == 'package create' ]]; then
            for ((i = 0; i < ARCHIVE_COUNT; i++)); do
              touch "${@: -1}/zarf-package-test-$i.tar.zst"
            done
          fi
          [[ "$2" != "$FAIL_COMMAND" ]]
        }
        """
        image = "ghcr.io/opendefence/tak-server@sha256:" + "a" * 64
        for count, failure in ((1, ""), (0, ""), (2, ""), (1, "sign")):
            with self.subTest(archives=count, failure=failure):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / ".bumpversion.toml").write_text(
                        '[tool.bumpversion]\ncurrent_version = "5.8.92+261011"\n'
                    )
                    log = root / "commands"
                    result = subprocess.run(
                        ["bash", "-c", textwrap.dedent(stub) + script],
                        cwd=root,
                        env={
                            **os.environ,
                            "TEST_PYTHON": sys.executable,
                            "TAK_IMAGE": image,
                            "RUNNER_TEMP": tmp,
                            "GITHUB_STEP_SUMMARY": str(root / "summary"),
                            "COMMAND_LOG": str(log),
                            "ARCHIVE_COUNT": str(count),
                            "FAIL_COMMAND": failure,
                        },
                        capture_output=True,
                        text=True,
                    )
                    commands = [
                        shlex.split(line) for line in log.read_text().splitlines()
                    ]
                    published = [
                        cmd for cmd in commands if cmd[:2] == ["package", "publish"]
                    ]
                    if count != 1 or failure:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(published, [])
                        continue
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(len(commands), 16)
                    for index, (flavor, arch) in enumerate(
                        (flavor, arch)
                        for flavor in ("standalone", "integrated")
                        for arch in ("amd64", "arm64")
                    ):
                        create, sign, versioned, latest = commands[
                            index * 4 : index * 4 + 4
                        ]
                        self.assertEqual(
                            create[:-1],
                            [
                                "package",
                                "create",
                                ".",
                                "--architecture",
                                arch,
                                "--flavor",
                                flavor,
                                "--set",
                                f"TAK_IMAGE={image}",
                                "--confirm",
                                "--output",
                            ],
                        )
                        archive = str(Path(create[-1]) / "zarf-package-test-0.tar.zst")
                        self.assertEqual(
                            sign, ["package", "sign", archive, "--keyless", "--confirm"]
                        )
                        for command, tag in (
                            (versioned, f"5.8.92-261011-{flavor}"),
                            (latest, f"latest-{flavor}"),
                        ):
                            self.assertEqual(
                                command,
                                [
                                    "package",
                                    "publish",
                                    archive,
                                    "oci://ghcr.io/opendefence/zarf",
                                    "--tag",
                                    tag,
                                    "--confirm",
                                ],
                            )


if __name__ == "__main__":
    unittest.main()
