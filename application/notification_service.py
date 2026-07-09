from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from schemas.notification import Notification


class NotificationService:
    def __init__(self, run_store: Any, read_state_path: Path):
        self.run_store = run_store
        self.read_state_path = read_state_path

    def _load_read_ids(self) -> set[str]:
        if not self.read_state_path.exists():
            return set()
        try:
            with open(self.read_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass
        return set()

    def _save_read_ids(self, read_ids: set[str]) -> None:
        try:
            self.read_state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.read_state_path, "w", encoding="utf-8") as f:
                json.dump(list(read_ids), f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_notifications(self) -> list[Notification]:
        try:
            runs_data = self.run_store.list_runs(limit=100)
            runs = runs_data.get("runs", []) if isinstance(runs_data, dict) else []
        except Exception:
            runs = []

        read_ids = self._load_read_ids()
        notifications: list[Notification] = []

        for run in runs:
            run_id = run.get("run_id")
            status = run.get("status")
            updated_at = run.get("updated_at") or run.get("created_at") or ""

            if not run_id or not status:
                continue

            notification_id = f"run_{run_id}_{status}"
            category = "info"
            title = ""
            message = ""

            if status == "needs_human_input":
                category = "warning"
                title = "設計需要人工確認 (Clarification Needed)"
                message = f"任務 {run_id} 需要您回答問題或提供進一步的規格。"
            elif status == "completed":
                category = "success"
                title = "設計任務已完成 (Design Completed)"
                message = f"任務 {run_id} 已順利生成候選方案與材料清單。"
            elif status in ("failed", "error"):
                category = "error"
                title = "設計任務失敗 (Design Failed)"
                message = f"任務 {run_id} 執行時發生錯誤。"
            elif status == "running":
                category = "info"
                title = "設計任務執行中 (Design Running)"
                message = f"任務 {run_id} 正在背景搜尋與模擬中..."
            elif status == "queued":
                category = "info"
                title = "設計任務已排程 (Design Queued)"
                message = f"任務 {run_id} 已加入佇列，等待開始。"
            elif status == "cancelled":
                category = "info"
                title = "設計任務已取消 (Design Cancelled)"
                message = f"任務 {run_id} 已被使用者手動取消。"
            else:
                continue

            is_read = notification_id in read_ids
            notifications.append(
                Notification(
                    notification_id=notification_id,
                    category=category,
                    title=title,
                    message=message,
                    read=is_read,
                    timestamp=updated_at,
                    link=f"/web/runs/{run_id}",
                )
            )

        return notifications

    def mark_as_read(self, notification_id: str) -> None:
        read_ids = self._load_read_ids()
        read_ids.add(notification_id)
        self._save_save_ids(read_ids)

    def _save_save_ids(self, read_ids: set[str]) -> None:
        # Helper to avoid typing issues with private saves
        self._save_read_ids(read_ids)

    def mark_all_as_read(self) -> None:
        notifications = self.get_notifications()
        read_ids = self._load_read_ids()
        for n in notifications:
            read_ids.add(n.notification_id)
        self._save_read_ids(read_ids)

    def get_unread_count(self) -> int:
        notifications = self.get_notifications()
        return sum(1 for n in notifications if not n.read)
