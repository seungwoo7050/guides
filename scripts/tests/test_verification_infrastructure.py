from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_cng
import check_app_profiles
import dependency_receipt
import export_bundle
import process_runner
import source_fingerprint
import source_manifest
import verify
import workspace_contract


class AppProfileContractTests(unittest.TestCase):
    def fake_config(self, profile: str) -> dict[str, object]:
        expected = check_app_profiles.PROFILE_EXPECTATIONS[profile]
        return {
            "name": expected["name"],
            "version": "1.0.0",
            "scheme": expected["scheme"],
            "android": {
                "package": expected["application_id"],
                "versionCode": 1,
            },
            "ios": {
                "bundleIdentifier": expected["application_id"],
                "buildNumber": "1",
            },
            "runtimeVersion": {"policy": "appVersion"},
            "updates": {"enabled": False},
            "extra": {
                "fieldNotes": {
                    "buildProfile": profile,
                    "appIdentityLabel": expected["app_identity_label"],
                    "backendEnvironmentLabel": expected[
                        "backend_environment_label"
                    ],
                }
            },
            "plugins": ["expo-router"],
        }

    def test_three_profiles_are_unique_and_unset_is_development(self) -> None:
        configs = {
            profile: self.fake_config(profile)
            for profile in check_app_profiles.PUBLIC_PROFILES
        }
        summaries = check_app_profiles.validate_profile_set(
            configs, self.fake_config("development")
        )
        self.assertEqual(
            [summary["profile"] for summary in summaries],
            list(check_app_profiles.PUBLIC_PROFILES),
        )
        self.assertEqual(len({summary["scheme"] for summary in summaries}), 3)
        with self.assertRaisesRegex(
            check_app_profiles.AppProfileContractError,
            "unset FIELD_NOTES_BUILD_PROFILE",
        ):
            check_app_profiles.validate_profile_set(
                configs, self.fake_config("preview")
            )

    def test_profile_contract_rejects_url_secret_update_and_identity_collision(self) -> None:
        invalid_cases: list[tuple[str, object]] = []
        url = self.fake_config("development")
        url["extra"] = {"fieldNotes": {
            **url["extra"]["fieldNotes"],  # type: ignore[index]
            "backendUrl": "https://example.invalid",
        }}
        invalid_cases.append(("URL value", url))

        secret = self.fake_config("development")
        secret["extra"] = {
            **secret["extra"],  # type: ignore[arg-type]
            "accessToken": "redacted-but-still-public",
        }
        invalid_cases.append(("secret-like public key", secret))

        update = self.fake_config("development")
        update["updates"] = {"enabled": False, "channel": "production"}
        invalid_cases.append(("routing keys", update))
        for expected_message, config in invalid_cases:
            with self.subTest(expected_message=expected_message), self.assertRaisesRegex(
                check_app_profiles.AppProfileContractError, expected_message
            ):
                check_app_profiles.validate_public_config("development", config)

        configs = {
            profile: self.fake_config(profile)
            for profile in check_app_profiles.PUBLIC_PROFILES
        }
        configs["preview"]["scheme"] = configs["development"]["scheme"]  # type: ignore[index]
        with self.assertRaisesRegex(
            check_app_profiles.AppProfileContractError, "scheme: expected"
        ):
            check_app_profiles.validate_profile_set(
                configs, self.fake_config("development")
            )

    def test_dev_client_generated_scheme_is_development_only(self) -> None:
        def raw(value: object) -> dict[str, object]:
            return {
                "plugins": [
                    "expo-router",
                    ["expo-dev-client", {"addGeneratedScheme": value}],
                ]
            }

        self.assertTrue(
            check_app_profiles.validate_raw_profile_config(
                "development", raw(True)
            )
        )
        self.assertFalse(
            check_app_profiles.validate_raw_profile_config("preview", raw(False))
        )
        self.assertFalse(
            check_app_profiles.validate_raw_profile_config("production", raw(False))
        )
        for profile, value in (("development", False), ("preview", True)):
            with self.subTest(profile=profile), self.assertRaisesRegex(
                check_app_profiles.AppProfileContractError,
                "addGeneratedScheme",
            ):
                check_app_profiles.validate_raw_profile_config(profile, raw(value))

    def test_dynamic_config_selects_exact_profiles_and_rejects_unknown(self) -> None:
        script = """
const factory = require('./app.config.js');
const profiles = [undefined, 'development', 'preview', 'production'].map((profile) => {
  const env = profile === undefined ? {} : { FIELD_NOTES_BUILD_PROFILE: profile };
  const config = factory.resolveConfig(env);
  const devClient = config.plugins.find((entry) =>
    Array.isArray(entry) && entry[0] === 'expo-dev-client');
  return [
    profile ?? 'unset',
    config.extra.fieldNotes.buildProfile,
    config.extra.fieldNotes.backendEnvironmentLabel,
    config.scheme,
    devClient[1].addGeneratedScheme,
  ];
});
let rejected = false;
try { factory.resolveConfig({ FIELD_NOTES_BUILD_PROFILE: 'wrong' }); } catch { rejected = true; }
process.stdout.write(JSON.stringify({ profiles, rejected }));
"""
        result = process_runner.run_process(
            ["node", "-e", script],
            cwd=SCRIPTS.parent / "exercises/field-notes/reference",
            timeout_seconds=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["profiles"],
            [
                ["unset", "development", "local-development", "fieldnotes-development", True],
                ["development", "development", "local-development", "fieldnotes-development", True],
                ["preview", "preview", "preview-test-not-configured", "fieldnotes-preview", False],
                ["production", "production", "production-external-not-configured", "fieldnotes", False],
            ],
        )
        self.assertTrue(payload["rejected"])


