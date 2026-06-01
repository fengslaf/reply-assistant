import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import preview_mode as pm
from preview_adapter import PreviewModeAdapter


def test_intelligence_manager_analyzes_and_enriches_samples():
    from local_intelligence import IntelligenceManager

    manager = IntelligenceManager()
    result = manager.analyze(
        "课程多少钱",
        [
            "您好，课程费用2980元，包含30课时，支持试听和报名咨询。您可以先带孩子来体验一节课，我们再根据实际情况给您推荐更合适的班型。",
            "基础班1980元，适合入门，包含24课时，也可以先预约试听后再决定是否报名。",
        ],
    )

    assert result.intent_result.intent == "price"
    assert result.summary["sample_count"] == 2
    assert result.prompt["system_prompt"]
    assert result.prompt["user_prompt"]
    assert result.enriched_samples


def test_preview_adapter_exposes_intelligence_summary_and_v202_output(tmp_path):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "课程多少钱",
                        "replies": ["课程费用2980元，包含30课时。"],
                        "scene_tag": "问价格",
                        "keywords": ["课程", "价格"],
                    },
                    {
                        "parent_message": "老师水平怎么样",
                        "replies": ["老师都有多年教学经验。"],
                        "scene_tag": "问师资",
                        "keywords": ["老师", "师资"],
                    },
                ],
                "config": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))
    adapter = PreviewModeAdapter(manager)

    analysis = adapter.analyze_intelligence("课程多少钱")
    assert analysis["summary"]["intent"] == "price"

    result = adapter.match_v2(
        query="课程多少钱",
        top_k=3,
        inference_mode="retrieval_only",
    )

    assert "intelligence" in result
    assert result["intelligence"]["summary"]["intent"] == "price"
