"""A scripted stand-in for Claude, so agent tests are free, fast and repeatable.

Each step is a function: it gets the conversation so far and returns the assistant's
content blocks, the way Claude would. A step can read earlier tool results, e.g. to
pick a recipe id that search returned.
"""

import copy
import json
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from app.agent.model import ModelTurn
from app.llm_costs import Usage

Messages = list[dict[str, Any]]
Step = Callable[[Messages], list[dict[str, Any]]]


def text(t: str) -> dict[str, Any]:
    return {"type": "text", "text": t}


def tool(name: str, **args: Any) -> dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:12]}", "name": name, "input": args}


def results(messages: Messages) -> list[dict[str, Any]]:
    """The tool results in the latest user message."""
    return [b for b in messages[-1]["content"] if b.get("type") == "tool_result"]


def last_result(messages: Messages) -> Any:
    content = results(messages)[-1]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


class ScriptedModel:
    name = "scripted"

    def __init__(self, steps: Sequence[Step | list[dict[str, Any]]] = ()) -> None:
        self.steps = list(steps)
        self.calls: list[Messages] = []  # what the model was sent, per call
        self.parameters: dict[str, Any] = {}
        # Call number (from 0) → stop reason, to fake a "refusal" or "max_tokens".
        self.stop_reasons: dict[int, str] = {}

    async def respond(
        self,
        system: str,
        tools: Sequence[dict[str, Any]],
        messages: Sequence[dict[str, Any]],
        on_text: Callable[[str], None],
    ) -> ModelTurn:
        history = copy.deepcopy(list(messages))
        self.calls.append(history)
        if not self.steps:
            raise AssertionError("the agent called the model more times than scripted")
        step = self.steps.pop(0)
        content = step(history) if callable(step) else step
        for block in content:
            if block["type"] == "text":
                on_text(block["text"])
        uses_tools = any(b["type"] == "tool_use" for b in content)
        usage = Usage(model=self.name, input_tokens=1000, output_tokens=100)
        stop = self.stop_reasons.get(len(self.calls) - 1)
        return ModelTurn(content, stop or ("tool_use" if uses_tools else "end_turn"), usage)


class ScriptedReader:
    """Stands in for the recipe reader (the Paste door's one Haiku call). Queue answers
    in `answers`; None means "no usable answer" (refused, cut off, malformed). An
    unscripted call fails the test, so no test can reach the real Claude."""

    def __init__(self) -> None:
        self.answers: list[Any] = []  # RecipeReading | None, in call order
        self.calls: list[tuple[str, list[str]]] = []  # (text, cuisines) per call

    async def read(self, text: str, cuisines: Sequence[str]) -> tuple[Any, Usage]:
        self.calls.append((text, list(cuisines)))
        if not self.answers:
            raise AssertionError("the recipe reader was called more times than scripted")
        return self.answers.pop(0), Usage(model="scripted", input_tokens=500, output_tokens=200)
