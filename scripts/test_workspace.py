from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import workspace


DOC_TARGET = "exercises/01-service-classification"
MODEL_TARGET = "exercises/07-local-cloud-model"
PROJECT_TARGET = "projects/multitenant-document-processing-saas"


def snapshot(root: Path) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    if not root.exists() and not root.is_symlink():
        return result
    if root.is_symlink():
        return {".": ("link", os.readlink(root))}
    if root.is_file():
        return {".": ("file", hashlib.sha256(root.read_bytes()).hexdigest())}
    result["."] = ("dir", "")
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        for name in sorted([*directory_names, *file_names]):
            path = current / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                result[relative] = ("link", os.readlink(path))
            elif path.is_file():
                result[relative] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
            elif path.is_dir():
                result[relative] = ("dir", "")
            else:
                result[relative] = ("other", "")
    return result


class WorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "guide"
        self.root.mkdir()
        self._write(DOC_TARGET, "template/assessment.md", b"starter\n")
        self._write(DOC_TARGET, "contract.json", b"{}\n")
        self._write(MODEL_TARGET, "skeleton/cloud_model.py", b"VALUE = 1\n")
        self._write(PROJECT_TARGET, "template/01.md", b"capstone\n")
        self._write(PROJECT_TARGET, "contract.json", b"{}\n")
        self._write("scripts", "check_artifact.py", b"pass\n")
        self._write("scripts", "verify_cloud_model.py", b"pass\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, base: str, relative: str, content: bytes) -> Path:
        path = self.root / base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_allowlist_is_exact(self) -> None:
        self.assertEqual(
            {
                "exercises/01-service-classification",
                "exercises/02-iaas-failure-domains",
                "exercises/03-managed-service-contract",
                "exercises/04-faas-event-lifecycle",
                "exercises/05-saas-tenant-isolation",
                "exercises/06-cost-and-exit",
                "exercises/07-local-cloud-model",
                "projects/multitenant-document-processing-saas",
            },
            set(workspace.TARGETS),
        )

    def test_document_and_capstone_templates_are_copied_without_overwrite(self) -> None:
        document = workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(b"starter\n", (document / "assessment.md").read_bytes())

        project = workspace.new_workspace(self.root, PROJECT_TARGET)
        self.assertEqual(b"capstone\n", (project / "01.md").read_bytes())

        before = snapshot(document)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(before, snapshot(document))

    def test_local_model_copies_skeleton_as_cloud_model(self) -> None:
        destination = workspace.new_workspace(self.root, MODEL_TARGET)
        self.assertEqual(b"VALUE = 1\n", (destination / "cloud_model.py").read_bytes())

    def test_copy_failure_removes_only_partial_destination_and_preserves_bytes(self) -> None:
        source = self.root / DOC_TARGET / "template"
        source_before = snapshot(source)
        external = Path(self.temporary.name) / "external-sentinel"
        external.write_bytes(b"outside\n")
        external_before = external.read_bytes()
        destination = self.root / ".workspace" / "01-service-classification"

        def fail_after_partial_copy(
            _source: Path, target: Path, *, copy_function: object
        ) -> None:
            del copy_function
            Path(target).mkdir()
            (Path(target) / "partial.md").write_bytes(b"partial\n")
            raise OSError("simulated copy failure")

        with mock.patch("workspace.shutil.copytree", side_effect=fail_after_partial_copy):
            with self.assertRaisesRegex(workspace.WorkspaceError, "만들 수 없습니다"):
                workspace.new_workspace(self.root, DOC_TARGET)

        self.assertFalse(destination.exists())
        self.assertEqual(source_before, snapshot(source))
        self.assertEqual(external_before, external.read_bytes())

    def test_absolute_traversal_extra_segments_and_unknown_targets_are_rejected(self) -> None:
        before = snapshot(self.root)
        invalid = (
            str((self.root / DOC_TARGET).resolve()),
            "exercises/../projects/multitenant-document-processing-saas",
            f"{DOC_TARGET}/template",
            "exercises/not-allowlisted",
        )
        for target in invalid:
            with self.subTest(target=target):
                with self.assertRaises(workspace.WorkspaceError):
                    workspace.new_workspace(self.root, target)
                self.assertEqual(before, snapshot(self.root))

    def test_source_symlink_and_dangling_symlink_are_rejected(self) -> None:
        external = Path(self.temporary.name) / "external"
        external.mkdir()
        external_file = external / "assessment.md"
        external_file.write_bytes(b"outside\n")

        template = self.root / DOC_TARGET / "template"
        for child in template.iterdir():
            child.unlink()
        template.rmdir()
        template.symlink_to(external, target_is_directory=True)
        before_external = external_file.read_bytes()
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(before_external, external_file.read_bytes())

        template.unlink()
        template.mkdir()
        (template / "dangling.md").symlink_to(external / "missing.md")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(before_external, external_file.read_bytes())

    def test_symlink_ancestor_is_rejected(self) -> None:
        real_exercises = self.root / "real-exercises"
        (real_exercises / "01-service-classification" / "template").mkdir(parents=True)
        (real_exercises / "01-service-classification" / "template" / "assessment.md").write_bytes(
            b"outside\n"
        )
        original = self.root / "exercises"
        for path in sorted(original.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
        original.rmdir()
        original.symlink_to(real_exercises, target_is_directory=True)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)

    def test_existing_destination_file_and_symlinks_are_rejected_without_byte_changes(self) -> None:
        workspace_root = self.root / ".workspace"
        workspace_root.mkdir()
        destination = workspace_root / "01-service-classification"

        destination.mkdir()
        directory_sentinel = destination / "keep.md"
        directory_sentinel.write_bytes(b"keep-directory\n")
        before_directory = snapshot(destination)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(before_directory, snapshot(destination))
        directory_sentinel.unlink()
        destination.rmdir()

        destination.write_bytes(b"keep-me\n")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(b"keep-me\n", destination.read_bytes())

        destination.unlink()
        external = Path(self.temporary.name) / "outside-workspace"
        external.mkdir()
        sentinel = external / "sentinel"
        sentinel.write_bytes(b"preserve\n")
        destination.symlink_to(external, target_is_directory=True)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertEqual(b"preserve\n", sentinel.read_bytes())

        destination.unlink()
        destination.symlink_to(external / "missing", target_is_directory=True)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.new_workspace(self.root, DOC_TARGET)
        self.assertFalse((external / "missing").exists())

    def test_check_dispatches_artifact_and_cloud_model_read_only(self) -> None:
        document = workspace.new_workspace(self.root, DOC_TARGET)
        model = workspace.new_workspace(self.root, MODEL_TARGET)
        before_document = snapshot(document)
        before_model = snapshot(model)

        completed = mock.Mock(returncode=0)
        with mock.patch("workspace.subprocess.run", return_value=completed) as run:
            self.assertEqual(0, workspace.check_workspace(self.root, DOC_TARGET))
            command = run.call_args.args[0]
            self.assertEqual(str(self.root / "scripts" / "check_artifact.py"), command[1])
            self.assertEqual(str(document), command[2])
            self.assertEqual(str(self.root / DOC_TARGET / "contract.json"), command[3])
            self.assertTrue(run.call_args.kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1")

        with mock.patch("workspace.subprocess.run", return_value=completed) as run:
            self.assertEqual(0, workspace.check_workspace(self.root, MODEL_TARGET))
            command = run.call_args.args[0]
            self.assertEqual(str(self.root / "scripts" / "verify_cloud_model.py"), command[1])
            self.assertEqual("--implementation", command[2])
            self.assertEqual(str(model / "cloud_model.py"), command[3])

        self.assertEqual(before_document, snapshot(document))
        self.assertEqual(before_model, snapshot(model))


class RealRepositorySafetyTest(unittest.TestCase):
    def test_invalid_requests_do_not_change_real_repository_bytes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        watched = [
            root / "exercises",
            root / "projects" / "multitenant-document-processing-saas",
            root / ".workspace",
        ]
        before = [snapshot(path) for path in watched]
        invalid = (
            "../cloud-computing",
            "exercises/01-service-classification/template",
            "projects/unknown",
        )
        for target in invalid:
            with self.assertRaises(workspace.WorkspaceError):
                workspace.new_workspace(root, target)
        self.assertEqual(before, [snapshot(path) for path in watched])


if __name__ == "__main__":
    unittest.main()
