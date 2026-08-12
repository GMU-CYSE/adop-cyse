"""The Observability and Audit Layer described in Section D.6/G.1 of the
Final Project Notebook. It is the ONLY component in the testbed that writes
the frozen log corpus. The agent host routes every MCP tool call through
`AuditLogger.record()`, so the corpus is a complete, ordered account of
tool-call telemetry for a session, exactly as specified in
docs/LOG_SCHEMA.md.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from adop_testbed.types import AuditLogRecord, ResultStatus, ScenarioTag, ServerName


class SessionSequencer:
    """Hands out a globally increasing `seq` for one `session_id`, shared by
    every AuditLogger writing part of that session (e.g. one logger per
    scenario_tag). This is what lets `seq` be used to reconstruct full
    session order across corpus/clean/*.jsonl and corpus/poisoned/*.jsonl.
    """

    def __init__(self) -> None:
        self._n = 0
        self._lock = asyncio.Lock()

    async def next(self) -> int:
        async with self._lock:
            self._n += 1
            return self._n


class AuditLogger:
    def __init__(self, out_file: Path, session_id: str, sequencer: SessionSequencer | None = None) -> None:
        self.out_file = out_file
        self.session_id = session_id
        self.sequencer = sequencer or SessionSequencer()
        self._local_count = 0
        self._write_lock = asyncio.Lock()

    async def init(self) -> None:
        self.out_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def count(self) -> int:
        """Number of records this particular logger (file) has written."""
        return self._local_count

    async def record(
        self,
        *,
        server: ServerName,
        tool_name: str,
        arguments: dict[str, Any],
        target_resource: str,
        result_status: ResultStatus,
        scenario_tag: ScenarioTag,
        duration_ms: float,
        result_summary: str,
        task_id: str,
        annotations: list[str] | None = None,
    ) -> AuditLogRecord:
        seq = await self.sequencer.next()
        record = AuditLogRecord(
            timestamp=_utc_now_iso(),
            session_id=self.session_id,
            server=server,
            tool_name=tool_name,
            arguments=arguments,
            target_resource=target_resource,
            result_status=result_status,
            scenario_tag=scenario_tag,
            duration_ms=round(duration_ms, 3),
            result_summary=result_summary,
            task_id=task_id,
            seq=seq,
            annotations=annotations or [],
        )
        async with self._write_lock:
            self._local_count += 1
            with self.out_file.open("a", encoding="utf-8") as fh:
                fh.write(record.model_dump_json() + "\n")
        return record


def _utc_now_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@asynccontextmanager
async def stopwatch() -> AsyncIterator[dict[str, float]]:
    """Usage: `async with stopwatch() as sw: ...; sw['ms']` after the block."""
    state = {"start": time.perf_counter(), "ms": 0.0}
    try:
        yield state
    finally:
        state["ms"] = (time.perf_counter() - state["start"]) * 1000.0
