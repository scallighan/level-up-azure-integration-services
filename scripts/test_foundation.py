"""Test Lab 0 helper actions without signing in or deploying Azure resources."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
COMMAND_STUB = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

command = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a") as log:
    log.write(json.dumps({
        "command": command, "args": args,
        "inputs": {key: value for key, value in os.environ.items()
                   if key.startswith("TF_VAR_")},
    }) + "\\n")
if os.environ.get("FAIL_COMMAND") == command + " " + " ".join(args[:2]):
    print("Mock command failed", file=sys.stderr)
    sys.exit(1)
if command == "az":
    if args[:2] == ["account", "show"] and os.environ.get("NEEDS_LOGIN") == "1":
        if not Path(os.environ["LOGIN_MARKER"]).exists():
            sys.exit(1)
    if args[0] == "login":
        Path(os.environ["LOGIN_MARKER"]).touch()
    elif args[:2] == ["account", "show"] and "--query" in args:
        print(os.environ.get("PRINCIPAL_TYPE", "user"))
    elif args[:3] == ["ad", "signed-in-user", "show"]:
        print(os.environ.get("PUBLISHER_ID", "00000000-0000-0000-0000-000000000003"))
    elif args[:2] == ["appservice", "list-locations"]:
        print("West US")
    elif args[0] == "rest":
        print('{"current":0,"limit":10}')
    elif args[:3] == ["deployment", "sub", "show"]:
        print(os.environ.get("HANDOFF", '{"resource_group_name":"rg-demo"}'))
elif command == "terraform":
    if args[0] == "version":
        print('{"terraform_version":"1.14.4"}')
    elif args[1] == "output":
        print(os.environ.get("HANDOFF", '{"resource_group_name":"rg-demo"}'))
"""


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ["foundation.sh", "check-prereqs.sh"]:
            shutil.copyfile(ROOT / "scripts" / name, scripts / name)
        shutil.copyfile(ROOT / ".env.example", self.root / ".env.example")
        tools = self.root / "bin"
        tools.mkdir()
        for name in ["az", "terraform"]:
            stub = tools / name
            stub.write_text(COMMAND_STUB)
            stub.chmod(0o700)
        self.log = self.root / "commands.jsonl"
        self.environment = {
            **os.environ,
            "PATH": f"{tools}:{os.environ['PATH']}",
            "COMMAND_LOG": str(self.log),
            "LOGIN_MARKER": str(self.root / "logged-in"),
        }

    def write_config(self, group=""):
        content = (ROOT / ".env.example").read_text()
        for name, value in {
            "AZURE_SUBSCRIPTION_ID": "subscription-demo",
            "WORKSHOP_PREFIX": "demo",
            "EXISTING_RESOURCE_GROUP_NAME": group,
            "FOUNDATION_RESOURCE_GROUP_NAME": "later-lab-group",
            "WORKSHOP_PUBLISHER_PRINCIPAL_ID": "00000000-0000-0000-0000-000000000003",
        }.items():
            content = content.replace(f'{name}=""', f'{name}="{value}"')
        (self.root / ".env").write_text(content)

    def run_helper(self, action, track="bicep", answers="", **settings):
        return subprocess.run(
            ["/bin/bash", str(self.root / "scripts" / "foundation.sh"), action, track],
            cwd=self.root / "bin",
            input=answers,
            capture_output=True,
            text=True,
            env={**self.environment, **settings},
            check=False,
        )

    def commands(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_setup_creates_config_and_checks_both_tracks_without_deploying(self):
        for track in ["bicep", "terraform"]:
            with self.subTest(track=track):
                result = self.run_helper("setup", track, "subscription-demo\ndemo\n\n\ny\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                config = (self.root / ".env").read_text()
                self.assertIn("WORKSHOP_PREFIX=demo", config)
                self.assertIn("AZURE_LOCATION=westus", config)
                self.assertIn("WORKSHOP_PUBLISHER_PRINCIPAL_ID=00000000-0000-0000-0000-000000000003", config)
                registrations = [
                    call for call in self.commands()
                    if call["args"][:2] == ["provider", "register"]
                ]
                self.assertEqual(len(registrations), 8)
                self.assertFalse(any(
                    call["args"][:1] == ["deployment"] or "apply" in call["args"]
                    for call in self.commands()
                ))
                self.log.unlink()

    def test_setup_preserves_existing_group_and_later_settings(self):
        self.write_config("existing-group")
        result = self.run_helper("setup", answers="\n\n\n\ny\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = (self.root / ".env").read_text()
        self.assertIn("EXISTING_RESOURCE_GROUP_NAME=existing-group", config)
        self.assertIn('FOUNDATION_RESOURCE_GROUP_NAME="later-lab-group"', config)
        self.assertTrue(any(
            call["args"][:2] == ["group", "show"]
            and "existing-group" in call["args"] for call in self.commands()
        ))

    def test_setup_logs_in_when_needed(self):
        self.write_config()
        result = self.run_helper("setup", answers="\n\n\n\ny\n", NEEDS_LOGIN="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(call["args"][0] == "login" for call in self.commands()))

    def test_setup_persists_missing_keys_for_subsequent_actions(self):
        for track in ["bicep", "terraform"]:
            for missing_keys in [
                {"EXISTING_RESOURCE_GROUP_NAME"},
                {
                    "AZURE_SUBSCRIPTION_ID", "WORKSHOP_PREFIX",
                    "AZURE_LOCATION", "EXISTING_RESOURCE_GROUP_NAME",
                },
            ]:
                with self.subTest(track=track, missing_keys=missing_keys):
                    self.write_config()
                    config_path = self.root / ".env"
                    config_path.write_text("".join(
                        line for line in config_path.read_text().splitlines(keepends=True)
                        if line.split("=", 1)[0] not in missing_keys
                    ))
                    result = self.run_helper(
                        "setup", track, "subscription-demo\ndemo\nwestus\nexisting-group\ny\n"
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(
                        'FOUNDATION_RESOURCE_GROUP_NAME="later-lab-group"',
                        config_path.read_text(),
                    )
                    loaded = subprocess.run(
                        ["/bin/bash", "-c",
                         'source .env; printf "%s" "$TF_VAR_existing_resource_group_name"'],
                        cwd=self.root, capture_output=True, text=True, check=True,
                    )
                    self.assertEqual(loaded.stdout, "existing-group")
                    for action in ["preview", "deploy"]:
                        self.log.unlink()
                        result = self.run_helper(action, track)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        calls = self.commands()
                        if track == "bicep":
                            deployment = next(
                                call for call in calls
                                if ("what-if" if action == "preview" else "create")
                                in call["args"]
                            )
                            self.assertIn(
                                "existingResourceGroupName=existing-group", deployment["args"]
                            )
                        else:
                            deployment = next(
                                call for call in calls
                                if ("plan" if action == "preview" else "apply")
                                in call["args"]
                            )
                            self.assertEqual(
                                deployment["inputs"]["TF_VAR_existing_resource_group_name"],
                                "existing-group",
                            )

    def test_missing_existing_group_stops_without_creating_or_saving_changes(self):
        self.write_config()
        before = (self.root / ".env").read_text()
        result = self.run_helper(
            "setup", answers="\n\n\nmissing-group\n", FAIL_COMMAND="az group show"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Mock command failed", result.stderr)
        self.assertEqual((self.root / ".env").read_text(), before)
        self.assertFalse(any("register" in call["args"] for call in self.commands()))

    def test_preview_runs_only_review_commands_with_loaded_inputs(self):
        self.write_config("existing-group")
        for track in ["bicep", "terraform"]:
            with self.subTest(track=track):
                result = self.run_helper("preview", track)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.commands()
                self.assertFalse(any("create" in call["args"] or "apply" in call["args"]
                                     for call in calls))
                if track == "bicep":
                    preview = next(call for call in calls if "what-if" in call["args"])
                    self.assertIn("existingResourceGroupName=existing-group", preview["args"])
                    self.assertIn("prefix=demo", preview["args"])
                    self.assertIn("publisherPrincipalId=00000000-0000-0000-0000-000000000003", preview["args"])
                else:
                    terraform = [call for call in calls if call["command"] == "terraform"]
                    self.assertEqual(
                        [call["args"][1] for call in terraform],
                        ["init", "fmt", "validate", "plan"],
                    )
                    self.assertEqual(terraform[-1]["inputs"]["TF_VAR_prefix"], "demo")
                    self.assertEqual(
                        terraform[-1]["inputs"]["TF_VAR_publisher_principal_id"],
                        "00000000-0000-0000-0000-000000000003",
                    )
                    self.assertEqual(
                        terraform[-1]["inputs"]["TF_VAR_existing_resource_group_name"],
                        "existing-group",
                    )
                self.log.unlink()

    def test_deploy_saves_handoff_without_auto_approving_terraform(self):
        self.write_config()
        for track in ["bicep", "terraform"]:
            with self.subTest(track=track):
                result = self.run_helper("deploy", track)
                self.assertEqual(result.returncode, 0, result.stderr)
                handoff = json.loads((self.root / "foundation.deployment.json").read_text())
                self.assertEqual(handoff["resource_group_name"], "rg-demo")
                calls = self.commands()
                self.assertFalse(any("-auto-approve" in call["args"] for call in calls))
                if track == "bicep":
                    deployment = next(call for call in calls if "create" in call["args"])
                    self.assertIn("foundation-demo", deployment["args"])
                else:
                    self.assertTrue(any("apply" in call["args"] for call in calls))
                self.log.unlink()

    def test_deployment_failure_preserves_previous_handoff(self):
        self.write_config()
        handoff = self.root / "foundation.deployment.json"
        handoff.write_text('{"resource_group_name":"previous-group"}')
        result = self.run_helper(
            "deploy", "terraform",
            FAIL_COMMAND="terraform -chdir=labs/00-foundation/iac/terraform apply",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Mock command failed", result.stderr)
        self.assertEqual(json.loads(handoff.read_text())["resource_group_name"], "previous-group")
        self.assertFalse(any("output" in call["args"] for call in self.commands()))

    def test_invalid_handoff_preserves_previous_file_and_removes_temporary_output(self):
        self.write_config()
        handoff = self.root / "foundation.deployment.json"
        handoff.write_text('{"resource_group_name":"previous-group"}')
        result = self.run_helper("deploy", HANDOFF="null")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid foundation handoff", result.stderr)
        self.assertEqual(json.loads(handoff.read_text())["resource_group_name"], "previous-group")
        self.assertEqual(list(self.root.glob(".foundation.deployment.*")), [])

    def test_missing_or_invalid_inputs_stop_before_azure_commands(self):
        result = self.run_helper("preview")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing .env", result.stderr)
        result = self.run_helper("setup", answers="subscription-demo\nINVALID\n\n\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lowercase alphanumeric prefix", result.stderr)
        self.assertEqual(self.commands(), [])

    def test_publisher_decline_preserves_config_and_stops_before_registration(self):
        self.write_config()
        before = (self.root / ".env").read_text()
        result = self.run_helper("setup", answers="\n\n\n\nn\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Publisher selection cancelled", result.stderr)
        self.assertEqual((self.root / ".env").read_text(), before)
        self.assertFalse(any("register" in call["args"] for call in self.commands()))

    def test_setup_rejects_application_login_or_invalid_user_object_id(self):
        self.write_config()
        for settings in [{"PRINCIPAL_TYPE": "servicePrincipal"}, {"PUBLISHER_ID": "not-a-uuid"}]:
            with self.subTest(settings=settings):
                result = self.run_helper("setup", answers="\n\n\n\ny\n", **settings)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any("register" in call["args"] for call in self.commands()))

    def test_missing_publisher_requires_setup_before_preview_or_deploy(self):
        self.write_config()
        config = self.root / ".env"
        config.write_text(config.read_text().replace(
            'WORKSHOP_PUBLISHER_PRINCIPAL_ID="00000000-0000-0000-0000-000000000003"',
            'WORKSHOP_PUBLISHER_PRINCIPAL_ID=""',
        ))
        for action in ("preview", "deploy"):
            result = self.run_helper(action)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing publisher user selection", result.stderr)
            self.assertFalse(any(
                call["args"][:1] == ["deployment"] for call in self.commands()
            ))


if __name__ == "__main__":
    unittest.main()
