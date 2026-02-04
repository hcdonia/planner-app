"""AI Orchestrator - manages AI conversations with function calling."""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session

from ..ai.client import OpenAIClient
from ..ai.functions import AI_FUNCTIONS, execute_function
from .context_builder import ContextBuilder
from .memory_service import MemoryService


class AIOrchestrator:
    """Orchestrates AI conversations with function calling."""

    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAIClient()
        self.context_builder = ContextBuilder(db)
        self.memory_service = MemoryService(db)

    async def process_message(
        self,
        user_message: str,
        conversation_id: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and stream the response."""
        # Save user message
        self.memory_service.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # Build messages for AI
        messages = self.context_builder.build_messages_for_ai(
            conversation_id=conversation_id,
            user_message=user_message,
        )

        # Track full response for saving
        full_response = ""
        function_results = []

        # Stream response
        async for chunk in self.client.stream_chat(messages, AI_FUNCTIONS):
            if chunk["type"] == "content":
                full_response += chunk["content"]
                yield {
                    "type": "chunk",
                    "content": chunk["content"],
                }

            elif chunk["type"] == "tool_call":
                tool_call = chunk["tool_call"]
                yield {
                    "type": "function_call",
                    "function": tool_call["name"],
                    "arguments": tool_call["arguments"],
                }

                # Execute the function
                result = execute_function(
                    db=self.db,
                    function_name=tool_call["name"],
                    arguments=tool_call["arguments"],
                )

                function_results.append({
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["name"],
                    "result": result,
                })

                yield {
                    "type": "function_result",
                    "function": tool_call["name"],
                    "result": result,
                }

            elif chunk["type"] == "finish":
                if chunk["finish_reason"] == "tool_calls" and function_results:
                    # Need to continue conversation with function results
                    async for response_chunk in self._continue_with_function_results(
                        messages, function_results
                    ):
                        if response_chunk["type"] == "content":
                            full_response += response_chunk["content"]
                        yield response_chunk

        # Save assistant response
        if full_response:
            metadata = None
            if function_results:
                metadata = {"function_calls": function_results}

            self.memory_service.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                metadata=metadata,
            )

            # Auto-generate conversation title if this is the first exchange
            conversation = self.memory_service.get_conversation(conversation_id)
            if conversation and not conversation.title:
                try:
                    title = self.client.generate_conversation_title(user_message, full_response)
                    self.memory_service.update_conversation(conversation_id, title=title)
                    yield {"type": "title_update", "title": title}
                except Exception:
                    pass  # Silently fail title generation

        yield {"type": "complete", "full_response": full_response}

    async def _continue_with_function_results(
        self,
        messages: List[Dict],
        function_results: List[Dict],
        depth: int = 0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Continue conversation after function calls."""
        # Prevent infinite loops - max 5 function call rounds
        if depth >= 5:
            yield {
                "type": "content",
                "content": "\n\nI've made several attempts but couldn't complete the task. Please try rephrasing your request.",
            }
            yield {"type": "finish", "finish_reason": "stop", "full_content": ""}
            return

        # Add assistant message with tool calls
        tool_calls_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": fr["tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": fr["name"],
                        "arguments": json.dumps(fr["result"]),
                    },
                }
                for fr in function_results
            ],
        }
        messages.append(tool_calls_message)

        # Add tool responses
        for fr in function_results:
            messages.append({
                "role": "tool",
                "tool_call_id": fr["tool_call_id"],
                "content": json.dumps(fr["result"]),
            })

        # Get AI response and handle any additional tool calls
        new_function_results = []
        async for chunk in self.client.stream_chat(messages, AI_FUNCTIONS):
            if chunk["type"] == "tool_call":
                from ..ai.functions import execute_function
                tool_call = chunk["tool_call"]
                result = execute_function(
                    db=self.db,
                    function_name=tool_call["name"],
                    arguments=tool_call["arguments"],
                )
                new_function_results.append({
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["name"],
                    "result": result,
                })
                yield chunk
                yield {
                    "type": "function_result",
                    "function": tool_call["name"],
                    "result": result,
                }
            elif chunk["type"] == "finish" and chunk["finish_reason"] == "tool_calls" and new_function_results:
                # Recursively continue with new function results
                async for response_chunk in self._continue_with_function_results(
                    messages, new_function_results, depth + 1
                ):
                    yield response_chunk
            else:
                yield chunk

    def process_message_sync(
        self,
        user_message: str,
        conversation_id: int,
    ) -> Dict[str, Any]:
        """Process a message synchronously (non-streaming)."""
        # Save user message
        self.memory_service.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # Build messages for AI
        messages = self.context_builder.build_messages_for_ai(
            conversation_id=conversation_id,
            user_message=user_message,
        )

        # Get response
        response = self.client.chat(messages, AI_FUNCTIONS)

        function_results = []

        # Handle function calls
        while response.get("tool_calls"):
            tool_calls = response["tool_calls"]

            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute functions and add results
            for tc in tool_calls:
                result = execute_function(
                    db=self.db,
                    function_name=tc["name"],
                    arguments=tc["arguments"],
                )
                function_results.append({
                    "tool_call_id": tc["id"],
                    "name": tc["name"],
                    "result": result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result),
                })

            # Get next response
            response = self.client.chat(messages, AI_FUNCTIONS)

        # Save assistant response
        content = response.get("content", "")
        metadata = {"function_calls": function_results} if function_results else None

        self.memory_service.save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            metadata=metadata,
        )

        return {
            "content": content,
            "function_results": function_results,
        }
