"""
Merge queue — FIFO queue for approved tasks awaiting merge.

Prevents merge conflicts by serializing merges when multiple tasks are approved.
Tasks that pass review are queued and merged one at a time.

Queue state persisted as .sextant/merge-queue.json
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


QUEUE_FILE = ".sextant/merge-queue.json"


@dataclass
class QueueItem:
    task_id: str
    added_at: str = ""
    priority: int = 0  # 0=normal, 1=high
    state: str = "queued"  # queued | merging | merged | failed
    merged_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MergeQueue:
    dag_id: Optional[str] = None
    items: list[QueueItem] = field(default_factory=list)
    current: Optional[str] = None  # task_id currently being merged
    paused: bool = False
    history: list[QueueItem] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    @property
    def pending_count(self) -> int:
        return len(self.items)

    def enqueue(self, task_id: str, priority: int = 0) -> QueueItem:
        """Add a task to the merge queue."""
        # Check for duplicates
        for item in self.items:
            if item.task_id == task_id:
                return item

        item = QueueItem(
            task_id=task_id,
            added_at=datetime.now(tz=timezone.utc).isoformat(),
            priority=priority,
        )
        self.items.append(item)
        # Sort by priority (high first) then by added_at
        self.items.sort(key=lambda x: (-x.priority, x.added_at))
        return item

    def dequeue(self) -> Optional[QueueItem]:
        """Remove and return the next task from the queue."""
        if not self.items:
            return None
        return self.items.pop(0)

    def start_merge(self, task_id: str) -> Optional[QueueItem]:
        """Mark a task as currently being merged."""
        for item in self.items:
            if item.task_id == task_id:
                item.state = "merging"
                self.current = task_id
                return item
        return None

    def complete_merge(self, task_id: str, success: bool, error: str = "") -> None:
        """Mark a merge as complete and move to history."""
        if self.current == task_id:
            self.current = None

        # Find the item (might be in items or history)
        for lst in [self.items, self.history]:
            for item in lst:
                if item.task_id == task_id:
                    item.state = "merged" if success else "failed"
                    item.merged_at = datetime.now(tz=timezone.utc).isoformat()
                    if error:
                        item.error = error
                    self.history.append(item)
                    if item in self.items:
                        self.items.remove(item)
                    return

    def clear_completed(self) -> int:
        """Remove all completed items from history. Returns count removed."""
        before = len(self.history)
        self.history = [i for i in self.history if i.state not in ("merged", "failed")]
        return before - len(self.history)

    def get_position(self, task_id: str) -> Optional[int]:
        """Get the queue position for a task (0-indexed). Returns None if not queued."""
        for i, item in enumerate(self.items):
            if item.task_id == task_id:
                return i
        return None


# ── Persistence ───────────────────────────────────────────────────────

def load_queue(path: Optional[Path] = None) -> MergeQueue:
    """Load the merge queue from disk."""
    if path is None:
        path = Path(QUEUE_FILE)

    if not path.exists():
        return MergeQueue()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MergeQueue(
            dag_id=data.get("dag_id"),
            items=[QueueItem(**i) for i in data.get("items", [])],
            current=data.get("current"),
            paused=data.get("paused", False),
            history=[QueueItem(**i) for i in data.get("history", [])],
        )
    except (json.JSONDecodeError, TypeError):
        return MergeQueue()


def save_queue(queue: MergeQueue, path: Optional[Path] = None) -> None:
    """Persist the merge queue to disk."""
    if path is None:
        path = Path(QUEUE_FILE)

    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "dag_id": queue.dag_id,
        "items": [asdict(i) for i in queue.items],
        "current": queue.current,
        "paused": queue.paused,
        "history": [asdict(i) for i in queue.history],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Display ───────────────────────────────────────────────────────────

def format_queue(queue: MergeQueue) -> str:
    """Format queue state for display."""
    lines = [
        f"Merge Queue",
        f"  Pending: {queue.pending_count}",
        f"  Current:  {queue.current or 'none'}",
        f"  Paused:   {'yes' if queue.paused else 'no'}",
        "",
    ]

    if queue.items:
        lines.append("  Queued:")
        for i, item in enumerate(queue.items):
            prio = " [HIGH]" if item.priority > 0 else ""
            lines.append(f"    {i + 1}. {item.task_id}{prio}  ({item.added_at[:19]})")
    else:
        lines.append("  (queue empty)")

    if queue.history:
        recent = queue.history[-10:]
        lines.append("")
        lines.append("  Recent history:")
        for item in reversed(recent):
            status = "\u2713" if item.state == "merged" else "\u2717"
            lines.append(f"    {status} {item.task_id}  [{item.state}]")

    return "\n".join(lines)
