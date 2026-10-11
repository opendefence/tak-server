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

    def test_kind_reuses_tested_image(self) -> None:
        taskfile = (Path(__file__).resolve().parents[1] / "Taskfile.yaml").read_text()
        task = taskfile.split("  image:\n", 1)[1].split("  tak:\n", 1)[0]
        script = textwrap.dedent(
            task.split("      - |\n", 1)[1].split("      - ", 1)[0]
        ).replace("{{.TAK_IMAGE | shellQuote}}", "localhost/tak-server:local")
        stub = r"""
        docker() {
          printf '%s\n' "$*" >> "$COMMAND_LOG"
          if [ "$1 $2" = 'image tag' ]; then
            [ "$3" = "$TAK_TEST_IMAGE" ] && [ "$MISSING_IMAGE" = 'false' ]
          fi
        }
        """
        for image, missing in (
            ("sha256:test", "false"),
            ("sha256:test", "true"),
            ("", "false"),
        ):
            with (
                self.subTest(image=image, missing=missing),
                tempfile.TemporaryDirectory() as tmp,
            ):
                log = Path(tmp) / "commands"
                result = subprocess.run(
                    ["bash", "-c", textwrap.dedent(stub) + script],
                    env={
                        **os.environ,
                        "TAK_TEST_IMAGE": image,
                        "MISSING_IMAGE": missing,
                        "COMMAND_LOG": str(log),
                    },
                    capture_output=True,
                    text=True,
                )
                commands = log.read_text().splitlines()
                if image:
                    self.assertEqual(
                        commands, [f"image tag {image} localhost/tak-server:local"]
                    )
                    self.assertEqual(
                        result.returncode == 0, missing == "false", result.stderr
                    )
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(
                        "buildx build --load -t localhost/tak-server:local .", commands
                    )

    def test_kind_imports_only_the_tested_platform(self) -> None:
        taskfile = (Path(__file__).resolve().parents[1] / "Taskfile.yaml").read_text()
        task = taskfile.split("  image:\n", 1)[1].split("  tak:\n", 1)[0]
        script = textwrap.dedent(task.split("      - ", 2)[2].removeprefix("|\n"))
        script = script.replace(
            "{{.TAK_IMAGE | shellQuote}}", "localhost/tak-server:local"
        )
        script = script.replace("{{.TAK_CLUSTER_NAME | shellQuote}}", "test-cluster")
        stub = r"""
        docker() {
          printf '%q ' "$@" >> "$COMMAND_LOG"
          printf '\n' >> "$COMMAND_LOG"
          case "$1 ${2:-}" in
            'info --format')
              if [ "$PROVIDER" = containerd ]; then
                printf '%s\n' '[["driver-type","io.containerd.snapshotter.v1"]]'
              fi ;;
            'image inspect')
              [ "$FAIL_COMMAND" != inspect ] || return 1
              printf '%s\n' "$IMAGE_PLATFORM" ;;
            'image save')
              [ "$FAIL_COMMAND" != save ] || return 1
              [ "$3" = --platform ] && [ "$4" = "$IMAGE_PLATFORM" ] || return 1
              [ "$5" = --output ] && [ "$7" = localhost/tak-server:local ] || return 1
              printf '%s\n' "$IMAGE_PLATFORM" > "$6" ;;
          esac
        }
        kind() {
          printf '%q ' "$@" >> "$COMMAND_LOG"
          printf '\n' >> "$COMMAND_LOG"
          [ "$3 $4" = '--name test-cluster' ] || return 1
          if [ "$PROVIDER" != containerd ]; then
            [ "$2 $5" = 'docker-image localhost/tak-server:local' ]
          else
            # Unfiltered multi-platform exports reproduce the missing-digest failure.
            [ "$2" = image-archive ] && [ "$(cat "$5")" = "$IMAGE_PLATFORM" ] || return 1
            [ "$FAIL_COMMAND" != load ]
          fi
        }
        """
        for provider, platform, failure in (
            ("containerd", "linux/amd64", ""),
            ("containerd", "linux/arm64", ""),
            ("containerd", "linux/amd64", "inspect"),
            ("containerd", "linux/amd64", "save"),
            ("containerd", "linux/amd64", "load"),
            ("classic", "linux/amd64", ""),
            ("Podman", "linux/arm64", ""),
        ):
            with (
                self.subTest(provider=provider, platform=platform, failure=failure),
                tempfile.TemporaryDirectory(prefix="kind import ") as tmp,
            ):
                log = Path(tmp) / "commands"
                result = subprocess.run(
                    ["bash", "-ec", textwrap.dedent(stub) + script],
                    env={
                        **os.environ,
                        "TMPDIR": tmp,
                        "COMMAND_LOG": str(log),
                        "PROVIDER": provider,
                        "IMAGE_PLATFORM": platform,
                        "FAIL_COMMAND": failure,
                    },
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode == 0, not failure, result.stderr)
                commands = [shlex.split(line) for line in log.read_text().splitlines()]
                if failure in {"inspect", "save"}:
                    self.assertFalse(any(cmd[0] == "load" for cmd in commands))
                self.assertEqual(list(Path(tmp).iterdir()), [log])

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
