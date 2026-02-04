"""OpenAI client wrapper."""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI, RateLimitError, APIError, AuthenticationError

from ..config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class OpenAIClient:
    """Wrapper for OpenAI API calls."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    def chat(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Make a chat completion request."""
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if functions:
            kwargs["tools"] = functions
            kwargs["tool_choice"] = "auto"

        if stream:
            kwargs["stream"] = True
            return self.client.chat.completions.create(**kwargs)

        response = self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict]] = None,
        stream: bool = False,
    ):
        """Make an async chat completion request."""
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if functions:
            kwargs["tools"] = functions
            kwargs["tool_choice"] = "auto"

        if stream:
            kwargs["stream"] = True
            return await self.async_client.chat.completions.create(**kwargs)

        response = await self.async_client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion responses."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        if functions:
            kwargs["tools"] = functions
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self.async_client.chat.completions.create(**kwargs)
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            yield {
                "type": "error",
                "error_type": "rate_limit",
                "message": "OpenAI rate limit exceeded. Please wait a moment and try again. If this persists, check your API usage at platform.openai.com/usage",
            }
            return
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            yield {
                "type": "error",
                "error_type": "auth_error",
                "message": "OpenAI API key is invalid or expired. Please check your OPENAI_API_KEY in the .env file.",
            }
            return
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            yield {
                "type": "error",
                "error_type": "api_error",
                "message": f"OpenAI API error: {str(e)}",
            }
            return
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            yield {
                "type": "error",
                "error_type": "unknown",
                "message": f"Unexpected error: {str(e)}",
            }
            return

        collected_content = ""
        collected_tool_calls = []

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    collected_content += delta.content
                    yield {
                        "type": "content",
                        "content": delta.content,
                    }

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if tool_call.index is not None:
                            # New or continuing tool call
                            while len(collected_tool_calls) <= tool_call.index:
                                collected_tool_calls.append({
                                    "id": "",
                                    "name": "",
                                    "arguments": "",
                                })

                            tc = collected_tool_calls[tool_call.index]

                            if tool_call.id:
                                tc["id"] = tool_call.id
                            if tool_call.function:
                                if tool_call.function.name:
                                    tc["name"] = tool_call.function.name
                                if tool_call.function.arguments:
                                    tc["arguments"] += tool_call.function.arguments

                # Check for finish
                if chunk.choices[0].finish_reason:
                    if chunk.choices[0].finish_reason == "tool_calls":
                        for tc in collected_tool_calls:
                            yield {
                                "type": "tool_call",
                                "tool_call": {
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "arguments": json.loads(tc["arguments"]) if tc["arguments"] else {},
                                },
                            }
                    yield {
                        "type": "finish",
                        "finish_reason": chunk.choices[0].finish_reason,
                        "full_content": collected_content,
                    }
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield {
                "type": "error",
                "error_type": "stream_error",
                "message": f"Error during response: {str(e)}",
            }

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse OpenAI response into a standard format."""
        message = response.choices[0].message

        result = {
            "content": message.content,
            "role": message.role,
            "finish_reason": response.choices[0].finish_reason,
        }

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in message.tool_calls
            ]

        return result

    def create_tool_response(
        self,
        tool_call_id: str,
        content: str,
    ) -> Dict[str, str]:
        """Create a tool response message."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }

    def generate_conversation_title(self, user_message: str, ai_response: str) -> str:
        """Generate a short title for a conversation based on the first exchange."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # Use faster/cheaper model for titles
            messages=[
                {
                    "role": "system",
                    "content": "Generate a very short title (2-5 words) for this conversation. Focus on the main topic or task. No quotes, no punctuation. Just the title.",
                },
                {
                    "role": "user",
                    "content": f"User said: {user_message[:200]}\n\nAssistant responded about: {ai_response[:200]}",
                },
            ],
            max_tokens=20,
        )
        return response.choices[0].message.content.strip()
