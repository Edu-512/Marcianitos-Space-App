"""Session-local conversation state and event mapping for Don Surco."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from utils.ai_chat import ChatEvent

MAX_PROMPT = 2000

@dataclass
class ChatSession:
    messages: list[dict[str, Any]] = field(default_factory=list)
    iterator: Iterator[ChatEvent] | None = None
    busy: bool = False
    starting: bool = False
    request_id: str = ""
    context: str = ""

    def history(self) -> list[dict[str, str]]:
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages if m["content"] and not m.get("error")
        ]

    def begin(self, text: str, request_id: str, context: str) -> bool:
        text = text.strip()
        if self.busy or not text or len(text) > MAX_PROMPT or not request_id or request_id == self.request_id:
            return False
        self.request_id = request_id
        self.context = context
        self.messages.extend([
            {"role": "user", "content": text},
            {"role": "assistant", "content": "", "steps": []},
        ])
        self.messages = self.messages[-40:]
        self.busy = self.starting = True
        return True

    def cancel(self) -> None:
        if self.iterator is not None:
            getattr(self.iterator, "close", lambda: None)()
        self.iterator = None
        if self.busy:
            self.messages[-1].update(content="La consulta se detuvo porque cambió el lote o la estrategia. Puedes volver a preguntar.", error=True)
        self.busy = self.starting = False

    def advance(self) -> None:
        """Consume one backend event; never invent token-level streaming."""
        if not self.busy or self.iterator is None:
            return
        try:
            event = next(self.iterator)
        except StopIteration:
            event = ChatEvent("error")
        except Exception:
            event = ChatEvent("error")
        message = self.messages[-1]
        if event.kind == "tool":
            message["steps"].append({"label": event.label, "payload": event.payload})
            return
        if event.kind == "final":
            message["content"] = str(event.payload or "No encontré una respuesta. Intenta con otra pregunta.")
        else:
            message.update(content="No pude completar la consulta. Inténtalo de nuevo en un momento.", error=True)
        self.busy = False
        if self.iterator is not None:
            getattr(self.iterator, "close", lambda: None)()
        self.iterator = None
