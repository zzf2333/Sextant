"""Tests for cli.merge_queue — merge queue management."""
from __future__ import annotations
from cli.merge_queue import (
    MergeQueue,
    QueueItem,
    load_queue,
    save_queue,
    format_queue,
)
import tempfile
from pathlib import Path


class TestQueueItem:
    def test_create(self):
        item = QueueItem(task_id="task-1")
        assert item.task_id == "task-1"
        assert item.state == "queued"
        assert item.priority == 0

    def test_high_priority(self):
        item = QueueItem(task_id="urgent", priority=1)
        assert item.priority == 1


class TestMergeQueue:
    def test_new_queue_is_empty(self):
        q = MergeQueue()
        assert q.is_empty
        assert q.pending_count == 0
        assert q.current is None
        assert not q.paused

    def test_enqueue(self):
        q = MergeQueue()
        q.enqueue("task-a")
        assert q.pending_count == 1
        assert q.items[0].task_id == "task-a"

    def test_enqueue_duplicate(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.enqueue("task-a")
        assert q.pending_count == 1

    def test_enqueue_sorts_by_priority(self):
        q = MergeQueue()
        q.enqueue("normal", priority=0)
        q.enqueue("urgent", priority=1)
        assert q.items[0].task_id == "urgent"

    def test_dequeue(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.enqueue("task-b")
        item = q.dequeue()
        assert item.task_id == "task-a"
        assert q.pending_count == 1

    def test_dequeue_empty(self):
        q = MergeQueue()
        assert q.dequeue() is None

    def test_start_merge(self):
        q = MergeQueue()
        q.enqueue("task-a")
        item = q.start_merge("task-a")
        assert item.state == "merging"
        assert q.current == "task-a"

    def test_complete_merge_success(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.start_merge("task-a")
        q.complete_merge("task-a", success=True)
        assert q.current is None
        assert q.pending_count == 0
        assert len(q.history) == 1
        assert q.history[0].state == "merged"

    def test_complete_merge_failure(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.start_merge("task-a")
        q.complete_merge("task-a", success=False, error="conflict")
        assert q.history[0].state == "failed"
        assert q.history[0].error == "conflict"

    def test_get_position(self):
        q = MergeQueue()
        q.enqueue("a")
        q.enqueue("b")
        q.enqueue("c")
        assert q.get_position("a") == 0
        assert q.get_position("b") == 1
        assert q.get_position("c") == 2
        assert q.get_position("nonexistent") is None

    def test_clear_completed(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.start_merge("task-a")
        q.complete_merge("task-a", success=True)
        assert len(q.history) == 1
        removed = q.clear_completed()
        assert removed == 1
        assert len(q.history) == 0

    def test_pause_resume(self):
        q = MergeQueue()
        assert not q.paused
        q.paused = True
        assert q.paused
        q.paused = False
        assert not q.paused


class TestQueuePersistence:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "merge-queue.json"
            q = MergeQueue(dag_id="test-dag")
            q.enqueue("task-a")
            q.enqueue("task-b")
            q.enqueue("task-c")
            q.start_merge("task-a")
            q.complete_merge("task-a", success=True)

            save_queue(q, path)

            loaded = load_queue(path)
            assert loaded.dag_id == "test-dag"
            assert loaded.pending_count == 2
            assert len(loaded.history) == 1
            assert loaded.history[0].task_id == "task-a"

    def test_load_nonexistent(self):
        q = load_queue(Path("/nonexistent/queue.json"))
        assert q.is_empty

    def test_roundtrip_priority_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            q = MergeQueue()
            q.enqueue("normal", priority=0)
            q.enqueue("urgent", priority=1)
            q.enqueue("also-normal", priority=0)

            save_queue(q, path)
            loaded = load_queue(path)

            assert loaded.items[0].task_id == "urgent"  # high priority first
            assert loaded.pending_count == 3


class TestFormatQueue:
    def test_empty_queue(self):
        output = format_queue(MergeQueue())
        assert "empty" in output.lower() or "pending: 0" in output.lower()

    def test_queue_with_items(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.enqueue("task-b")
        output = format_queue(q)
        assert "task-a" in output
        assert "task-b" in output
        assert "Pending: 2" in output

    def test_queue_with_history(self):
        q = MergeQueue()
        q.enqueue("task-a")
        q.start_merge("task-a")
        q.complete_merge("task-a", success=True)
        output = format_queue(q)
        assert "task-a" in output
        assert "merged" in output
