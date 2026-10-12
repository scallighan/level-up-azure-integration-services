"""Test the Azure-only Lab 0 preflight without Azure or GitHub access."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("check-prereqs.sh")
AZURE_STUB = """#!/bin/sh
case "$1" in
  account) echo "Workshop subscription" ;;
  bicep) echo "Bicep CLI available" ;;
  appservice) printf 'West US\\nWest US (Stage)\\n' ;;
  rest)
    if [ "${FAKE_REST_FAIL:-0}" = 1 ]; then
      echo "Azure permission denied" >&2
      exit 1
    fi
    quota='{"current":0,"limit":1}'
    printf '%s\\n' "${FAKE_QUOTA:-$quota}"
    ;;
  *) echo "Unexpected Azure command" >&2; exit 1 ;;
esac
"""
TERRAFORM_STUB = """#!/bin/sh
printf '{"terraform_version":"%s"}\\n' "${FAKE_TF_VERSION:-1.14.4}"
"""


class PrerequisiteTests(unittest.TestCase):
    def run_check(self, *args, **settings):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name, content in [("az", AZURE_STUB), ("terraform", TERRAFORM_STUB)]:
                stub = path / name
                stub.write_text(content)
                stub.chmod(0o700)
            for name in ["jq", "tr"]:
                (path / name).symlink_to(shutil.which(name))
            return subprocess.run(
                ["/bin/bash", str(SCRIPT), *args],
                capture_output=True,
                text=True,
                env={**os.environ, **settings, "PATH": str(path)},
                check=False,
            )

    def test_both_tracks_work_without_git_or_github_cli(self):
        for track in ["bicep", "terraform"]:
            with self.subTest(track=track):
                result = self.run_check(track, "westus")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"Ready for {track} in westus", result.stdout)

    def test_region_is_required(self):
        result = self.run_check("bicep")
        self.assertEqual(result.returncode, 2)
        self.assertIn("<azure-region>", result.stderr)

    def test_unsupported_region_is_rejected(self):
        result = self.run_check("bicep", "eastus")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WS1 is not available in eastus", result.stderr)

    def test_exhausted_quota_is_rejected(self):
        result = self.run_check("bicep", "westus", FAKE_QUOTA='{"current":1,"limit":1}')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No WS1 capacity remains in westus", result.stderr)

    def test_quota_uses_named_json_fields(self):
        result = self.run_check("bicep", "westus", FAKE_QUOTA='{"limit":3,\n"current":1}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 WS1 worker(s) available", result.stdout)

    def test_quota_api_errors_are_not_hidden(self):
        result = self.run_check("bicep", "westus", FAKE_REST_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Azure permission denied", result.stderr)
        self.assertIn("Unable to check WS1 quota", result.stderr)
        self.assertNotIn("No WS1 capacity", result.stderr)

    def test_missing_quota_is_rejected(self):
        result = self.run_check("bicep", "westus", FAKE_QUOTA="null")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Azure did not return WS1 quota", result.stderr)

    def test_incompatible_terraform_is_rejected(self):
        result = self.run_check("terraform", "westus", FAKE_TF_VERSION="1.13.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires Terraform 1.14.4; found 1.13.0", result.stderr)


if __name__ == "__main__":
    unittest.main()
