import json
import re
from pathlib import PurePosixPath
from uuid import UUID

from notesolve.domain.models import VaultChangeSet, VaultOperation, WorksheetResult

_UNSAFE_PATH_CHARS = re.compile(r'[<>:"/\\|?*#\[\]^]')
_WHITESPACE = re.compile(r"\s+")


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = _UNSAFE_PATH_CHARS.sub("-", value).strip(" .-")
    cleaned = _WHITESPACE.sub(" ", cleaned)
    return cleaned[:80] or fallback


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_vault_preview(
    *,
    document_id: UUID,
    original_filename: str,
    result: WorksheetResult,
) -> VaultChangeSet:
    subject = _safe_segment(result.document.subject, "미분류")
    unit = _safe_segment(result.document.unit or "단원 미분류", "단원 미분류")
    source_stem = _safe_segment(PurePosixPath(original_filename).stem, "학습지")
    filename = f"{source_stem}-{str(document_id)[:8]}.md"
    path = str(PurePosixPath("NoteSolve", subject, unit, filename))
    title = f"{result.document.subject} - {result.document.unit or source_stem}"

    lines = [
        "---",
        f"title: {_yaml_string(title)}",
        f"subject: {_yaml_string(result.document.subject)}",
        f"unit: {_yaml_string(result.document.unit or '')}",
        f"source: {_yaml_string(original_filename)}",
        f"notesolve_document_id: {_yaml_string(str(document_id))}",
        "tags:",
        "  - notesolve",
        "---",
        "",
        f"# {title}",
        "",
        "> [!info] NoteSolve 분석",
        f"> 문서 신뢰도: {result.document.confidence:.0%} · 문제 {len(result.problems)}개",
    ]
    if result.document.warnings:
        lines.extend(["", "> [!warning] 문서 검토 필요"])
        lines.extend(f"> - {warning}" for warning in result.document.warnings)

    for index, problem in enumerate(result.problems, start=1):
        number = problem.number or str(index)
        lines.extend([
            "",
            "---",
            "",
            f"## 문제 {number}",
            "",
            problem.question_markdown,
            "",
            "### 풀이",
            "",
            problem.solution_markdown,
            "",
            "### 정답",
            "",
            problem.answer_markdown,
            "",
            "### 검산",
            "",
            f"- 상태: **{problem.verification.status.value}**",
            f"- 방법: {problem.verification.method or '미기재'}",
            f"- 신뢰도: {problem.verification.confidence:.0%}",
        ])
        if problem.verification.details_markdown:
            lines.extend(["", problem.verification.details_markdown])
        if problem.warnings:
            lines.extend(["", "> [!warning] 검토 필요"])
            lines.extend(f"> - {warning}" for warning in problem.warnings)
        if problem.concepts:
            concept_tags = " ".join(
                f"#{_safe_segment(concept, '개념').replace(' ', '-')}"
                for concept in problem.concepts
            )
            lines.extend(["", f"개념: {concept_tags}"])

    content = "\n".join(lines).rstrip() + "\n"
    return VaultChangeSet(
        operations=[VaultOperation(operation="create", path=path, content=content)],
        requires_approval=True,
        reason="분석 결과를 과목·단원별 Obsidian Markdown 노트로 생성",
    )
