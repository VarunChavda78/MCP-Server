import asyncio
import json
from datetime import datetime

# In-memory store: run_id -> workflow state dict
workflows = {}

# SSE subscribers: set of asyncio.Queue
_subscribers = set()
_lock = asyncio.Lock()

MAX_WORKFLOWS = 100


async def emit_event(run_id: str, step: str, data: dict = None):
    """Update workflow state and broadcast to all SSE subscribers."""
    now = datetime.now().isoformat()
    data = data or {}

    if run_id not in workflows:
        workflows[run_id] = {
            "run_id": run_id,
            "repo": data.get("repo", ""),
            "branch": data.get("branch", ""),
            "status": data.get("status", ""),
            "current_step": step,
            "steps": [],           # ordered list of {step, timestamp, data}
            "steps_completed": [],
            "steps_total": 5,      # Core: Received, Logs, Analyzed, Approval, Completed
            "planned_tools": [],
            "error": None,
            "analysis": None,
            "started_at": now,
            "updated_at": now,
        }

    wf = workflows[run_id]
    wf["current_step"] = step
    wf["updated_at"] = now

    # Append to step log
    wf["steps"].append({"step": step, "timestamp": now, "data": data})

    # Track completion of 5 core milestones for the progress bar
    milestones = {
        "RECEIVED", "LOGS_FETCHED", "LLM_COMPLETE", 
        "APPROVED", "REJECTED", "COMPLETED"
    }
    if step in milestones:
        # Don't double-count if events repeat
        if step not in wf["steps_completed"]:
            wf["steps_completed"].append(step)

    if step == "TOOLS_PLANNED":
        wf["planned_tools"] = data.get("tools", [])
        # We no longer recompute total based on tools to keep progress bar aligned with core UI nodes

    if step == "LLM_COMPLETE":
        wf["analysis"] = data.get("analysis")

    if step == "ERROR":
        wf["error"] = data.get("error")

    # Broadcast
    message = {
        "run_id": run_id,
        "step": step,
        "workflow": wf,
        "timestamp": now,
    }

    async with _lock:
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)

    # Cap memory
    if len(workflows) > MAX_WORKFLOWS:
        # Remove oldest completed workflows
        completed = [
            (rid, w) for rid, w in workflows.items()
            if w["current_step"] in ("COMPLETED", "ERROR", "SKIPPED")
        ]
        completed.sort(key=lambda x: x[1]["updated_at"])
        for rid, _ in completed[: len(workflows) - MAX_WORKFLOWS]:
            del workflows[rid]


async def subscribe() -> asyncio.Queue:
    q = asyncio.Queue(maxsize=256)
    async with _lock:
        _subscribers.add(q)
    return q


async def unsubscribe(q: asyncio.Queue):
    async with _lock:
        _subscribers.discard(q)
