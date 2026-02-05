"""AI Orchestrator - manages AI conversations with function calling."""
import io
import json
import base64
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session

from ..ai.client import OpenAIClient
from ..ai.functions import AI_FUNCTIONS, execute_function
from .context_builder import ContextBuilder
from .memory_service import MemoryService
from .drive_service import get_drive_service


class AIOrchestrator:
    """Orchestrates AI conversations with function calling."""

    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAIClient()
        self.context_builder = ContextBuilder(db)
        self.memory_service = MemoryService(db)

    async def _build_user_content(
        self,
        text: str,
        files: List[Dict],
    ) -> Any:
        """Build user content with text and images for OpenAI Vision API."""
        if not files:
            return text

        # Build content array for vision
        content = []

        # Add text if present
        if text:
            content.append({"type": "text", "text": text})

        # Process each file
        drive_service = get_drive_service()

        for file_info in files:
            file_id = file_info.get("id")
            mime_type = file_info.get("mime_type", "")

            try:
                if mime_type.startswith("image/"):
                    # Download image and convert to base64 for GPT-4 Vision
                    file_content, _ = drive_service.download_file(file_id)
                    b64_content = base64.b64encode(file_content).decode("utf-8")

                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_content}",
                            "detail": "auto"
                        }
                    })

                elif mime_type == "application/pdf":
                    # Download PDF and extract text
                    file_content, _ = drive_service.download_file(file_id)
                    pdf_text = self._extract_pdf_text(file_content)
                    filename = file_info.get('name', 'document.pdf')

                    if pdf_text.strip():
                        content.append({
                            "type": "text",
                            "text": f"\n[Attached PDF: {filename}]\nContents:\n{pdf_text}"
                        })
                    else:
                        content.append({
                            "type": "text",
                            "text": f"\n[Attached PDF: {filename}]\n(Could not extract text - the PDF may be image-based or empty.)"
                        })

            except Exception as e:
                content.append({
                    "type": "text",
                    "text": f"\n[Error loading file {file_info.get('name', 'unknown')}: {str(e)}]"
                })

        return content if len(content) > 1 else (content[0] if content else text)

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text content from a PDF file."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            return f"(Error extracting PDF text: {str(e)})"

    async def process_message(
        self,
        user_message: str,
        conversation_id: int,
        attached_files: List[Dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and stream the response."""
        attached_files = attached_files or []

        # Build user content with any attached files
        user_content = await self._build_user_content(user_message, attached_files)

        # Save user message (store text and file references)
        metadata = {"files": attached_files} if attached_files else None
        self.memory_service.save_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            metadata=metadata,
        )

        # Build messages for AI
        messages = self.context_builder.build_messages_for_ai(
            conversation_id=conversation_id,
            user_message=user_content,  # Pass content with images
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
