"""Anthropic Claude client wrapper."""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import Anthropic, AsyncAnthropic, RateLimitError, APIError, AuthenticationError

from ..config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class AIClient:
    """Wrapper for Anthropic Claude API calls."""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.AI_MODEL

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Make a chat completion request (non-streaming)."""
        system_prompt, chat_messages = self._extract_system(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**kwargs)
        return self._parse_response(response)

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion responses."""
        system_prompt, chat_messages = self._extract_system(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = {"type": "auto"}

        try:
            async with self.async_client.messages.stream(**kwargs) as stream:
                collected_content = ""
                current_tool_id = None
                current_tool_name = None
                current_tool_input = ""

                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            current_tool_id = block.id
                            current_tool_name = block.name
                            current_tool_input = ""

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            collected_content += delta.text
                            yield {
                                "type": "content",
                                "content": delta.text,
                            }
                        elif delta.type == "input_json_delta":
                            current_tool_input += delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_id and current_tool_name:
                            try:
                                parsed_input = json.loads(current_tool_input) if current_tool_input else {}
                            except json.JSONDecodeError:
                                parsed_input = {}

                            yield {
                                "type": "tool_call",
                                "tool_call": {
                                    "id": current_tool_id,
                                    "name": current_tool_name,
                                    "arguments": parsed_input,
                                },
                            }

                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input = ""

                # Get the final message to check stop reason
                final_message = await stream.get_final_message()
                stop_reason = final_message.stop_reason

                yield {
                    "type": "finish",
                    "finish_reason": "tool_calls" if stop_reason == "tool_use" else "stop",
                    "full_content": collected_content,
                }

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            yield {
                "type": "error",
                "error_type": "rate_limit",
                "message": "Claude rate limit exceeded. Please wait a moment and try again.",
            }
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            yield {
                "type": "error",
                "error_type": "auth_error",
                "message": "Anthropic API key is invalid or expired. Please check your ANTHROPIC_API_KEY.",
            }
        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            yield {
                "type": "error",
                "error_type": "api_error",
                "message": f"Claude API error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            yield {
                "type": "error",
                "error_type": "unknown",
                "message": f"Unexpected error: {str(e)}",
            }

    def _extract_system(self, messages: List[Dict]) -> tuple:
        """Extract system message and return (system_prompt, chat_messages)."""
        system_prompt = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                chat_messages.append(msg)
        return system_prompt, chat_messages

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse Anthropic response into a standard format."""
        result = {
            "content": "",
            "role": "assistant",
            "finish_reason": response.stop_reason,
        }

        tool_calls = []
        for block in response.content:
            if block.type == "text":
                result["content"] = (result["content"] or "") + block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        if tool_calls:
            result["tool_calls"] = tool_calls

        return result

    def generate_conversation_title(self, user_message: str, ai_response: str) -> str:
        """Generate a short title for a conversation based on the first exchange."""
        response = self.client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=20,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a very short title (2-5 words) for this conversation. Focus on the main topic or task. No quotes, no punctuation. Just the title.\n\nUser said: {user_message[:200]}\n\nAssistant responded about: {ai_response[:200]}",
                },
            ],
        )
        return response.content[0].text.strip()
