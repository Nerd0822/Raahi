"""OpenAI-compatible chat client using only the standard library.

Works with any provider that exposes `/chat/completions` (OpenAI, OpenRouter,
Groq, Together, local Ollama, …). Configure via the root `.env`:

    LLM_API_KEY=...
    LLM_BASE_URL=https://api.openai.com/v1
    LLM_MODEL=gpt-4o-mini

`LLM_API_KEY` is optional for local servers that don't check auth.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date

from .tools import TOOL_SPECS, execute_tool

DEFAULT_BASE_URL = "https://api.openai.com/v1"

SYSTEM_PROMPT = (
    "You are Raahi, a concise travel companion. Answer in 2-3 short sentences. "
    "Prefer practical advice about places, food, routes, timing and costs in India. "
    "Use the weather, web search and Wikipedia tools when an answer depends on "
    "current conditions, opening details or historical background; otherwise "
    "answer directly. Use at most three tool calls per answer, never repeat the "
    "same call, and answer with what you have if a tool returns nothing."
)

ITINERARY_PROMPT = """You are Raahi, an India-first travel planner. Turn the \
traveller's request into a realistic day-by-day itinerary.

Return ONLY a JSON object with this exact shape:
{
  "title": "short trip title, max 80 characters",
  "destination": "city or region, max 80 characters",
  "summary": "2-3 sentence overview of the trip",
  "days": [
    {
      "title": "theme for the day, max 80 characters",
      "items": [
        {
          "time": "HH:MM in 24-hour time",
          "category": "place | food | restaurant | transport | flight | stay | other",
          "name": "short stop name, max 120 characters",
          "notes": "one or two practical sentences: what to see or order, timing tips, bookings",
          "cost": 0
        }
      ]
    }
  ]
}

Rules:
- 2 to 4 stops per day, in chronological order.
- Respect the traveller's dates, duration, budget, pace and starting point.
- If no duration is given, plan 3 days.
- Costs are rough per-person estimates in Indian rupees (plain numbers, no
  currency symbols); use null when a cost does not apply.
- Use the categories exactly as listed.
- Prefer well-known places, local food and realistic travel time.
- Use get_weather for outdoor plans in the forecast window, search_web for
  current opening hours or ticket details, and get_wikipedia for historical
  context when it improves the plan. Do not invent facts a tool can check.
- Use at most three tool calls in total. Never repeat a call; if a tool returns
  nothing, continue with the information you already have.
- No markdown, commentary or code fences outside the JSON object."""


class LLMNotConfigured(Exception):
    """No model is configured; the API should tell the client to set one."""


class LLMError(Exception):
    """The provider rejected the call or was unreachable."""


def _complete(messages, temperature, timeout, json_mode=False, tools=None):
    """POST a chat completion and return the assistant's final text.

    When `tools` is supplied, up to three tool calls are executed and fed back
    to the model, then tools are removed from the payload so the model must
    answer with what it has.
    """
    base = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    key = os.getenv("LLM_API_KEY", "").strip()
    if not model:
        raise LLMNotConfigured("Set LLM_MODEL in .env to enable the AI guide.")

    conversation = list(messages)
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    calls_used = 0
    seen = set()
    for _ in range(5):
        allow_tools = bool(tools) and calls_used < 3
        payload = {
            "model": model,
            "messages": conversation,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        # Some OpenAI-compatible servers ignore tool_choice, so the final
        # round drops tools altogether rather than trusting "none".
        if allow_tools:
            payload["tools"] = tools

        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                data = json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:300]
            raise LLMError(f"provider returned {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(f"provider unreachable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError("provider returned invalid JSON") from exc

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("provider returned an unexpected shape") from exc

        calls = message.get("tool_calls")
        if not calls:
            content = (message.get("content") or "").strip()
            if not content:
                raise LLMError("provider returned an empty reply")
            return content

        clean_calls = []
        for index, call in enumerate(calls):
            function = call.get("function") or {}
            clean_calls.append(
                {
                    "id": call.get("id") or f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": function.get("name") or "",
                        "arguments": function.get("arguments") or "{}",
                    },
                }
            )

        if not allow_tools:
            # Some providers return tool calls even when `tools` is omitted.
            # Feed the refusal back and ask for a final answer instead of
            # failing the whole request.
            content = (message.get("content") or "").strip()
            if content:
                return content
            conversation.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": clean_calls,
                }
            )
            for call in clean_calls:
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(
                            {"error": "tool limit reached; answer with what you have"}
                        ),
                    }
                )
            conversation.append(
                {
                    "role": "user",
                    "content": (
                        "Tool budget exhausted. Answer now using the information "
                        "already gathered. Do not call tools."
                    ),
                }
            )
            continue

        conversation.append(
            {
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": clean_calls,
            }
        )
        for call in clean_calls:
            name = call["function"]["name"]
            try:
                arguments = json.loads(call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            signature = (name, json.dumps(arguments, sort_keys=True))
            if calls_used >= 3:
                result = {"error": "tool limit reached; answer with what you have"}
            elif signature in seen:
                result = {
                    "error": "duplicate tool call; answer using the earlier result"
                }
            else:
                result = execute_tool(name, arguments)
                seen.add(signature)
                calls_used += 1
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise LLMError("model kept requesting tools")


def chat_reply(message, destination="", timeout=20):
    """Return the assistant's reply for one user message.

    Raises LLMNotConfigured when LLM_MODEL is missing, and LLMError when the
    provider errors, times out or returns something unexpected.
    """
    system = f"{SYSTEM_PROMPT} Today's date is {date.today().isoformat()}."
    if destination:
        system += f" The traveller is currently looking at {destination}."

    return _complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        timeout=timeout,
        tools=TOOL_SPECS,
    )


def generate_itinerary(prompt, start_date="", timeout=90):
    """Generate a structured, day-by-day itinerary for a free-text request.

    Returns the parsed JSON object (shape documented in ITINERARY_PROMPT).
    The caller owns validation against the database models. Raises
    LLMNotConfigured / LLMError exactly like chat_reply.
    """
    user = f"Today's date: {date.today().isoformat()}\nTraveller request: {prompt}"
    if start_date:
        user += f"\nStart date: {start_date}"
    user += "\nReturn the itinerary JSON now."

    raw = _complete(
        [
            {"role": "system", "content": ITINERARY_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        timeout=timeout,
        json_mode=True,
        tools=TOOL_SPECS,
    )

    # Providers occasionally wrap JSON in ``` fences despite instructions.
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("model did not return a JSON object")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError("model returned invalid itinerary JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("model returned an unexpected itinerary shape")
    return data
