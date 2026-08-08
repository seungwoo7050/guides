#!/usr/bin/env python3
"""Validate dependency and plugin pins from Maven's effective model XML."""

from __future__ import annotations

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NAMESPACE = {"m": "http://maven.apache.org/POM/4.0.0"}


def text(element: ET.Element, path: str) -> str | None:
    child = element.find(path, NAMESPACE)
    return child.text.strip() if child is not None and child.text else None


def fail(message: str) -> None:
    raise SystemExit(f"effective POM 계약이 다릅니다: {message}")


def validate(root: ET.Element) -> None:
    local_name = root.tag.rsplit("}", 1)[-1]
    projects = [root] if local_name == "project" else root.findall("./m:project", NAMESPACE)
    if len(projects) != 8:
        fail(f"reactor project 수가 8이 아닙니다: {len(projects)}")

    by_artifact = {text(project, "./m:artifactId"): project for project in projects}
    parent = by_artifact.get("backend-spring-boot-guide-parent")
    if parent is None:
        fail("root project가 없습니다.")
    if text(parent, "./m:parent/m:version") != "4.1.0":
        fail("Spring Boot parent가 4.1.0이 아닙니다.")

    expected_properties = {
        "java.version": "21",
        "maven.compiler.release": "21",
        "testcontainers.version": "2.0.5",
        "avro.version": "1.12.1",
        "resilience4j.version": "2.4.0",
        "wiremock.version": "3.12.1",
        "kafka.version": "4.3.1",
        "maven-surefire-plugin.version": "3.5.6",
    }
    for name, expected in expected_properties.items():
        actual = text(parent, f"./m:properties/m:{name}")
        if actual != expected:
            fail(f"root property {name}: 예상={expected}, 실제={actual}")

    surefire_versions = {
        text(plugin, "./m:version")
        for project in projects
        for plugin in project.findall(
            ".//m:plugin[m:artifactId='maven-surefire-plugin']", NAMESPACE
        )
    }
    if surefire_versions != {"3.5.6"}:
        fail(f"Surefire effective version: {surefire_versions}")

    dependency_versions: dict[tuple[str | None, str | None], set[str | None]] = {}
    for project in projects:
        for dependency in project.findall(".//m:dependency", NAMESPACE):
            key = (
                text(dependency, "./m:groupId"),
                text(dependency, "./m:artifactId"),
            )
            dependency_versions.setdefault(key, set()).add(text(dependency, "./m:version"))
    required_dependencies = {
        ("org.testcontainers", "testcontainers"): "2.0.5",
        ("org.apache.avro", "avro"): "1.12.1",
        ("io.github.resilience4j", "resilience4j-spring-boot4"): "2.4.0",
        ("org.wiremock", "wiremock-standalone"): "3.12.1",
    }
    for dependency, expected in required_dependencies.items():
        versions = dependency_versions.get(dependency, set())
        if not versions or versions != {expected}:
            fail(f"dependency {dependency}: 예상={expected}, 실제={versions}")

def self_test(root: ET.Element) -> None:
    projects = [root] if root.tag.rsplit("}", 1)[-1] == "project" else root.findall(
        "./m:project", NAMESPACE
    )
    parent = next(
        project
        for project in projects
        if text(project, "./m:artifactId") == "backend-spring-boot-guide-parent"
    )
    mutations: list[tuple[str, ET.Element, str]] = []

    property_element = parent.find("./m:properties/m:testcontainers.version", NAMESPACE)
    if property_element is None:
        fail("self-test 대상 testcontainers.version이 없습니다.")
    mutations.append(("effective-property", property_element, "2.0.4"))

    plugin_version = parent.find(
        ".//m:plugin[m:artifactId='maven-surefire-plugin']/m:version", NAMESPACE
    )
    if plugin_version is None:
        fail("self-test 대상 Surefire plugin이 없습니다.")
    mutations.append(("effective-plugin", plugin_version, "3.5.5"))

    avro_version = None
    for project in projects:
        for dependency in project.findall(".//m:dependency", NAMESPACE):
            if text(dependency, "./m:artifactId") == "avro":
                avro_version = dependency.find("./m:version", NAMESPACE)
                break
        if avro_version is not None:
            break
    if avro_version is None:
        fail("self-test 대상 Avro dependency가 없습니다.")
    mutations.append(("effective-dependency", avro_version, "1.12.0"))

    for name, original_element, replacement in mutations:
        candidate = copy.deepcopy(root)
        original_elements = list(root.iter())
        candidate_elements = list(candidate.iter())
        index = original_elements.index(original_element)
        candidate_elements[index].text = replacement
        try:
            validate(candidate)
        except SystemExit:
            print(f"[PASS] effective POM mutant: {name}")
        else:
            fail(f"effective POM mutant를 허용했습니다: {name}")


def main() -> int:
    if len(sys.argv) not in {2, 3} or (len(sys.argv) == 3 and sys.argv[2] != "--self-test"):
        fail("사용법: check-effective-pom.py EFFECTIVE_XML [--self-test]")
    path = Path(sys.argv[1])
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        fail(f"XML을 읽을 수 없습니다: {error}")
    validate(root)
    if len(sys.argv) == 3:
        self_test(root)
    print("Spring Boot effective POM 판본·plugin·dependency pin 검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
