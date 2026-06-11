# Changelog

## 2026-06-07

- Added persisted MCP run events, stage progress, cursor-based event queries, and progress summaries.
- Added human feedback submission and auditable parent-to-child run resume.
- Added MCP DesignIR materialization, compatible-part discovery, replacement validation,
  immutable part replacement, revision diff, and BOM/GenBank/SBOL3 export tools.
- Hardened concurrent run metadata writes with re-entrant locking and unique atomic temp files.
# 變更紀錄

## 2026-06-06 - Design Representation and Exchange Formats
## 2026-06-06 - 設計表示與交換格式

### Added / 新增

- Added `DesignIR` for biological parts, regulatory interactions, transcriptional units, validation status, provenance, part assignments, and immutable revisions.
- 新增 `DesignIR`，表示生物元件、調控關係、transcriptional units、驗證狀態、來源、元件映射與不可變版本。

- Added Logic, Regulatory, DNA Construct, Parts, Compare, and Export views to the Streamlit interface.
- 在 Streamlit 介面加入 Logic、Regulatory、DNA Construct、Parts、Compare 與 Export 視圖。

- External Cello execution now preserves input Verilog, output files, stdout/stderr, and an artifact manifest with SHA-256 hashes. Successful, failed, and timed-out runs are retained.
- 外部 Cello 執行現在會保存輸入 Verilog、輸出檔案、stdout/stderr，以及含 SHA-256 的 artifact manifest；成功、失敗與逾時執行都會被保留。

- Added a parser for supported Cello v2 JSON circuit and assignment artifacts.
- 新增支援 Cello v2 JSON circuit 與 assignment artifacts 的解析器。

- Added fixed demonstration library `demo-cello-library@1.0.0`.
- 新增固定版本示範元件庫 `demo-cello-library@1.0.0`。

- Added part replacement validation for type, host, gate role, sequence availability, and evidence level.
- 新增元件替換驗證，涵蓋類型、宿主、gate role、序列可用性與證據等級。

- Added immutable part replacement. Replacement creates a new `DesignRevision` without mutating the original design.
- 新增不可變元件替換；替換會建立新的 `DesignRevision`，不修改原始設計。

- Added `DesignDiff` for part, construct, maturity, and metric comparison.
- 新增 `DesignDiff`，比較元件、construct、成熟度與評分指標。

- Added BOM CSV, GenBank, and SBOL3 Turtle exporters.
- 新增 BOM CSV、GenBank 與 SBOL3 Turtle 匯出器。

### Export Rules / 匯出規則

- BOM may describe incomplete or conceptual designs.
- BOM 可以描述不完整或概念性設計。

- GenBank export is blocked when construct sequences are missing or contain non-IUPAC DNA characters.
- construct 序列缺失或含非 IUPAC DNA 字元時，GenBank 匯出會被阻擋。

- SBOL3 can represent sequence-less conceptual Components, but warnings are emitted and sequences are never invented.
- SBOL3 可表示沒有序列的概念性 Component，但會發出警告，且不會自行補入序列。

- Demonstration-library sequences are marked `illustrative` and the library evidence level is `demo_only`.
- 示範元件庫序列標示為 `illustrative`，元件庫證據等級為 `demo_only`。

- Export availability does not establish plasmid completeness, assembly readiness, biosafety, or experimental validation.
- 可匯出不代表質體完整、可組裝、生物安全或已通過實驗驗證。

### Validation / 驗證

- Added focused tests for DesignIR, Cello artifact persistence and parsing, part libraries, immutable replacement, DesignDiff, BOM, GenBank, and SBOL3.
- 新增 DesignIR、Cello artifact 保存與解析、元件庫、不可變替換、DesignDiff、BOM、GenBank 與 SBOL3 的測試。
