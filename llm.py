"""LLM providers: OpenAI (GPT-4o mini) or Anthropic Claude, chosen at runtime."""
from __future__ import annotations

import os
import sys

# Generous limit: the system prompt already caps length at ~220 words, and
# "thinking" models (e.g. Gemini 2.5 Flash) spend part of this budget on
# hidden reasoning before writing the answer.
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))


def _warn_if_truncated(reason: str | None) -> None:
    if reason in ("length", "max_tokens"):
        print(f"[warning] response was cut off ({reason}); raise LLM_MAX_TOKENS", file=sys.stderr)


def generate(system_prompt: str, user_prompt: str, provider: str = "openai") -> str:
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()  # reads OPENAI_API_KEY
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.8,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = response.choices[0]
        _warn_if_truncated(choice.finish_reason)
        return (choice.message.content or "").strip()

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=MAX_TOKENS,
            temperature=0.8,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        _warn_if_truncated(response.stop_reason)
        return response.content[0].text.strip()

    raise ValueError(f"Unknown provider: {provider!r} (use 'openai' or 'anthropic')")
