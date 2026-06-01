import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import preview_mode as pm
from preview_adapter import PreviewModeAdapter


def test_adapter_exposes_context_and_cluster_helpers(tmp_path):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "怎么退款",
                        "replies": ["请提供订单号"],
                        "scene_tag": "退款",
                        "keywords": ["退款", "订单"],
                    }
                ],
                "config": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))
    adapter = PreviewModeAdapter(manager)

    assert adapter.get_context_summary() is not None
    assert adapter.cluster_saved_samples() is not None
