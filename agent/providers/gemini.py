"""
Google Gemini Model Provider
Integrates with the official google-genai SDK.
"""
import time
from typing import Any, Dict, List, Optional

from .base import BaseProvider, ProviderResponse, ToolCall


class GeminiProvider(BaseProvider):
    """Google Gemini provider implementing BaseProvider."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", temperature: float = 0.2):
        super().__init__(model_name=model_name, temperature=temperature)
        self.api_key = api_key
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise ImportError(
                "The 'google-genai' package is required. "
                "Install it using: pip install google-genai"
            )

    def _convert_tool_schemas(self, tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert standard JSON schemas into Gemini FunctionDeclarations."""
        from google.genai import types

        declarations = []
        for t in tools:
            # t has: name, description, parameters (dict with type, properties, required)
            dec = types.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("parameters"),
            )
            declarations.append(dec)

        if not declarations:
            return []
        return [types.Tool(function_declarations=declarations)]

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Any]:
        """Convert universal message history into Gemini Content objects."""
        from google.genai import types

        contents: List[types.Content] = []
        i = 0
        n = len(messages)

        while i < n:
            msg = messages[i]
            role = msg.get("role", "user")

            if role == "assistant":
                # Check if we preserved the original model response Content (with thought_signature intact)
                raw_resp = msg.get("raw_response")
                if raw_resp is not None:
                    if hasattr(raw_resp, "candidates") and raw_resp.candidates:
                        candidate = raw_resp.candidates[0]
                        if candidate.content:
                            contents.append(candidate.content)
                            i += 1
                            continue
                    elif isinstance(raw_resp, types.Content):
                        contents.append(raw_resp)
                        i += 1
                        continue

                # Fallback if raw_response is not available
                parts = []
                if "content" in msg and msg["content"]:
                    parts.append(types.Part.from_text(text=str(msg["content"])))

                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        parts.append(
                            types.Part.from_function_call(
                                name=tc["name"],
                                args=tc.get("args", {})
                            )
                        )

                if parts:
                    contents.append(types.Content(role="model", parts=parts))
                i += 1

            elif role == "tool":
                # In Gemini, tool responses are sent as 'user' turns with function_response parts.
                # Group consecutive tool outputs for the current turn together.
                tool_parts = []
                while i < n and messages[i].get("role") == "tool":
                    t_msg = messages[i]
                    tool_parts.append(
                        types.Part.from_function_response(
                            name=t_msg.get("tool_name", "tool"),
                            response={"result": t_msg.get("content", "")}
                        )
                    )
                    i += 1
                if tool_parts:
                    contents.append(types.Content(role="user", parts=tool_parts))

            else:
                # Standard user message
                text_content = str(msg.get("content", ""))
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=text_content)]))
                i += 1

        return contents

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
    ) -> ProviderResponse:
        """Call Gemini generate_content with retries on rate limits."""
        from google.genai import types

        gemini_tools = self._convert_tool_schemas(tools)
        contents = self._convert_messages(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
            tools=gemini_tools if gemini_tools else None,
        )

        max_retries = 4
        delay = 2.0

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                extracted_text: Optional[str] = None
                text_segments: List[str] = []
                tool_calls: List[ToolCall] = []

                # Safely read text from candidates.content.parts instead of response.text
                # to avoid warnings/errors about non-text parts (e.g. thoughts or function calls)
                if response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if getattr(part, "text", None):
                                text_segments.append(part.text)
                            if getattr(part, "function_call", None):
                                fc = part.function_call
                                args = dict(fc.args) if fc.args else {}
                                tool_calls.append(ToolCall(name=fc.name, args=args, call_id=fc.name))

                if not tool_calls and response.function_calls:
                    for fc in response.function_calls:
                        args = dict(fc.args) if fc.args else {}
                        tool_calls.append(ToolCall(name=fc.name, args=args, call_id=fc.name))

                if text_segments:
                    extracted_text = "".join(text_segments)

                return ProviderResponse(
                    text=extracted_text,
                    tool_calls=tool_calls,
                    raw_response=response,
                )

            except Exception as e:
                err_str = str(e)
                # Check for transient server errors, high demand / capacity spikes, or rate limits
                is_transient = any(
                    token in err_str
                    for token in [
                        "503",
                        "UNAVAILABLE",
                        "high demand",
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "500",
                        "INTERNAL",
                        "overloaded",
                        "10053",
                        "10054",
                        "connection was aborted",
                        "ConnectionResetError",
                        "RemoteDisconnected",
                    ]
                )
                if is_transient and attempt < max_retries - 1:
                    print(
                        f"\n   [Notice] Model temporarily busy or experiencing high demand. "
                        f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise RuntimeError(f"Gemini API error: {err_str}") from e

        raise RuntimeError("Failed to generate response from Gemini after maximum retries.")
