from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Any

from application.services import get_default_services
from schemas.design_diff import compare_designs
from schemas.design_ir import DesignIR
from schemas.import_draft import (
    DraftPart,
    FieldEvidence,
    ImportDraft,
    validate_import_draft,
)


SOURCE_TYPES = ["literature", "repository", "GenBank", "SBOL", "manual", "other"]
EVIDENCE_STATUSES = [
    "explicit",
    "derived",
    "inferred",
    "assumed",
    "not_reported",
    "unknown",
]
VALIDATION_STATUSES = [
    "experimentally_validated",
    "partially_validated",
    "computational_only",
    "reported_without_raw_data",
    "not_reported",
    "unknown",
]
PART_TYPES = ["promoter", "RBS", "CDS", "terminator", "sensor", "regulator", "other"]


def ensure_external_import_state(session_state: Any) -> None:
    services = get_default_services()
    if "external_import_draft" not in session_state:
        session_state.external_import_draft = ImportDraft.empty()
    if "external_designs" not in session_state:
        session_state.external_designs = services.designs.list()
    if "external_import_message" not in session_state:
        session_state.external_import_message = None


def render_external_import_sidebar(st: Any) -> None:
    ensure_external_import_state(st.session_state)
    with st.expander("外部設計導入 v1", expanded=False):
        st.caption("從論文或資料庫建立可追溯草稿；未知資料可保留為 unknown。")
        mode = st.radio(
            "導入方式",
            ["引導式輸入", "檔案上傳"],
            horizontal=True,
            key="external_import_mode",
        )
        if mode == "檔案上傳":
            _render_file_upload(st)
        else:
            _render_guided_form(st)


def render_external_import_workspace(
    st: Any,
    generated_designs: list[DesignIR] | None = None,
) -> None:
    ensure_external_import_state(st.session_state)
    draft = st.session_state.external_import_draft
    designs: list[DesignIR] = st.session_state.external_designs
    message = st.session_state.external_import_message

    with st.expander(
        f"外部設計工作區 ({len(designs)} 個已確認設計)",
        expanded=bool(draft.name or designs),
    ):
        if message:
            level, text = message
            getattr(st, level)(text)
            st.session_state.external_import_message = None
        draft_tab, library_tab, compare_tab = st.tabs(
            ["草稿審查", "已導入設計", "橫向比較"]
        )
        with draft_tab:
            _render_draft_review(st, draft)
        with library_tab:
            _render_design_library(st, designs)
        with compare_tab:
            _render_comparison(st, designs, generated_designs or [])


