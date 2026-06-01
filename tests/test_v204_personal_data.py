import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import preview_mode as pm
from preview_adapter import PreviewModeAdapter


def test_preview_manager_v204_generation_toggle_round_trip(tmp_path):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps({"samples": [], "config": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))

    assert manager.get_v204_generation_enabled() is False

    manager.set_v204_generation_enabled(True)

    reloaded = pm.PreviewModeManager(data_path=str(data_path))
    assert reloaded.get_v204_generation_enabled() is True


def test_preview_adapter_uses_v204_engine_when_enabled(tmp_path):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "价格多少",
                        "replies": ["课程费用是 2980 元。"],
                        "scene_tag": "问价格",
                        "keywords": ["价格", "费用"],
                    }
                ],
                "config": {"v204_generation_enabled": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))
    adapter = PreviewModeAdapter(manager)

    assert adapter.local_engine.__class__.__name__ == "LocalSearchEngineV204"


def test_preview_adapter_keeps_v203_engine_when_v204_disabled(tmp_path):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "价格多少",
                        "replies": ["课程费用是 2980 元。"],
                        "scene_tag": "问价格",
                        "keywords": ["价格", "费用"],
                    }
                ],
                "config": {"v204_generation_enabled": False},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))
    adapter = PreviewModeAdapter(manager)

    assert adapter.local_engine.__class__.__name__ == "LocalSearchEngine"


def test_preview_api_client_falls_back_while_v2_adapter_is_still_building(tmp_path, monkeypatch):
    data_path = tmp_path / "local_data.json"
    data_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "价格多少",
                        "replies": ["课程费用是 2980 元。"],
                        "scene_tag": "问价格",
                        "keywords": ["价格", "费用"],
                    }
                ],
                "config": {"v204_generation_enabled": False},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = pm.PreviewModeManager(data_path=str(data_path))
    client = pm.PreviewAPIClient(manager, "local_user")
    client.v2_adapter = None
    client._v2_adapter_building = True

    def fail_create():
        raise AssertionError("should not build adapter synchronously on the UI path")

    monkeypatch.setattr(client, "_create_v2_adapter", fail_create)

    result = client.generate_reply("价格多少", top_k=5)

    assert result["candidates"]
    assert result["match_type"] in {"exact", "similar", "none"}


def test_personal_record_parser_handles_compact_text():
    from personal_data import parse_personal_record

    record = parse_personal_record(
        "李萌萌13789877876五年级英语集训A物理燎原B",
        recorded_at="2026-05-20T10:00:00",
    )

    assert record["name"] == "李萌萌"
    assert record["phone"] == "13789877876"
    assert record["recorded_grade"] == "五年级"
    assert len(record["courses"]) == 2
    assert record["courses"][0]["subject"] == "英语"
    assert record["courses"][0]["class_type"] == "集训A"
    assert record["courses"][0]["stage"] == ""
    assert record["courses"][1]["subject"] == "物理"
    assert record["courses"][1]["class_type"] == "燎原B"
    assert record["courses"][1]["stage"] == ""


def test_personal_record_parser_extracts_stage_before_each_course():
    from personal_data import parse_personal_record

    record = parse_personal_record(
        "李萌萌17677882226六年级暑秋数学燎原A秋物理燎原B",
        recorded_at="2026-05-20T10:00:00",
    )

    assert len(record["courses"]) == 2
    assert record["courses"][0]["subject"] == "数学"
    assert record["courses"][0]["stage"] == "暑秋"
    assert record["courses"][0]["class_type"] == "燎原A"
    assert record["courses"][1]["subject"] == "物理"
    assert record["courses"][1]["stage"] == "秋"
    assert record["courses"][1]["class_type"] == "燎原B"


def test_grade_progression_crosses_to_high_school_and_keeps_plus_suffix():
    from personal_data import compute_display_grade

    assert compute_display_grade("初三", "2026-05-20T10:00:00", "2026-09-02T00:00:00") == "高一"
    assert compute_display_grade("高三", "2026-05-20T10:00:00", "2026-09-02T00:00:00") == "高三+1"
    assert compute_display_grade("高三", "2026-05-20T10:00:00", "2027-09-02T00:00:00") == "高三+2"