class SourceManifestTests(unittest.TestCase):
    def test_gitignore_matches_the_canonical_generated_boundaries(self) -> None:
        root = SCRIPTS.parent
        source_inputs = (
            "exercises/field-notes/fault-server/artifacts/keep.txt",
            "exercises/field-notes/sync-engine/android/keep.ts",
            "exercises/field-notes/shared/ios/keep.ts",
            "logs/verification.log",
        )
        generated_outputs = (
            "exercises/field-notes/reference/android/app/build.gradle",
            "exercises/field-notes/reference/ios/App/Info.plist",
            "exercises/field-notes/skeleton/dist/metadata.json",
            "node_modules/.package-lock.json",
        )
        for relative in source_inputs:
            with self.subTest(source=relative):
                result = process_runner.run_process(
                    ["git", "check-ignore", "--no-index", relative],
                    cwd=root,
                    timeout_seconds=5,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for relative in generated_outputs:
            with self.subTest(generated=relative):
                result = process_runner.run_process(
                    ["git", "check-ignore", "--no-index", relative],
                    cwd=root,
                    timeout_seconds=5,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_git_ignored_regular_input_is_still_hashed_and_copied(self) -> None:
        with tempfile.TemporaryDirectory(prefix="manifest-ignore-test-") as temporary:
            root = Path(temporary)
            (root / ".git/info").mkdir(parents=True)
            relative_project = Path("exercises/field-notes/reference")
            (root / ".git/info/exclude").write_text(f"{relative_project}/app.config.js\n")
            project = root / relative_project
            project.mkdir(parents=True)
            hidden = project / "app.config.js"
            hidden.write_text("export default { value: 1 };\n")
            (project / "dist").mkdir()
            (project / "dist/ignored.js").write_text("generated\n")

            first = source_manifest.build_manifest(root)
            first_digest = source_manifest.fingerprint_manifest(first)[0]
            relatives = {entry.relative.as_posix() for entry in first}
            self.assertIn(f"{relative_project.as_posix()}/app.config.js", relatives)
            self.assertNotIn(f"{relative_project.as_posix()}/dist/ignored.js", relatives)

            destination = root / "outside-copy"
            # The destination must not be inside root because a canonical source
            # scan intentionally includes every non-generated regular file.
            with tempfile.TemporaryDirectory(prefix="manifest-copy-test-") as copy_temporary:
                destination = Path(copy_temporary) / "project"
                source_manifest.copy_source_subset(
                    root, relative_project, destination, entries=first
                )
                self.assertEqual(
                    (destination / "app.config.js").read_text(), hidden.read_text()
                )
                self.assertFalse((destination / "dist").exists())

            hidden.write_text("export default { value: 2 };\n")
            second_digest = source_manifest.fingerprint_manifest(
                source_manifest.build_manifest(root)
            )[0]
            self.assertNotEqual(first_digest, second_digest)

    def test_source_names_that_collide_with_generated_basenames_remain_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="manifest-name-collision-test-") as temporary:
            root = Path(temporary)
            sources = {
                "docs/android/contract.md": "android source\n",
                "examples/dist/model.ts": "dist source\n",
                "capstone/artifacts/evidence.md": "artifact source\n",
                "logs/verification.log": "log source\n",
            }
            for relative, content in sources.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            generated = root / "exercises/field-notes/reference/dist/generated.js"
            generated.parent.mkdir(parents=True)
            generated.write_text("generated\n")

            relatives = {
                entry.relative.as_posix() for entry in source_manifest.build_manifest(root)
            }
            self.assertTrue(set(sources).issubset(relatives))
            self.assertNotIn("exercises/field-notes/reference/dist/generated.js", relatives)

    def test_package_generated_boundaries_match_actual_tool_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="manifest-package-boundary-test-") as temporary:
            root = Path(temporary)
            source_inputs = {
                "exercises/field-notes/sync-engine/android/source.ts": "sync source\n",
                "exercises/field-notes/shared/ios/contract.ts": "shared source\n",
                "exercises/field-notes/fault-server/artifacts/fault.json": "{}\n",
            }
            generated_outputs = {
                "exercises/field-notes/reference/.expo/state.json": "{}\n",
                "exercises/field-notes/reference/android/app/build.gradle": "generated\n",
                "exercises/field-notes/reference/ios/App/Info.plist": "generated\n",
                "exercises/field-notes/reference/dist/android/bundle.js": "generated\n",
                "exercises/field-notes/skeleton/android/app/build.gradle": "generated\n",
                "exercises/field-notes/skeleton/ios/App/Info.plist": "generated\n",
                "exercises/field-notes/fault-server/node_modules/pkg/index.js": "generated\n",
                "exercises/field-notes/shared/coverage/report.json": "generated\n",
            }
            for relative, content in {**source_inputs, **generated_outputs}.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

            relatives = {
                entry.relative.as_posix() for entry in source_manifest.build_manifest(root)
            }
            self.assertTrue(set(source_inputs).issubset(relatives))
            self.assertTrue(set(generated_outputs).isdisjoint(relatives))

    def test_symlink_and_special_source_entries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="manifest-safety-test-") as temporary:
            root = Path(temporary)
            outside = root.parent / f"{root.name}-outside"
            outside.write_text("outside")
            try:
                (root / "escape.md").symlink_to(outside)
                with self.assertRaisesRegex(source_manifest.SourceManifestError, "symlink"):
                    source_manifest.build_manifest(root)
                (root / "escape.md").unlink()
                if hasattr(os, "mkfifo"):
                    os.mkfifo(root / "source.fifo")
                    with self.assertRaisesRegex(source_manifest.SourceManifestError, "허용하지"):
                        source_manifest.build_manifest(root)
            finally:
                outside.unlink(missing_ok=True)