def _render_guided_form(st: Any) -> None:
    draft: ImportDraft = st.session_state.external_import_draft
    with st.form("external_design_basic_form"):
        st.markdown("**1. 來源與基本資料**")
        name = st.text_input("設計名稱", value=draft.name)
        source_type = st.selectbox(
            "來源類型",
            SOURCE_TYPES,
            index=_safe_index(SOURCE_TYPES, draft.source_type),
        )
        source_uri = st.text_input("DOI、URL 或資料庫識別碼", value=draft.source_uri or "")
        citation = st.text_area("引用資訊", value=draft.citation, height=70)

        st.markdown("**2. 電路與宿主**")
        host = st.text_input("宿主或菌株", value=draft.host_organism)
        inputs = st.text_input("輸入，以逗號分隔", value=", ".join(draft.inputs))
        outputs = st.text_input("輸出，以逗號分隔", value=", ".join(draft.outputs))
        logic_expression = st.text_area(
            "Boolean expression 或邏輯描述",
            value=draft.logic_expression,
            height=70,
        )

        st.markdown("**3. 實驗證據**")
        validation_status = st.selectbox(
            "驗證狀態",
            VALIDATION_STATUSES,
            index=_safe_index(VALIDATION_STATUSES, draft.validation_status),
        )
        validation_notes = st.text_area(
            "觀測結果或驗證說明",
            value=draft.validation_notes,
            height=70,
        )
        evidence_status = st.selectbox("上述資料的證據狀態", EVIDENCE_STATUSES)
        locator = st.text_input("論文位置，例如 Figure 2、Methods p.4")
        submitted = st.form_submit_button("更新草稿", use_container_width=True)

    if submitted:
        draft.name = name.strip()
        draft.source_type = source_type
        draft.source_uri = source_uri.strip() or None
        draft.citation = citation.strip()
        draft.host_organism = host.strip() or "unknown"
        draft.inputs = _comma_list(inputs)
        draft.outputs = _comma_list(outputs)
        draft.logic_expression = logic_expression.strip()
        draft.validation_status = validation_status
        draft.validation_notes = validation_notes.strip()
        draft.evidence = [
            FieldEvidence(
                field_path="design_summary",
                status=evidence_status,
                source_uri=draft.source_uri,
                locator=locator.strip() or None,
                note="Evidence record for the guided import summary.",
            )
        ]
        st.session_state.external_import_message = ("success", "外部設計草稿已更新。")

    st.markdown("**4. 生物元件（選填）**")
    with st.form("external_design_part_form", clear_on_submit=True):
        part_name = st.text_input("元件名稱")
        part_type = st.selectbox("元件類型", PART_TYPES)
        part_role = st.text_input("功能或角色")
        part_sequence = st.text_area("DNA 序列（選填）", height=60)
        part_evidence = st.selectbox("元件證據狀態", EVIDENCE_STATUSES)
        part_locator = st.text_input("元件來源位置")
        add_part = st.form_submit_button("加入元件", use_container_width=True)

    if add_part:
        if not part_name.strip():
            st.session_state.external_import_message = ("error", "元件名稱不可空白。")
        else:
            part_id = _unique_part_id(draft, part_name)
            draft.parts.append(
                DraftPart(
                    id=part_id,
                    name=part_name.strip(),
                    part_type=part_type,
                    role=part_role.strip(),
                    sequence=part_sequence.strip() or None,
                    host_compatibility=(
                        [] if draft.host_organism == "unknown" else [draft.host_organism]
                    ),
                    evidence=FieldEvidence(
                        field_path=f"parts.{part_id}",
                        status=part_evidence,
                        source_uri=draft.source_uri,
                        locator=part_locator.strip() or None,
                    ),
                )
            )
            st.session_state.external_import_message = (
                "success",
                f"已加入元件 {part_name.strip()}。",
            )


