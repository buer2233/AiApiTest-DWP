"""每次构建独立证据目录及原子 JSON 写入。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Mapping

from .security import Redactor


class EvidenceStore:
    def __init__(self, root: Path, redactor: Redactor | None = None):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.redactor = redactor or Redactor()

    def path(self, name: str) -> Path:
        candidate = (self.root / name).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("evidence path escapes evidence root")
        return candidate

    def write_json(self, name: str, payload: Mapping[str, object]) -> Path:
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_payload = self.redactor.mapping(payload)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
        return path

    def write_text(self, name: str, value: object) -> Path:
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(self.redactor.text(value).rstrip() + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return path

    def write_stage_result(self, name: str, payload: object) -> Path:
        if hasattr(payload, "to_dict"):
            value = payload.to_dict()
        elif is_dataclass(payload):
            value = asdict(payload)
        else:
            value = dict(payload)
        return self.write_json(f"{name}.json", value)

    def read_stage_result(self, name: str) -> dict[str, object] | None:
        path = self.path(f"{name}.json")
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_stage_results(self) -> list[dict[str, object]]:
        order = {name: index for index, name in enumerate(("preflight", "dependencies", "deploy", "health", "tests"))}
        values = []
        for path in self.root.glob("*.json"):
            if path.name.startswith("platform-bootstrap-"):
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and "stage" in value:
                values.append(value)
        return sorted(values, key=lambda item: (order.get(str(item.get("stage")), 99), str(item.get("stage"))))
