#!/usr/bin/env python3
"""Verify the five project-local skill installs against the provenance lock."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "UPSTREAMS.lock.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    match = re.search(r"(?m)^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", text)
    if not match:
        raise ValueError(f"missing YAML name: {skill_file}")
    return match.group(1).strip()


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    install_root = (ROOT / lock["install_root"]).resolve()
    expected_dirs = {entry["requested_name"] for entry in lock["skills"]}
    actual_dirs = {
        path.name for path in install_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    }

    errors: list[str] = []
    if actual_dirs != expected_dirs:
        errors.append(
            f"installed directory set differs: expected={sorted(expected_dirs)}, actual={sorted(actual_dirs)}"
        )

    for entry in lock["skills"]:
        error_count = len(errors)
        skill_file = install_root / entry["requested_name"] / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"missing {skill_file}")
            print(f"FAIL  {entry['requested_name']}")
            continue
        actual_name = metadata_name(skill_file)
        actual_hash = sha256(skill_file)
        if actual_name != entry["installed_metadata_name"]:
            errors.append(
                f"{entry['requested_name']}: metadata name {actual_name!r} != "
                f"{entry['installed_metadata_name']!r}"
            )
        if actual_hash != entry["installed_skill_sha256"]:
            errors.append(
                f"{entry['requested_name']}: SKILL.md sha256 {actual_hash} != locked value"
            )
        if "installed_agent_sha256" in entry:
            agent_file = skill_file.parent / "agents" / "openai.yaml"
            if not agent_file.is_file():
                errors.append(f"missing {agent_file}")
            elif sha256(agent_file) != entry["installed_agent_sha256"]:
                errors.append(
                    f"{entry['requested_name']}: agents/openai.yaml sha256 differs from locked value"
                )
        status = "OK" if len(errors) == error_count else "FAIL"
        print(f"{status}  {entry['requested_name']}  {entry['commit'][:12]}")

    if errors:
        print("\nVerification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"\nVerified {len(expected_dirs)} project-local skills under {install_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