def _render_file_upload(st: Any) -> None:
    uploaded = st.file_uploader(
        "上傳外部設計 JSON 或 GenBank",
        type=["json", "gb", "gbk", "genbank"],
        key="external_design_file_upload",
    )
    if uploaded is not None and st.button(
        "載入為草稿",
        use_container_width=True,
        key="load_external_json",
    ):
        try:
            if uploaded.name.lower().endswith(".json"):
                draft = get_default_services().imports.import_json(uploaded.getvalue())
            else:
                draft = get_default_services().imports.import_genbank(
                    uploaded.getvalue(),
                    filename=uploaded.name,
                )
            st.session_state.external_import_draft = draft
            st.session_state.external_import_message = (
                "success",
                f"已載入 {uploaded.name}，請在工作區確認內容。",
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            st.session_state.external_import_message = (
                "error",
                f"檔案無法載入：{exc}",
            )

    template = ImportDraft.empty()
    template.name = "Example literature circuit"
    template.inputs = ["A", "B"]
    template.outputs = ["GFP"]
    template.logic_expression = "GFP = A AND NOT B"
    st.download_button(
        "下載 JSON 範本",
        data=template.to_json(),
        file_name="external_design_import_template.json",
        mime="application/json",
        use_container_width=True,
    )


def _render_draft_review(st: Any, draft: ImportDraft) -> None:
    validation = validate_import_draft(draft)
    cols = st.columns(3)
    cols[0].metric("資料完整度", f"{validation.completeness:.0%}")
    cols[1].metric("證據品質", f"{validation.evidence_quality:.0%}")
    cols[2].metric("可評估區段", str(len(validation.applicable_sections)))
    st.markdown(f"**名稱：** {draft.name or '未填寫'}")
    st.markdown(
        f"**邏輯：** `{draft.logic_expression or '未填寫'}`  \n"
        f"**輸入：** {', '.join(draft.inputs) or '未填寫'}  \n"
        f"**輸出：** {', '.join(draft.outputs) or '未填寫'}  \n"
        f"**宿主：** {draft.host_organism}"
    )
    st.caption("可評估區段：" + ", ".join(validation.applicable_sections or ["無"]))
    for error in validation.errors:
        st.error(error)
    for warning in validation.warnings:
        st.warning(warning)
    if draft.parts:
        st.dataframe(
            [
                {
                    "id": part.id,
                    "name": part.name,
                    "type": part.part_type,
                    "sequence": "available" if part.sequence else "missing",
                    "evidence": part.evidence.status if part.evidence else "unknown",
                }
                for part in draft.parts
            ],
            use_container_width=True,
            hide_index=True,
        )

    left, right = st.columns(2)
    with left:
        st.download_button(
            "匯出草稿 JSON",
            data=draft.to_json(),
            file_name=f"{_slug(draft.name or draft.draft_id)}.json",
            mime="application/json",
            use_container_width=True,
        )
    with right:
        if st.button(
            "確認並導入 DesignIR",
            type="primary",
            disabled=not validation.can_import,
            use_container_width=True,
            key="confirm_external_import",
        ):
            design = get_default_services().imports.confirm(draft)
            designs: list[DesignIR] = st.session_state.external_designs
            designs[:] = [
                item for item in designs if item.design_id != design.design_id
            ]
            designs.append(design)
            st.session_state.external_import_message = (
                "success",
                f"已導入 {design.name}。原始草稿與證據資訊已保留。",
            )
    with st.expander("草稿原始資料", expanded=False):
        st.json(draft.to_dict())


def _render_design_library(st: Any, designs: list[DesignIR]) -> None:
    if not designs:
        st.info("尚未確認任何外部設計。")
        return
    labels = [f"{design.name} ({design.design_id})" for design in designs]
    selected = st.selectbox("選擇外部設計", labels, key="external_design_select")
    design = designs[labels.index(selected)]
    cols = st.columns(4)
    cols[0].metric("Inputs", len(design.inputs))
    cols[1].metric("Outputs", len(design.outputs))
    cols[2].metric("Parts", len(design.parts))
    cols[3].metric("Constructs", len(design.constructs))
    st.code(design.logic_expression or "Logic expression unavailable", language="text")
    st.json(design.validation_status)
    for warning in design.warnings:
        st.warning(warning)
    st.download_button(
        "匯出 DesignIR JSON",
        data=json.dumps(design.to_dict(), indent=2, ensure_ascii=False),
        file_name=f"{_slug(design.name)}_design_ir.json",
        mime="application/json",
        use_container_width=True,
    )


def _render_comparison(
    st: Any,
    external_designs: list[DesignIR],
    generated_designs: list[DesignIR],
) -> None:
    entries = [
        (f"外部：{design.name} ({design.design_id})", design)
        for design in external_designs
    ]
    entries.extend(
        (f"生成：{design.name} ({design.design_id})", design)
        for design in generated_designs
    )
    if len(entries) < 2:
        st.info("至少需要兩個外部或系統生成設計才能進行橫向比較。")
        return
    labels = [label for label, _ in entries]
    left_col, right_col = st.columns(2)
    with left_col:
        left_label = st.selectbox("設計 A", labels, key="external_compare_left")
    with right_col:
        right_label = st.selectbox(
            "設計 B",
            labels,
            index=1,
            key="external_compare_right",
        )
    if left_label == right_label:
        st.warning("請選擇兩個不同的設計。")
        return
    design_map = dict(entries)
    diff = compare_designs(
        design_map[left_label],
        design_map[right_label],
    )
    st.info(diff.summary)
    st.json(asdict(diff))


def _comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _unique_part_id(draft: ImportDraft, name: str) -> str:
    base = _slug(name) or "part"
    existing = {part.id for part in draft.parts}
    candidate = base
    index = 2
    while candidate in existing:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()


def _safe_index(options: list[str], value: str) -> int:
    try:
        return options.index(value)
    except ValueError:
        return 0
