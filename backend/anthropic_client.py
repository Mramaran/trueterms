"""
Anthropic Client Wrapper — TrueTerms (Corrected)
=====================================================
Drop-in replacement for OpenAI client interface.

Key fix: When the system prompt already asks for JSON inside a markdown
code block (contract generation), we do NOT inject "Respond with ONLY a
valid JSON object, no markdown" — that contradicts the system prompt and
breaks JSON extraction.

The injection is now ONLY applied to agents that genuinely need bare JSON
responses (router, grader, hallucination, rewriter agents).
"""

import os
import time
import anthropic
from dotenv import load_dotenv

load_dotenv()


class AnthropicMessage:
    def __init__(self, content: str):
        self.content = content


class AnthropicChoice:
    def __init__(self, content: str):
        self.message = AnthropicMessage(content)


class AnthropicResponse:
    def __init__(self, content: str):
        self.choices = [AnthropicChoice(content)]


class AnthropicChatCompletions:
    """Mimics openai.chat.completions interface."""

    def __init__(self, client: anthropic.Anthropic):
        self._client = client

    def create(
        self,
        model: str,
        messages: list,
        temperature: float = 0,
        response_format: dict = None,
        **kwargs
    ) -> AnthropicResponse:

        # Split system prompt from conversation messages
        system_prompt = ""
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        if not user_messages:
            user_messages = [{"role": "user", "content": system_prompt}]
            system_prompt = ""

        # Inject "bare JSON" instruction ONLY when:
        #   1. response_format=json_object is requested AND
        #   2. The system prompt does NOT already ask for markdown code blocks
        #      (i.e., not the contract generator prompt)
        if response_format and response_format.get("type") == "json_object":
            system_already_has_json_block = (
                "```json" in system_prompt or
                "code block" in system_prompt.lower() or
                "postman" in system_prompt.lower()
            )

            if not system_already_has_json_block and user_messages:
                last = user_messages[-1]
                if "json" not in last["content"].lower():
                    user_messages[-1] = {
                        "role": last["role"],
                        "content": (
                            last["content"] +
                            "\n\nRespond with ONLY a valid JSON object. "
                            "No markdown, no explanation, no code fences."
                        )
                    }

        # Call Anthropic API — with auto-retry on 529 overloaded
        # Max tokens: 8192 to handle large responses (Korean/multilingual
        # text uses 2-3x more tokens than English; long contract explanations
        # with tables/timelines can exceed 4096 and crash mid-JSON).
        api_kwargs = {
            "model": model,
            "max_tokens": 8192,
            "messages": user_messages,
            "temperature": temperature,
        }
        if system_prompt:
            api_kwargs["system"] = system_prompt

        # Fallback model chain — uses latest active models per Anthropic docs Feb 2026
        FALLBACK_MODELS = [
            api_kwargs["model"],        # primary:   whatever is set in config/env
            "claude-haiku-4-5-20251001", # fallback1: latest haiku (fast + cheap)
            "claude-sonnet-4-6",         # fallback2: latest sonnet (very reliable)
            "claude-opus-4-6",           # fallback3: latest opus (most powerful)
        ]

        max_retries = 3
        retry_delay = 5  # seconds between retries per model
        last_error  = None

        for model_attempt, fallback_model in enumerate(FALLBACK_MODELS):
            api_kwargs["model"] = fallback_model
            if model_attempt > 0:
                print(f"  [API] Switching to fallback model: {fallback_model}")

            for attempt in range(max_retries):
                try:
                    response = self._client.messages.create(**api_kwargs)
                    last_error = None
                    break  # success — exit retry loop
                except anthropic.APIStatusError as e:
                    last_error = e
                    if e.status_code == 529:  # overloaded
                        wait = retry_delay * (attempt + 1)
                        print(f"  [API] Overloaded (529) — retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(wait)
                    else:
                        raise  # non-529 errors raise immediately

            if last_error is None:
                break  # success — no need to try next fallback model

        if last_error is not None:
            raise last_error  # all models and retries exhausted

        content = response.content[0].text

        # Clean bare JSON responses (strip accidental code fences + extra data)
        if response_format and response_format.get("type") == "json_object":
            stripped = content.strip()
            system_already_has_json_block = (
                "```json" in system_prompt or
                "postman" in system_prompt.lower()
            )
            if not system_already_has_json_block:
                # Strip code fences if present
                if stripped.startswith("```"):
                    lines = stripped.split("\n")
                    stripped = "\n".join(
                        line for line in lines if not line.startswith("```")
                    ).strip()
                # Extract ONLY the first complete JSON object
                # This fixes: 'Extra data: line 3 column 1' error
                # caused by Claude returning extra text after the JSON
                if stripped.startswith("{"):
                    depth = 0
                    end_idx = 0
                    for i, ch in enumerate(stripped):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                end_idx = i + 1
                                break
                    if end_idx:
                        stripped = stripped[:end_idx]
                content = stripped

        return AnthropicResponse(content)


class AnthropicChat:
    def __init__(self, client: anthropic.Anthropic):
        self.completions = AnthropicChatCompletions(client)


class AnthropicClientWrapper:
    """Drop-in replacement for OpenAI client."""

    def __init__(self, api_key: str = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found!\n"
                "Set it in .env: ANTHROPIC_API_KEY=your-key-here"
            )
        self._client = anthropic.Anthropic(api_key=key)
        self.chat = AnthropicChat(self._client)


def get_llm_client() -> AnthropicClientWrapper:
    return AnthropicClientWrapper()
