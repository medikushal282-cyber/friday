import asyncio
from typing import Dict
from datetime import datetime, timezone

event_bus: Dict[str, asyncio.Queue] = {}

def get_queue(run_id: str) -> asyncio.Queue:
    if run_id not in event_bus:
        event_bus[run_id] = asyncio.Queue()
    return event_bus[run_id]

async def emit(run_id: str, event_type: str, node: str = "", data: dict = None):
    q = get_queue(run_id)
    event = {
        "event": event_type,
        "run_id": run_id,
        "node": node,
        "ts": datetime.now(timezone.utc).isoformat(),
        "data": data if data is not None else {}
    }
    await q.put(event)
