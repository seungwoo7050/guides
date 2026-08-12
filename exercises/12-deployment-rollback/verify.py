#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parent


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("deployment_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(name: str) -> dict:
    return yaml.safe_load((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def initialise(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "current.json").write_text(
        json.dumps(
            {
                "current": "v1",
                "previous": None,
                "db_schema": 3,
                "current_compat": {"schema_min": 3, "schema_max": 4},
                "image": manifest("v1.yaml")["image"],
            }
        ) + "\n",
        encoding="utf-8",
    )


def state(path: Path) -> dict:
    return json.loads((path / "current.json").read_text(encoding="utf-8"))


def events(path: Path) -> list[dict]:
    event_path = path / "events.jsonl"
    if not event_path.exists():
        return []
    return [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "workspace", "reference"}:
        print("사용법: verify.py [skeleton|workspace|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "deploy.py")
    errors: list[str] = []

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)

        bad_dir = base / "bad"
        initialise(bad_dir)
        result = module.deploy(bad_dir, manifest("bad.yaml"))
        if result.get("status") != "failed" or result.get("phase") != "smoke":
            errors.append(f"smoke 실패 결과가 올바르지 않습니다: {result}")
        bad_state = state(bad_dir)
        if bad_state.get("current") != "v1":
            errors.append("smoke 실패 전에 current release를 바꿨습니다.")
        if bad_state.get("db_schema") != 4:
            errors.append(
                "호환 migration이 적용된 뒤 smoke가 실패하면 이전 release는 유지하되 "
                "database schema 상태는 4로 남아야 합니다."
            )
        if (bad_dir / "staged.json").exists():
            errors.append("실패 뒤 staged 상태가 남았습니다.")
        event_names = [item.get("event") for item in events(bad_dir)]
        for required in (
            "preflight-passed",
            "candidate-staged",
            "migration-applied",
            "readiness-passed",
            "rollback-completed",
            "deployment-failed",
        ):
            if required not in event_names:
                errors.append(f"smoke 실패 event가 없습니다: {required}")

        incompatible_dir = base / "incompatible"
        initialise(incompatible_dir)
        result = module.deploy(incompatible_dir, manifest("incompatible.yaml"))
        if result.get("status") != "failed" or result.get("phase") != "preflight":
            errors.append(f"schema 비호환을 preflight에서 거부하지 않았습니다: {result}")
        if state(incompatible_dir).get("current") != "v1":
            errors.append("preflight 실패가 current 상태를 바꿨습니다.")
        if any(item.get("event") == "candidate-staged" for item in events(incompatible_dir)):
            errors.append("preflight 실패한 candidate를 staged로 기록했습니다.")

        locked_dir = base / "locked"
        initialise(locked_dir)
        (locked_dir / "deployment.lock").write_text("other\n", encoding="utf-8")
        before = state(locked_dir)
        result = module.deploy(locked_dir, manifest("v2.yaml"))
        if result.get("status") != "failed" or result.get("phase") != "lock":
            errors.append(f"기존 lock을 거부하지 않았습니다: {result}")
        if state(locked_dir) != before:
            errors.append("lock 실패가 current 상태를 바꿨습니다.")

        success_dir = base / "success"
        initialise(success_dir)
        result = module.deploy(success_dir, manifest("v2.yaml"))
        final = state(success_dir)
        if result.get("status") != "success" or final.get("current") != "v2":
            errors.append(f"정상 배포가 성공하지 않았습니다: {result}, {final}")
        if final.get("previous") != "v1" or final.get("db_schema") != 4:
            errors.append("정상 배포의 previous 또는 schema 상태가 올바르지 않습니다.")
        if (success_dir / "deployment.lock").exists() or (success_dir / "staged.json").exists():
            errors.append("정상 배포 뒤 임시 lock 또는 staged 파일이 남았습니다.")
        success_events = events(success_dir)
        if not success_events or success_events[-1].get("event") != "release-committed":
            errors.append("정상 배포의 마지막 event가 release-committed가 아닙니다.")
        for item in success_events:
            if not all(isinstance(item.get(key), str) and item[key] for key in ("timestamp", "event", "release")):
                errors.append(f"event schema가 올바르지 않습니다: {item}")

    if errors:
        print(f"배포 상태 기계 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: lock, preflight, staged, smoke, commit과 rollback 상태")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
