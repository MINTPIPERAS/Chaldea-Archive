import json
from typing import Any


def ndjson(event_type: str, **data: Any) -> str:
    """编码一行 NDJSON 事件（协议定义见 Docs/streaming-design.md §3）。"""
    payload = {"type": event_type, **data}
    return json.dumps(payload, ensure_ascii=False) + "\n"
