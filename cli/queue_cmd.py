"""
sextant queue — merge queue management.

Commands:
  sextant queue list             — show queue status
  sextant queue add --task-id    — add task to queue
  sextant queue remove --task-id — remove task from queue
  sextant queue process          — process queue (merge one at a time)
  sextant queue pause/resume     — pause/resume processing
  sextant queue clear            — clear completed history
"""
from __future__ import annotations
import sys
from pathlib import Path

from cli.merge_queue import (
    MergeQueue,
    load_queue,
    save_queue,
    format_queue,
)


def run_queue(args) -> int:
    action = getattr(args, "action", "list")
    task_id = getattr(args, "task_id", None)
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()

    queue_path = Path(".sextant/merge-queue.json")
    queue = load_queue(queue_path)

    if action == "list":
        print(format_queue(queue))
        return 0

    elif action == "add":
        if not task_id:
            print("Usage: sextant queue add --task-id <id>")
            return 1
        item = queue.enqueue(task_id)
        save_queue(queue, queue_path)
        print(f"  Added to queue: {task_id} (position: {queue.get_position(task_id)!r})")
        print(f"  Queue length: {queue.pending_count}")
        return 0

    elif action == "remove":
        if not task_id:
            print("Usage: sextant queue remove --task-id <id>")
            return 1
        before = queue.pending_count
        queue.items = [i for i in queue.items if i.task_id != task_id]
        if len(queue.items) == before:
            print(f"  Task '{task_id}' not in queue")
            return 1
        save_queue(queue, queue_path)
        print(f"  Removed from queue: {task_id}")
        return 0

    elif action == "process":
        return _process_queue(queue, queue_path)

    elif action == "pause":
        queue.paused = True
        save_queue(queue, queue_path)
        print("  Queue paused")
        return 0

    elif action == "resume":
        queue.paused = False
        save_queue(queue, queue_path)
        print("  Queue resumed")
        return 0

    elif action == "clear":
        removed = queue.clear_completed()
        save_queue(queue, queue_path)
        print(f"  Cleared {removed} completed item(s) from history")
        return 0

    else:
        print(f"  Unknown action: {action}")
        print("  Use: list, add, remove, process, pause, resume, clear")
        return 1


def _process_queue(queue: MergeQueue, queue_path: Path) -> int:
    """Process the merge queue sequentially."""
    if queue.paused:
        print("  Queue is paused. Run 'sextant queue resume' to continue.")
        print(format_queue(queue))
        return 1

    if queue.is_empty:
        print("  Queue is empty.")
        print(format_queue(queue))
        return 0

    import subprocess
    from cli.worktree import get_repo_root, has_uncommitted_changes
    from cli.state import TaskState, load_state
    from pathlib import Path

    repo_root = get_repo_root()
    if has_uncommitted_changes(repo_root):
        print("  Error: uncommitted changes in repo. Commit or stash first.")
        return 1

    states_dir = Path(".sextant/states")
    processed = 0
    while not queue.is_empty and not queue.paused:
        item = queue.dequeue()
        if item is None:
            break

        # Validate state — must be APPROVED before merging
        state_record = load_state(states_dir, item.task_id)
        if state_record.state != TaskState.APPROVED:
            print(f"\n  Skipping {item.task_id}: state is {state_record.state.value} (need APPROVED)")
            queue.complete_merge(item.task_id, success=False,
                                 error=f"state is {state_record.state.value}, expected APPROVED")
            continue

        queue.start_merge(item.task_id)
        print(f"\n  Processing: {item.task_id}")

        # Run merge
        branch_name = f"sextant/task/{item.task_id}"
        try:
            result = subprocess.run(
                ["git", "merge", "--no-ff", branch_name,
                 "-m", f"sextant: merge {item.task_id}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                queue.complete_merge(item.task_id, success=True)
                print(f"    \u2713 Merged {branch_name}")
                processed += 1
            else:
                queue.complete_merge(
                    item.task_id, success=False,
                    error=result.stderr[:200],
                )
                print(f"    \u2717 Merge conflict for {item.task_id}")
                print(f"    {result.stderr[:200]}")
                print(f"\n  Queue stopped — resolve conflicts manually.")
                queue.paused = True

        except Exception as e:
            queue.complete_merge(item.task_id, success=False, error=str(e))
            print(f"    \u2717 Error: {e}")
            queue.paused = True

        save_queue(queue, queue_path)

    print(f"\n  Processed: {processed} task(s)")
    print(format_queue(queue))
    return 0