class ProcessRunnerTests(unittest.TestCase):
    def test_timeout_terminates_descendant_process_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="process-tree-test-") as temporary:
            marker = Path(temporary) / "late-write"
            grandchild = (
                "import pathlib,time; "
                "time.sleep(0.8); "
                f"pathlib.Path({str(marker)!r}).write_text('survived')"
            )
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable,'-c',{grandchild!r}]); "
                "time.sleep(10)"
            )
            result = process_runner.run_process(
                [sys.executable, "-c", parent],
                cwd=Path(temporary),
                timeout_seconds=0.15,
                grace_seconds=0.15,
            )
            self.assertTrue(result.timed_out)
            time.sleep(0.9)
            self.assertFalse(marker.exists(), "grandchild survived the timeout process-group cleanup")

    def test_spawn_error_is_typed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="spawn-test-") as temporary:
            with self.assertRaises(process_runner.CommandSpawnError):
                process_runner.run_process(
                    ["definitely-not-a-mobile-guide-command"],
                    cwd=Path(temporary),
                    timeout_seconds=1,
                )


class BundleEvidenceTests(unittest.TestCase):
    def create_valid_output(self, root: Path) -> None:
        bundle = root / "_expo/static/js/android/entry.hbc"
        bundle.parent.mkdir(parents=True)
        bundle.write_bytes(b"bundle")
        asset = root / "assets/image"
        asset.parent.mkdir()
        asset.write_bytes(b"asset")
        (root / "metadata.json").write_text(
            json.dumps(
                {
                    "version": 0,
                    "bundler": "metro",
                    "fileMetadata": {
                        "android": {
                            "bundle": "_expo/static/js/android/entry.hbc",
                            "assets": [{"path": "assets/image", "ext": "png"}],
                        }
                    },
                }
            )
        )

    def test_full_artifact_manifest_binds_metadata_bundle_and_assets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bundle-evidence-test-") as temporary:
            output = Path(temporary)
            self.create_valid_output(output)
            first = export_bundle.validate_bundle_output(output, "android")
            self.assertEqual(first["artifact_file_count"], 3)
            (output / "assets/image").write_bytes(b"changed")
            second = export_bundle.validate_bundle_output(output, "android")
            self.assertNotEqual(
                first["artifact_manifest_sha256"], second["artifact_manifest_sha256"]
            )

    def test_metadata_platform_and_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bundle-negative-test-") as temporary:
            output = Path(temporary)
            self.create_valid_output(output)
            metadata = json.loads((output / "metadata.json").read_text())
            metadata["fileMetadata"] = {
                "ios": {"bundle": "../outside.js", "assets": []}
            }
            (output / "metadata.json").write_text(json.dumps(metadata))
            with self.assertRaises(SystemExit):
                export_bundle.validate_bundle_output(output, "android")


