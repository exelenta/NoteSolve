import json
from pathlib import Path

import pytest
from notesolve.domain.models import AnalyzeOptions, InputFile
from notesolve.providers.fake_analyzer import FakeWorksheetAnalyzer


@pytest.mark.asyncio
async def test_versioned_worksheet_eval_fixtures() -> None:
    root = Path(__file__).resolve().parents[3] / "evals" / "worksheet"
    fixtures = sorted(root.glob("*.json"))
    assert fixtures, "At least one worksheet evaluation fixture is required"

    analyzer = FakeWorksheetAnalyzer()
    for path in fixtures:
        case = json.loads(path.read_text(encoding="utf-8"))
        result = await analyzer.analyze(
            [InputFile(
                storage_key="eval.png",
                content_type="image/png",
                original_filename="eval.png",
                content=b"eval",
            )],
            AnalyzeOptions(subject_hint=case["subject_hint"]),
        )
        expected = case["expected"]
        assert result.document.subject == expected["subject"], case["case_id"]
        assert len(result.problems) == expected["problem_count"], case["case_id"]
        assert expected["answer_contains"] in result.problems[0].answer_markdown
        assert result.problems[0].confidence >= expected["minimum_confidence"]