def test_personal_data_manager_searches_structured_fields(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)
    manager.clear_all_records()
    manager.import_text_lines(
        [
            "李萌萌，13789877876，五年级，英语集训A，物理燎原B",
            "王一诺 13800001111 初二 数学培优班",
        ],
        recorded_at="2026-05-20T10:00:00",
    )

    by_name = manager.search_records("李萌萌")
    by_phone = manager.search_records("13800001111")
    by_subject = manager.search_records("物理")

    assert len(by_name) == 1
    assert by_name[0]["name"] == "李萌萌"
    assert len(by_phone) == 1
    assert by_phone[0]["name"] == "王一诺"
    assert len(by_subject) == 1
    assert by_subject[0]["name"] == "李萌萌"


def test_personal_data_manager_uses_isolated_storage(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)

    assert manager.data_dir == tmp_path / "personal_data"
    assert manager.records_path == manager.data_dir / "records.json"
    assert manager.config_path == manager.data_dir / "config.json"
    assert manager.imports_dir == manager.data_dir / "imports"


def test_personal_data_manager_seeds_default_samples_and_color(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)

    records = manager.get_all_records()
    assert len(records) >= 4
    assert manager.get_result_highlight_color() == "#fff59d"
    assert any(item.get("name") == "李明轩" for item in records)


def test_personal_data_manager_can_favorite_record(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)
    before = len(manager.get_all_records())

    record = manager.add_record_from_text("赵小雨 13955556666 高一 数学拔高班")

    assert record is not None
    assert len(manager.get_all_records()) == before + 1
    assert any(item.get("phone") == "13955556666" for item in manager.get_all_records())


def test_personal_data_manager_seeds_defaults_for_existing_empty_store(tmp_path):
    from personal_data import PersonalDataManager

    data_dir = tmp_path / "personal_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "records.json").write_text("[]", encoding="utf-8")
    (data_dir / "config.json").write_text("{}", encoding="utf-8")

    manager = PersonalDataManager(base_dir=tmp_path)

    assert len(manager.get_all_records()) >= 4


def test_personal_data_manager_upgrades_default_samples_without_resetting_store(tmp_path):
    from personal_data import PersonalDataManager, parse_personal_record

    data_dir = tmp_path / "personal_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    recorded_at = "2026-05-24T19:20:00"
    records = [
        parse_personal_record("李萌萌，13789877876，五年级，英语集训A，物理燎原B", recorded_at=recorded_at),
        parse_personal_record("王一诺 13800001111 初二 数学培优班", recorded_at=recorded_at),
    ]
    (data_dir / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "config.json").write_text('{"defaults_seeded": true, "default_sample_version": 1}', encoding="utf-8")

    manager = PersonalDataManager(base_dir=tmp_path)

    all_records = manager.get_all_records()
    assert any(item.get("name") == "李明轩" for item in all_records)
    assert manager.config.get("default_sample_version") == 2


def test_personal_data_manager_hotkey_round_trip(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)

    assert manager.get_hotkey() == "ctrl+shift+y"

    manager.set_hotkey("ctrl+alt+y")

    reloaded = PersonalDataManager(base_dir=tmp_path)
    assert reloaded.get_hotkey() == "ctrl+alt+y"


def test_personal_data_manager_display_mode_round_trip(tmp_path):
    from personal_data import PersonalDataManager

    manager = PersonalDataManager(base_dir=tmp_path)

    assert manager.get_display_mode() == "table"

    manager.set_display_mode("table")

    reloaded = PersonalDataManager(base_dir=tmp_path)
    assert reloaded.get_display_mode() == "table"


def test_personal_data_manager_migrates_existing_card_mode_to_table(tmp_path):
    from personal_data import PersonalDataManager

    data_dir = tmp_path / "personal_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "records.json").write_text(
        json.dumps([{"id": "p1", "raw_text": "李萌萌 13789877876 五年级 数学燎原A"}], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (data_dir / "config.json").write_text(
        '{"display_mode": "card", "defaults_seeded": true, "default_sample_version": 2}',
        encoding="utf-8",
    )

    manager = PersonalDataManager(base_dir=tmp_path)

    assert manager.get_display_mode() == "table"
    assert manager.config.get("display_mode_migrated") is True