class CngContractTests(unittest.TestCase):
    def test_android_filter_requires_exported_view_default_browsable_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cng-manifest-test-") as temporary:
            manifest = Path(temporary) / "AndroidManifest.xml"
            manifest.write_text(
                """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
                <application><activity android:name=".MainActivity" android:exported="true">
                  <intent-filter>
                    <action android:name="android.intent.action.VIEW" />
                    <category android:name="android.intent.category.DEFAULT" />
                    <category android:name="android.intent.category.BROWSABLE" />
                    <data android:scheme="fieldnotes" />
                  </intent-filter>
                </activity></application></manifest>"""
            )
            owners = check_cng.validate_android_links(manifest, {"fieldnotes"})
            self.assertEqual(owners, {"fieldnotes": ".MainActivity"})
            manifest.write_text(manifest.read_text().replace("android.intent.category.DEFAULT", "wrong"))
            with self.assertRaises(SystemExit):
                check_cng.validate_android_links(manifest, {"fieldnotes"})

    def test_ios_bundle_ids_are_read_from_build_settings(self) -> None:
        pbx = """
          PRODUCT_BUNDLE_IDENTIFIER = dev.example.app;
          PRODUCT_BUNDLE_IDENTIFIER = "dev.example.app";
        """
        self.assertEqual(check_cng.ios_bundle_ids(pbx), ["dev.example.app", "dev.example.app"])

    def test_android_permissions_use_only_effective_manifest_nodes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cng-permission-test-") as temporary:
            manifest = Path(temporary) / "AndroidManifest.xml"
            manifest.write_text(
                """<manifest xmlns:android="http://schemas.android.com/apk/res/android"
                  xmlns:tools="http://schemas.android.com/tools">
                  <uses-permission android:name="android.permission.CAMERA" />
                  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
                  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
                  <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
                  <uses-permission android:name="android.permission.RECORD_AUDIO" tools:node="remove" />
                  <application>
                    <meta-data android:name="unrelated"
                      android:value="android.permission.ACCESS_BACKGROUND_LOCATION" />
                  </application>
                </manifest>"""
            )
            summary = check_cng.validate_android_permissions(manifest)
            self.assertIn(
                "android.permission.POST_NOTIFICATIONS", summary["effective_requested"]
            )
            self.assertIn(
                "android.permission.RECORD_AUDIO", summary["removal_directives"]
            )
            self.assertNotIn(
                "android.permission.ACCESS_BACKGROUND_LOCATION",
                summary["effective_requested"],
            )

            manifest.write_text(
                manifest.read_text().replace(
                    "<application>",
                    '<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />'
                    "<application>",
                )
            )
            with self.assertRaises(SystemExit):
                check_cng.validate_android_permissions(manifest)

    def test_android_permissions_reject_missing_required_permission(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cng-required-permission-test-") as temporary:
            manifest = Path(temporary) / "AndroidManifest.xml"
            manifest.write_text(
                """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
                  <uses-permission android:name="android.permission.CAMERA" />
                  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
                </manifest>"""
            )
            with self.assertRaises(SystemExit):
                check_cng.validate_android_permissions(manifest)

    def test_ios_permissions_require_bounded_processing_and_reject_excess(self) -> None:
        valid: dict[str, object] = {
            "NSCameraUsageDescription": "Take a field-note photo",
            "NSLocationWhenInUseUsageDescription": "Attach foreground location",
            "NSPhotoLibraryUsageDescription": "Choose an existing photo",
            "UIBackgroundModes": ["processing"],
            "BGTaskSchedulerPermittedIdentifiers": [
                "com.expo.modules.backgroundtask.processing"
            ],
        }
        summary = check_cng.validate_ios_permissions(valid)
        self.assertEqual(summary["background_modes"], ["processing"])
        self.assertEqual(
            summary["background_task_identifiers"],
            ["com.expo.modules.backgroundtask.processing"],
        )
        self.assertEqual(
            summary["photo_library_usage_description_keys"],
            ["NSPhotoLibraryUsageDescription"],
        )

        invalid_values = (
            {**valid, "NSMicrophoneUsageDescription": "Record audio"},
            {**valid, "NSLocationAlwaysUsageDescription": "Track always"},
            {**valid, "UIBackgroundModes": ["processing", "remote-notification"]},
            {**valid, "UIBackgroundModes": []},
            {
                **valid,
                "BGTaskSchedulerPermittedIdentifiers": [
                    "com.example.unbounded.background"
                ],
            },
            {**valid, "NSCameraUsageDescription": "   "},
        )
        for plist in invalid_values:
            with self.subTest(plist=plist), self.assertRaises(SystemExit):
                check_cng.validate_ios_permissions(plist)


class DependencyReceiptTests(unittest.TestCase):
    def create_install(self, root: Path, declared: list[tuple[str, str]]) -> None:
        (root / "package.json").write_text(
            json.dumps({"name": "root", "workspaces": [relative for relative, _ in declared]})
        )
        node_modules = root / "node_modules"
        (node_modules / ".bin").mkdir(parents=True)
        (node_modules / ".package-lock.json").write_text("{}")
        tools = node_modules / "tools"
        tools.mkdir()
        for binary in dependency_receipt.BINARIES:
            target = tools / binary
            target.write_text(binary)
            (node_modules / ".bin" / binary).symlink_to(target)
        for relative, package_name in declared:
            canonical = root / relative
            canonical.mkdir(parents=True)
            (canonical / "package.json").write_text(json.dumps({"name": package_name}))
            install = node_modules.joinpath(*package_name.split("/"))
            install.parent.mkdir(parents=True, exist_ok=True)
            install.symlink_to(canonical)

    def test_workspace_realpath_and_selected_bins_are_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="dependency-receipt-test-") as temporary:
            root = Path(temporary)
            declared = [
                ("packages/shared", "@field-notes/shared"),
                ("packages/tool", "plain-tool"),
            ]
            self.create_install(root, declared)
            receipt = dependency_receipt.installation_receipt(root)
            self.assertEqual(
                set(receipt["workspace_targets"]),
                {"@field-notes/shared", "plain-tool"},
            )

            shared = root / "node_modules/@field-notes/shared"
            shared.unlink()
            external = root / "external-shared"
            external.mkdir()
            shared.symlink_to(external)
            with self.assertRaisesRegex(dependency_receipt.DependencyReceiptError, "target 불일치"):
                dependency_receipt.installation_receipt(root)

    def test_workspace_paths_and_package_names_reject_glob_escape_and_mismatch(self) -> None:
        invalid_paths = ("packages/*", "../outside", "/absolute", "packages/../outside")
        for invalid in invalid_paths:
            with self.subTest(path=invalid), tempfile.TemporaryDirectory(
                prefix="workspace-path-negative-test-"
            ) as temporary:
                root = Path(temporary)
                (root / "package.json").write_text(
                    json.dumps({"name": "root", "workspaces": [invalid]})
                )
                with self.assertRaises(workspace_contract.WorkspaceContractError):
                    workspace_contract.load_declared_workspaces(root)

        with tempfile.TemporaryDirectory(prefix="workspace-name-negative-test-") as temporary:
            root = Path(temporary)
            workspace = root / "packages/bad"
            workspace.mkdir(parents=True)
            (root / "package.json").write_text(
                json.dumps({"name": "root", "workspaces": ["packages/bad"]})
            )
            (workspace / "package.json").write_text(json.dumps({"name": "../escape"}))
            with self.assertRaisesRegex(workspace_contract.WorkspaceContractError, "npm name"):
                workspace_contract.load_declared_workspaces(root)

        with tempfile.TemporaryDirectory(prefix="workspace-symlink-escape-test-") as temporary:
            root = Path(temporary) / "root"
            outside = Path(temporary) / "outside"
            (root / "packages").mkdir(parents=True)
            outside.mkdir()
            (outside / "package.json").write_text(json.dumps({"name": "escaped-package"}))
            (root / "package.json").write_text(
                json.dumps({"name": "root", "workspaces": ["packages/escape"]})
            )
            (root / "packages/escape").symlink_to(outside)
            with self.assertRaisesRegex(workspace_contract.WorkspaceContractError, "symlink"):
                workspace_contract.load_declared_workspaces(root)

        with tempfile.TemporaryDirectory(prefix="workspace-name-mismatch-test-") as temporary:
            root = Path(temporary)
            self.create_install(root, [("packages/shared", "@field-notes/shared")])
            (root / "packages/shared/package.json").write_text(
                json.dumps({"name": "@field-notes/renamed"})
            )
            with self.assertRaisesRegex(dependency_receipt.DependencyReceiptError, "install link"):
                dependency_receipt.installation_receipt(root)


