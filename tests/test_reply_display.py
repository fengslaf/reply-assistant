from __future__ import annotations

import inspect
from pathlib import Path

import personal_data as pd
import preview_mode as pm
import reply_display as rd
import start_gui as gui
from server.app.prompts.reply_prompt import parse_llm_response

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_home_model_is_free_only():
    model = gui.build_home_view_model(
        {"access_mode": "free", "display_name": ""},
        {"reply_samples": 487, "personal_records": 0},
    )

    assert model["footer_buttons"] == ["帮助", "关于"]
    assert model["top_secondary_text"] == ""
    assert model["show_secondary"] is False
    assert model["banner"] is None
    assert gui.HOME_ACCESS_MODES == {"free"}
    assert all(token not in " ".join(model["reply_lines"] + model["personal_lines"]) for token in ("local_perpetual", "monthly", "yearly"))


def test_public_run_app_routes_directly_to_local_modes():
    run_app_source = inspect.getsource(gui.run_app)

    assert "reply_assistant" in run_app_source
    assert "personal_data" in run_app_source
    assert "LoginWindow()" not in run_app_source
    assert "PreviewModeManager()" in run_app_source
    assert "LocalMainWindow(api, user_id).show()" in run_app_source


def test_public_online_snapshot_is_ignored():
    window = gui.ProductHomeWindow.__new__(gui.ProductHomeWindow)
    window._state = gui._load_home_state()
    window._online_client = gui.OnlineClient()
    window._local_license_payload = None
    window._setup_ui = lambda: None

    window._merge_online_snapshot(
        {
            "access_mode": "other",
            "subscription_plan": "custom",
            "subscription_status": "active",
            "server_status_text": "ok",
            "can_cloud_sync": True,
        },
        persist=False,
    )

    assert window._state["access_mode"] == "free"
    assert window._state["subscription_plan"] == ""
    assert window._state["subscription_status"] == ""
    assert window._state["can_cloud_sync"] is False
    assert window._state["logged_in"] is False


def test_public_build_script_stays_edition_aware():
    build_exe_source = (PROJECT_ROOT / "build_exe.py").read_text(encoding="utf-8")

    assert "get_build_edition()" in build_exe_source
    assert "online_client" not in build_exe_source
    assert "membership_license" not in build_exe_source


def test_prompt_parser_handles_five_numbered_candidates():
    content = (
        "【候选1】（温和共情型）\n"
        "第一条\n"
        "【候选2】（专业自信型）\n"
        "第二条\n"
        "【候选3】（行动推动型）\n"
        "第三条\n"
        "【候选4】（信息补充型）\n"
        "第四条\n"
        "【候选5】（柔和推进型）\n"
        "第五条"
    )

    candidates = parse_llm_response(content, [])

    assert len(candidates) == 5
    assert [c["content"] for c in candidates] == ["第一条", "第二条", "第三条", "第四条", "第五条"]
    assert candidates[0]["style_tag"] == "温和共情型"
    assert candidates[-1]["style_tag"] == "柔和推进型"


def test_reply_display_supports_custom_highlight_colors():
    preset_label, preset_color = rd.HIGHLIGHT_COLOR_OPTIONS[0]

    assert rd.highlight_color_from_label(preset_label) == preset_color
    assert rd.highlight_color_from_label(None) == rd.DEFAULT_HIGHLIGHT_COLOR


def test_public_sample_limit_is_enforced(tmp_path, monkeypatch):
    manager = pm.PreviewModeManager(data_path=str(tmp_path / "local_data.json"))
    current_count = manager.get_sample_count()
    monkeypatch.setattr(pm, "get_sample_limit", lambda: current_count)

    try:
        manager.add_sample("新的家长问题", ["新的回复"])
    except ValueError as exc:
        assert f"{current_count} 条样本" in str(exc)
    else:
        raise AssertionError("公开版样本上限未生效")


def test_public_sample_import_stops_at_limit(tmp_path, monkeypatch):
    manager = pm.PreviewModeManager(data_path=str(tmp_path / "local_data.json"))
    current_count = manager.get_sample_count()
    monkeypatch.setattr(pm, "get_sample_limit", lambda: current_count)

    imported_count = manager.import_conversations(
        [{"parent_message": "全新问题", "advisor_reply": "全新回复"}]
    )

    assert imported_count == 0
    assert manager.get_sample_count() == current_count


def test_public_customer_limit_is_enforced(tmp_path, monkeypatch):
    manager = pd.PersonalDataManager(base_dir=tmp_path)
    current_count = len(manager.records)
    monkeypatch.setattr(pd, "get_customer_limit", lambda: current_count)

    try:
        manager.add_record_from_text("赵小雨13900002222三年级数学提高班")
    except ValueError as exc:
        assert f"{current_count} 条客户记录" in str(exc)
    else:
        raise AssertionError("公开版客户上限未生效")


def test_public_customer_import_stops_at_limit(tmp_path, monkeypatch):
    manager = pd.PersonalDataManager(base_dir=tmp_path)
    current_count = len(manager.records)
    monkeypatch.setattr(pd, "get_customer_limit", lambda: current_count)

    try:
        manager.import_text_lines(["赵小雨13900002222三年级数学提高班"])
    except ValueError as exc:
        assert f"{current_count} 条客户记录" in str(exc)
    else:
        raise AssertionError("公开版客户导入上限未生效")
