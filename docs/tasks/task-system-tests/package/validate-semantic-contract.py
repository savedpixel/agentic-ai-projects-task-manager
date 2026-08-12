#!/usr/bin/env python3
"""Validate task-system semantic instruction contracts.

This catches regressions that plain file-count, line-count, and checklist audits miss.
It enforces the same-message planning review and the three-layer path-aware lessons
system, including create-if-missing preservation of live lesson ledgers.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent


def contract_path() -> Path:
    candidates = [
        PACKAGE_ROOT / "tests" / "semantic-contract.json",
        SCRIPT_DIR / "semantic-contract.json",
        PACKAGE_ROOT / "plan-folder-structure" / "semantic-contract.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise AssertionError(f"missing semantic-contract.json in candidates: {candidates}")


def is_source_package_layout() -> bool:
    return (PACKAGE_ROOT / "manifest.json").exists() and (PACKAGE_ROOT / "files").exists()


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path}")
    return path.read_text(errors="replace")


def read_json(path: Path) -> object:
    try:
        return json.loads(read(path))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {path}: {exc}") from exc


def strip_yaml_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#":
            return line[:index]
    return line


def parse_yaml_scalar(value: str) -> object:
    value = value.strip()
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_yaml_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def read_simple_yaml(path: Path) -> dict[str, object]:
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]
    for raw_line in read(path).splitlines():
        uncommented = strip_yaml_comment(raw_line).rstrip()
        if not uncommented.strip():
            continue
        indent = len(uncommented) - len(uncommented.lstrip(" "))
        stripped = uncommented.strip()
        if ":" not in stripped:
            raise AssertionError(f"unsupported YAML line in {path}: {raw_line!r}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise AssertionError(f"invalid YAML indentation in {path}: {raw_line!r}")
        current = stack[-1][1]
        if not value:
            child: dict[str, object] = {}
            current[key] = child
            stack.append((indent, child))
        else:
            current[key] = parse_yaml_scalar(value)
    return root


def require_all(label: str, text: str, needles: list[str]) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{label} missing required semantic strings: {missing}")


def regression(contract: dict[str, object], regression_id: str) -> dict[str, object]:
    for item in contract["regressions"]:
        if item["id"] == regression_id:
            return item
    raise AssertionError(f"semantic contract missing regression: {regression_id}")


def validate_skill_frontmatter(root: Path, *, label: str) -> None:
    skills_root = root / ".agents" / "skills"
    if not skills_root.exists():
        raise AssertionError(f"{label} missing skills root: {skills_root}")
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        lines = read(skill_file).splitlines()
        if not lines or lines[0].strip() != "---":
            raise AssertionError(f"{label} {skill_file} must start with YAML frontmatter delimiter ---")
        close = None
        for idx in range(1, min(len(lines), 40)):
            if lines[idx].strip() == "---":
                close = idx
                break
        if close is None:
            raise AssertionError(f"{label} {skill_file} missing closing YAML frontmatter delimiter ---")
        fields: dict[str, str] = {}
        for raw in lines[1:close]:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                raise AssertionError(f"{label} {skill_file} malformed YAML frontmatter line: {raw!r}")
            key, value = stripped.split(":", 1)
            fields[key.strip()] = value.strip().strip('"\'')
        if fields.get("name") != skill_name:
            raise AssertionError(f"{label} {skill_file} frontmatter name must be {skill_name!r}, got {fields.get('name')!r}")
        if not fields.get("description"):
            raise AssertionError(f"{label} {skill_file} frontmatter description is required")


def validate_surface(
    root: Path,
    task_root: str,
    *,
    label: str,
    agents_text: str | None = None,
) -> None:
    contract = read_json(contract_path())
    validate_skill_frontmatter(root, label=label)

    review_regression = regression(contract, "post-answer-move-to-pending-review")
    plan_skill = read(root / ".agents" / "skills" / "plan-task" / "SKILL.md")
    workflow = read(root / task_root / "workflow.md")
    if agents_text is None:
        agents_path = root / "AGENTS.md"
        agents = read(agents_path) if agents_path.exists() else ""
    else:
        agents = agents_text

    require_all(
        f"{label} plan-task skill",
        plan_skill,
        review_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} workflow",
        workflow,
        review_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS managed block",
            agents,
            review_regression["mustContainInAgentsManagedBlock"],
        )

    for bad in review_regression["forbiddenWithoutFullReview"]:
        if bad in plan_skill or bad in workflow or bad in agents:
            raise AssertionError(f"{label} contains forbidden movement-only prompt: {bad}")

    lessons_regression = regression(contract, "path-aware-lessons-system")
    execute_skill = read(root / ".agents" / "skills" / "execute-plan" / "SKILL.md")
    correct_skill = read(root / ".agents" / "skills" / "correct-task" / "SKILL.md")
    review_skill = read(root / ".agents" / "skills" / "review-task" / "SKILL.md")
    verification_skill = read(root / ".agents" / "skills" / "user-verification" / "SKILL.md")
    document_skill = read(root / ".agents" / "skills" / "document-task" / "SKILL.md")

    require_all(
        f"{label} plan-task lessons contract",
        plan_skill,
        lessons_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} execute-plan lessons contract",
        execute_skill,
        lessons_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} correct-task lessons contract",
        correct_skill,
        lessons_regression["mustContainInCorrectTaskSkill"],
    )
    require_all(
        f"{label} review-task lessons contract",
        review_skill,
        lessons_regression["mustContainInReviewTaskSkill"],
    )
    require_all(
        f"{label} user-verification lessons contract",
        verification_skill,
        lessons_regression["mustContainInUserVerificationSkill"],
    )
    require_all(
        f"{label} document-task lessons contract",
        document_skill,
        lessons_regression["mustContainInDocumentTaskSkill"],
    )
    require_all(
        f"{label} workflow lessons contract",
        workflow,
        lessons_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS lessons contract",
            agents,
            lessons_regression["mustContainInAgentsManagedBlock"],
        )

    key_surfaces = {
        "plan-task": plan_skill,
        "execute-plan": execute_skill,
        "correct-task": correct_skill,
        "review-task": review_skill,
        "user-verification": verification_skill,
        "document-task": document_skill,
        "workflow": workflow,
    }
    for surface_name, text in key_surfaces.items():
        if "lessons.md" in text:
            require_all(
                f"{label} {surface_name} three-layer references",
                text,
                ["lessons-active.md", "lessons-index.json"],
            )

    blocked_regression = regression(contract, "high-visibility-blocked-response")
    lifecycle_blocked_surfaces = {
        "execute-plan": execute_skill,
        "review-task": review_skill,
        "user-verification": verification_skill,
        "correct-task": correct_skill,
        "document-task": document_skill,
    }
    for surface_name, text in lifecycle_blocked_surfaces.items():
        require_all(
            f"{label} {surface_name} blocked response contract",
            text,
            blocked_regression["mustContainInLifecycleSkills"],
        )
    require_all(
        f"{label} workflow blocked response contract",
        workflow,
        blocked_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS blocked response contract",
            agents,
            blocked_regression["mustContainInAgentsManagedBlock"],
        )

    commit_regression = regression(contract, "r1-commit-boundary-reviewer-scope")
    require_all(
        f"{label} review-task commit boundary contract",
        review_skill,
        commit_regression["mustContainInReviewTaskSkill"],
    )
    require_all(
        f"{label} execute-plan commit boundary contract",
        execute_skill,
        commit_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow commit boundary contract",
        workflow,
        commit_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS commit boundary contract",
            agents,
            commit_regression["mustContainInAgentsManagedBlock"],
        )

    wait_regression = regression(contract, "executor-review-wait-handoff")
    require_all(
        f"{label} execute-plan wait handoff contract",
        execute_skill,
        wait_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow wait handoff contract",
        workflow,
        wait_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS wait handoff contract",
            agents,
            wait_regression["mustContainInAgentsManagedBlock"],
        )

    commit_action_regression = regression(contract, "non-blocking-commit-action-needed-format")
    require_all(
        f"{label} execute-plan commit action needed contract",
        execute_skill,
        commit_action_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow commit action needed contract",
        workflow,
        commit_action_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS commit action needed contract",
            agents,
            commit_action_regression["mustContainInAgentsManagedBlock"],
        )

    next_step_regression = regression(contract, "plan-next-step-numbered-options")
    require_all(
        f"{label} plan-task next-step numbered choices contract",
        plan_skill,
        next_step_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} workflow next-step numbered choices contract",
        workflow,
        next_step_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS next-step numbered choices contract",
            agents,
            next_step_regression["mustContainInAgentsManagedBlock"],
        )
    for bad in next_step_regression.get("forbiddenWithoutNumberedOptions", []):
        if bad in plan_skill or bad in workflow or bad in agents:
            raise AssertionError(f"{label} contains forbidden vague next-step prompt: {bad}")

    question_regression = regression(contract, "full-context-clarification-questions")
    require_all(
        f"{label} plan-task full-context question contract",
        plan_skill,
        question_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} workflow full-context question contract",
        workflow,
        question_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS full-context question contract",
            agents,
            question_regression["mustContainInAgentsManagedBlock"],
        )

    post_plan_regression = regression(contract, "post-plan-change-preparation")
    require_all(
        f"{label} execute-plan post-plan change preparation contract",
        execute_skill,
        post_plan_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow post-plan change preparation contract",
        workflow,
        post_plan_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS post-plan change preparation contract",
            agents,
            post_plan_regression["mustContainInAgentsManagedBlock"],
        )

    goal_regression = regression(contract, "codex-end-goal-goal-tool-contract")
    require_all(
        f"{label} plan-task Codex goal contract",
        plan_skill,
        goal_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} execute-plan Codex goal contract",
        execute_skill,
        goal_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow Codex goal contract",
        workflow,
        goal_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS Codex goal contract",
            agents,
            goal_regression["mustContainInAgentsManagedBlock"],
        )

    config_regression = regression(contract, "task-system-config-snapshot-and-user-verification-done")
    helper_text = read(root / "docs" / "tasks" / "task-system-helpers" / "create-plan-folder.py")
    task_config_path = root / "docs" / "tasks" / "task-system.config.yaml"
    if not task_config_path.exists():
        raise AssertionError(f"{label} missing task-system config: docs/tasks/task-system.config.yaml")
    task_config = read_simple_yaml(task_config_path)
    if task_config.get("schema") != "codex-task-system-config/v1":
        raise AssertionError(f"{label} task-system.config.yaml schema must be codex-task-system-config/v1")
    planning = task_config.get("planning", {})
    if not isinstance(planning, dict) or planning.get("defaultMode") not in {"auto", "quick", "standard", "full"}:
        raise AssertionError(f"{label} task-system.config.yaml missing planning.defaultMode")
    lifecycle = task_config.get("lifecycle", {})
    user_verification = lifecycle.get("userVerification", {}) if isinstance(lifecycle, dict) else {}
    for key in (
        "treatAsDoneForAgentWork",
        "excludeFromActiveAssignment",
        "requireExplicitFailureToReopen",
        "doNotMarkDirtyBecauseStillInUserVerification",
    ):
        if key not in user_verification:
            raise AssertionError(f"{label} task-system.config.yaml missing lifecycle.userVerification.{key}")
    require_all(
        f"{label} plan-task task-system config contract",
        plan_skill,
        config_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} execute-plan task-system config contract",
        execute_skill,
        config_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} review-task task-system config contract",
        review_skill,
        config_regression["mustContainInReviewTaskSkill"],
    )
    require_all(
        f"{label} user-verification task-system config contract",
        verification_skill,
        config_regression["mustContainInUserVerificationSkill"],
    )
    require_all(
        f"{label} workflow task-system config contract",
        workflow,
        config_regression["mustContainInWorkflow"],
    )
    require_all(
        f"{label} plan-folder helper task-system config contract",
        helper_text,
        config_regression["mustContainInHelper"],
    )
    if agents:
        require_all(
            f"{label} AGENTS task-system config contract",
            agents,
            config_regression["mustContainInAgentsManagedBlock"],
        )

    quick_fix_regression = regression(contract, "quick-fix-preflight-readiness-gate")
    quick_fix_skill = read(root / ".agents" / "skills" / "quick-fix" / "SKILL.md")
    for rel in quick_fix_regression.get("requiredFiles", []):
        if not (root / rel).exists():
            raise AssertionError(f"{label} missing quick-fix/pre-flight file: {rel}")
    for rel in quick_fix_regression.get("requiredFolders", []):
        if not (root / rel).exists():
            raise AssertionError(f"{label} missing quick-fix/pre-flight folder: {rel}")
    require_all(
        f"{label} quick-fix skill contract",
        quick_fix_skill,
        quick_fix_regression["mustContainInQuickFixSkill"],
    )
    require_all(
        f"{label} plan-task quick-fix/pre-flight contract",
        plan_skill,
        quick_fix_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} execute-plan readiness contract",
        execute_skill,
        quick_fix_regression["mustContainInExecutePlanSkill"],
    )
    require_all(
        f"{label} workflow quick-fix/pre-flight contract",
        workflow,
        quick_fix_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS quick-fix/pre-flight contract",
            agents,
            quick_fix_regression["mustContainInAgentsManagedBlock"],
        )

    helper_regression = regression(contract, "plan-folder-creation-helper")
    for rel in helper_regression.get("requiredFiles", []):
        if not (root / rel).exists():
            raise AssertionError(f"{label} missing plan-folder helper file: {rel}")
    require_all(
        f"{label} plan-task plan-folder helper contract",
        plan_skill,
        helper_regression["mustContainInPlanTaskSkill"],
    )
    require_all(
        f"{label} workflow plan-folder helper contract",
        workflow,
        helper_regression["mustContainInWorkflow"],
    )
    if agents:
        require_all(
            f"{label} AGENTS plan-folder helper contract",
            agents,
            helper_regression["mustContainInAgentsManagedBlock"],
        )


def validate_package_contract() -> None:
    if not is_source_package_layout():
        return
    contract = read_json(contract_path())
    lessons_regression = regression(contract, "path-aware-lessons-system")

    manifest = read_json(PACKAGE_ROOT / "manifest.json")
    required_seeds = set(lessons_regression["requiredSeedFiles"])
    create_if_missing = set(manifest.get("seedFilesCreateIfMissing", []))
    static_files = set(manifest.get("staticFiles", []))

    missing_seeds = sorted(required_seeds - create_if_missing)
    if missing_seeds:
        raise AssertionError(
            f"manifest seedFilesCreateIfMissing missing lesson ledgers: {missing_seeds}"
        )
    overwritten_seeds = sorted(required_seeds & static_files)
    if overwritten_seeds:
        raise AssertionError(
            f"lesson ledgers must not be static overwrite files: {overwritten_seeds}"
        )
    if manifest.get("preserveLiveLedgerFiles") is not True:
        raise AssertionError("manifest preserveLiveLedgerFiles must be true")

    for rel in required_seeds:
        if not (PACKAGE_ROOT / "files" / rel).exists():
            raise AssertionError(f"missing lesson seed file: {rel}")

    index_path = PACKAGE_ROOT / "files" / "docs" / "tasks" / "lessons-index.json"
    index = read_json(index_path)
    if index.get("version") != 1:
        raise AssertionError("lessons-index.json version must be 1")
    if index.get("purpose") != (
        "Path-aware lesson lookup for planning, execution, verification, and commit workflows."
    ):
        raise AssertionError("lessons-index.json purpose is missing or incorrect")

    protocol = index.get("lookupProtocol")
    if not isinstance(protocol, dict):
        raise AssertionError("lessons-index.json lookupProtocol must be an object")
    expected_read_first = [
        "docs/tasks/lessons-active.md",
        "docs/tasks/lessons-index.json",
    ]
    if protocol.get("readFirst") != expected_read_first:
        raise AssertionError(
            f"lessons-index.json readFirst must be {expected_read_first}"
        )
    expected_signals = {
        "task keywords from the user request",
        "expected or confirmed touched paths",
        "workflow type such as planning, execution, verification, commit, or docs",
    }
    if set(protocol.get("matchSignals", [])) != expected_signals:
        raise AssertionError("lessons-index.json matchSignals are incomplete")
    for key in ("reportingRule", "archiveRule", "promotionRule"):
        value = protocol.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AssertionError(f"lessons-index.json missing {key}")
    if not isinstance(index.get("entries"), list):
        raise AssertionError("lessons-index.json entries must be an array")

    generator_prompt = read(PACKAGE_ROOT.parent / "generate-task-system.prompt.md")
    frontmatter_regression = regression(contract, "valid-skill-yaml-frontmatter")
    require_all(
        "generator prompt skill frontmatter contract",
        generator_prompt,
        frontmatter_regression["mustContainInGeneratorPrompt"],
    )
    require_all(
        "generator prompt lessons contract",
        generator_prompt,
        lessons_regression["mustContainInGeneratorPrompt"],
    )
    commit_regression = regression(contract, "r1-commit-boundary-reviewer-scope")
    require_all(
        "generator prompt commit boundary contract",
        generator_prompt,
        commit_regression["mustContainInGeneratorPrompt"],
    )
    wait_regression = regression(contract, "executor-review-wait-handoff")
    require_all(
        "generator prompt wait handoff contract",
        generator_prompt,
        wait_regression["mustContainInGeneratorPrompt"],
    )
    commit_action_regression = regression(contract, "non-blocking-commit-action-needed-format")
    require_all(
        "generator prompt commit action needed contract",
        generator_prompt,
        commit_action_regression["mustContainInGeneratorPrompt"],
    )
    next_step_regression = regression(contract, "plan-next-step-numbered-options")
    require_all(
        "generator prompt next-step numbered choices contract",
        generator_prompt,
        next_step_regression["mustContainInGeneratorPrompt"],
    )
    question_regression = regression(contract, "full-context-clarification-questions")
    require_all(
        "generator prompt full-context question contract",
        generator_prompt,
        question_regression["mustContainInGeneratorPrompt"],
    )
    post_plan_regression = regression(contract, "post-plan-change-preparation")
    require_all(
        "generator prompt post-plan change preparation contract",
        generator_prompt,
        post_plan_regression["mustContainInGeneratorPrompt"],
    )

    goal_regression = regression(contract, "codex-end-goal-goal-tool-contract")
    require_all(
        "generator prompt Codex goal contract",
        generator_prompt,
        goal_regression["mustContainInGeneratorPrompt"],
    )

    config_regression = regression(contract, "task-system-config-snapshot-and-user-verification-done")
    create_if_missing = set(manifest.get("seedFilesCreateIfMissing", []))
    static_files = set(manifest.get("staticFiles", []))
    schema_files = set(manifest.get("schemas", []))
    for rel in config_regression.get("requiredSeedFiles", []):
        if rel not in create_if_missing:
            raise AssertionError(f"manifest seedFilesCreateIfMissing missing task-system config YAML seed: {rel}")
        if rel in static_files:
            raise AssertionError(f"task-system config YAML must not be a static overwrite file: {rel}")
        if not (PACKAGE_ROOT / "files" / rel).exists():
            raise AssertionError(f"package files missing task-system config YAML seed: {rel}")
    for rel in config_regression.get("requiredSchemaFiles", []):
        if rel not in schema_files:
            raise AssertionError(f"manifest schemas missing task-system config schema: {rel}")
        if not (PACKAGE_ROOT / rel).exists():
            raise AssertionError(f"package missing task-system config schema: {rel}")
    if manifest.get("preserveTaskSystemConfig") is not True:
        raise AssertionError("manifest preserveTaskSystemConfig must be true")
    require_all(
        "generator prompt task-system config YAML contract",
        generator_prompt,
        config_regression["mustContainInGeneratorPrompt"],
    )

    quick_fix_regression = regression(contract, "quick-fix-preflight-readiness-gate")
    manifest_static = set(manifest.get("staticFiles", []))
    manifest_folders = set(manifest.get("folders", []))
    for rel in quick_fix_regression.get("requiredFiles", []):
        if rel not in manifest_static:
            raise AssertionError(f"manifest staticFiles missing quick-fix/pre-flight file: {rel}")
        if not (PACKAGE_ROOT / "files" / rel).exists():
            raise AssertionError(f"package files missing quick-fix/pre-flight file: {rel}")
    for rel in quick_fix_regression.get("requiredFolders", []):
        if rel not in manifest_folders:
            raise AssertionError(f"manifest folders missing quick-fix/pre-flight folder: {rel}")
    require_all(
        "generator prompt quick-fix/pre-flight contract",
        generator_prompt,
        quick_fix_regression["mustContainInGeneratorPrompt"],
    )

    helper_regression = regression(contract, "plan-folder-creation-helper")
    for rel in helper_regression.get("requiredFiles", []):
        if rel not in manifest.get("staticFiles", []):
            raise AssertionError(f"manifest staticFiles missing plan-folder helper file: {rel}")
        if not (PACKAGE_ROOT / "files" / rel).exists():
            raise AssertionError(f"package files missing plan-folder helper file: {rel}")
    require_all(
        "generator prompt plan-folder helper contract",
        generator_prompt,
        helper_regression["mustContainInGeneratorPrompt"],
    )


    expected_files = read_json(PACKAGE_ROOT / "tests" / "expected-files.json")
    missing_expected = sorted(required_seeds - set(expected_files.get("files", [])))
    if missing_expected:
        raise AssertionError(
            f"expected-files.json missing lesson ledgers: {missing_expected}"
        )


def main(argv: list[str]) -> int:
    validate_package_contract()

    if is_source_package_layout():
        package_agents = read(PACKAGE_ROOT / "managed-blocks" / "AGENTS.task-system.md")
        validate_surface(
            PACKAGE_ROOT / "files",
            "docs/tasks",
            label="package",
            agents_text=package_agents,
        )

    args = argv[1:]
    if args[:1] == ["--project-root"] and len(args) >= 2:
        root_s = args[1]
        task_root = args[2] if len(args) >= 3 else "docs/tasks"
        validate_surface(Path(root_s), task_root, label=root_s)
    elif args:
        # Optional project args are root=taskRoot, for example /repo=docs/tasks.
        for arg in args:
            if "=" not in arg:
                raise SystemExit(f"expected project arg root=taskRoot or --project-root <root> [taskRoot], got: {arg}")
            root_s, task_root = arg.split("=", 1)
            validate_surface(Path(root_s), task_root, label=root_s)
    elif not is_source_package_layout():
        # Installed project layout: <project>/docs/tasks/task-system-tests/package/validate-semantic-contract.py
        inferred_project = Path(__file__).resolve().parents[4]
        validate_surface(inferred_project, "docs/tasks", label=str(inferred_project))

    print("semantic contract validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