class SourceFingerprintCliTests(unittest.TestCase):
    def test_digest_does_not_require_dependency_receipt(self) -> None:
        expected = "a" * 64
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["source_fingerprint.py", "--digest"]), mock.patch.object(
            source_fingerprint, "fingerprint", return_value=(expected, 1)
        ), mock.patch.object(
            source_fingerprint,
            "installation_receipt",
            side_effect=AssertionError("digest must not inspect node_modules"),
        ), contextlib.redirect_stdout(output):
            source_fingerprint.main()
        self.assertEqual(output.getvalue().strip(), expected)


class VerifySummaryTests(unittest.TestCase):
    def reset_verify(self) -> None:
        verify.RESULTS.clear()
        verify.STARTED_AT = verify.datetime.now(verify.UTC)
        verify.FINISHED_AT = None
        verify.LIFECYCLE = "RUNNING"
        verify.INTERRUPTED_BY = None
        verify.INFRASTRUCTURE_ERROR = None
        verify.ACTIVE_GATE_ID = None
        verify.EXPECTED_GATES = ()
        verify.LOG_PATH.write_text("")

    def test_gate_manifest_rejects_unknown_or_forward_dependencies(self) -> None:
        with self.assertRaises(ValueError):
            verify.validate_gate_manifest(
                (verify.Gate("a", "a", ("true",), dependencies=("missing",)),)
            )
        with self.assertRaises(ValueError):
            verify.validate_gate_manifest(
                (
                    verify.Gate("a", "a", ("true",), dependencies=("b",)),
                    verify.Gate("b", "b", ("true",)),
                )
            )

    def test_real_gate_manifest_has_required_environment_and_infra_suite(self) -> None:
        gate_list = tuple(verify.gates())
        verify.validate_gate_manifest(gate_list)
        by_id = {gate.gate_id: gate for gate in gate_list}
        self.assertEqual(len(gate_list), 22)
        self.assertEqual(sum(gate.kind == "required" for gate in gate_list), 22)
        self.assertEqual(sum(gate.kind == "informational" for gate in gate_list), 0)
        self.assertEqual(by_id["environment"].kind, "required")
        self.assertEqual(by_id["verification-infrastructure"].kind, "required")
        self.assertIn("scripts/tests", by_id["verification-infrastructure"].command)
        self.reset_verify()
        verify.EXPECTED_GATES = gate_list
        payload = verify.summary_payload()
        self.assertEqual(payload["expected"]["automatic_total"], 22)
        self.assertEqual(payload["expected"]["required_total"], 22)
        self.assertEqual(payload["expected"]["informational_total"], 0)

    def test_spawn_error_yields_infra_lifecycle_and_complete_result_set(self) -> None:
        self.reset_verify()
        test_gates = [
            verify.Gate("spawn", "spawn", ("definitely-not-a-mobile-guide-command",)),
            verify.Gate("after", "after", (sys.executable, "-c", "pass")),
        ]
        with mock.patch.object(verify, "gates", return_value=test_gates), mock.patch.object(
            verify.signal, "signal"
        ):
            exit_code = verify.main()
        payload = json.loads(verify.SUMMARY_PATH.read_text())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["lifecycle"], "INFRA_ERROR")
        self.assertEqual(payload["overall_status"], "INCOMPLETE")
        self.assertIn("finished_at_utc", payload)
        self.assertEqual(payload["completed"]["automatic_results"], 2)
        by_id = {item["gate_id"]: item for item in payload["results"]}
        self.assertEqual(by_id["spawn"]["status"], "FAIL")
        self.assertEqual(by_id["spawn"]["failure_class"], "infrastructure")
        self.assertEqual(by_id["after"]["status"], "NOT-RUN")
        self.assertEqual(payload["counts"]["manual_not_run"], len(verify.MANUAL))

    def test_running_summary_has_no_finished_timestamp(self) -> None:
        self.reset_verify()
        verify.EXPECTED_GATES = tuple(verify.gates())
        payload = verify.summary_payload()
        self.assertEqual(payload["lifecycle"], "RUNNING")
        self.assertEqual(payload["overall_status"], "INCOMPLETE")
        self.assertNotIn("finished_at_utc", payload)


if __name__ == "__main__":
    unittest.main()
