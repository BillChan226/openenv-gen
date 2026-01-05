"""
LLM Client Module - Provides unified interface for LLM calls

Supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- Local models (Ollama, vLLM)
- Custom endpoints
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Optional, Union
import asyncio
import json
import logging
import os
import re

from .config import LLMConfig, LLMProvider


def _redact_secrets(text: str) -> str:
    """
    Best-effort redaction of secrets and very large inline blobs.

    Purpose:
    - Avoid sending accidental credentials/tokens to LLM providers
    - Reduce chance of OpenAI 'invalid_prompt' due to policy triggers on sensitive content
    """
    if not text:
        return text

    # Common API keys / tokens
    patterns = [
        # OpenAI-style
        (r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED_OPENAI_KEY]"),
        # Google API key
        (r"\bAIza[0-9A-Za-z\-_]{30,}\b", "[REDACTED_GOOGLE_KEY]"),
        # JWT tokens
        (r"\beyJ[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-]+=*\.[A-Za-z0-9_\-]+=*\b", "[REDACTED_JWT]"),
        # data:image base64 blobs (very large)
        (r"data:image\/[^;]+;base64,[A-Za-z0-9+/=]{200,}", "data:image/...;base64,[TRUNCATED]"),
    ]
    redacted = text
    for pat, repl in patterns:
        redacted = re.sub(pat, repl, redacted)

    # Redact obvious password assignments in text
    redacted = re.sub(r"(?im)^(.*\bpassword\b\s*[:=]\s*)(.+)$", r"\1[REDACTED]", redacted)
    redacted = re.sub(r"(?im)^(.*\bpasswd\b\s*[:=]\s*)(.+)$", r"\1[REDACTED]", redacted)

    return redacted


def _sanitize_message_content(content: Optional[Union[str, list]]) -> Optional[Union[str, list]]:
    if content is None:
        return None
    if isinstance(content, str):
        return _redact_secrets(content)
    if isinstance(content, list):
        # Check if this is valid multimodal content (each item should have 'type')
        all_valid_multimodal = all(
            isinstance(part, dict) and 'type' in part 
            for part in content
        )
        
        if all_valid_multimodal:
            # Valid multimodal - sanitize and keep as list
            sanitized_parts = []
            for part in content:
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    new_part = dict(part)
                    new_part["text"] = _redact_secrets(new_part["text"])
                    sanitized_parts.append(new_part)
                else:
                    sanitized_parts.append(part)
            return sanitized_parts
        else:
            # Invalid multimodal format - convert to string
            # This handles cases where content accidentally became a list
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict):
                    if 'text' in part:
                        text_parts.append(str(part['text']))
                    elif 'content' in part:
                        text_parts.append(str(part['content']))
                    else:
                        text_parts.append(str(part))
                else:
                    text_parts.append(str(part))
            return _redact_secrets(" ".join(text_parts))
    
    # Non-string, non-list content - convert to string
    return _redact_secrets(str(content))


@dataclass
class Message:
    """Chat message - supports both text and multimodal content"""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[Union[str, list]] = None  # str for text, list for multimodal
    name: Optional[str] = None  # For function messages
    function_call: Optional[dict] = None  # For assistant function calls
    tool_calls: Optional[list] = None  # For tool calls
    tool_call_id: Optional[str] = None  # For tool response
    
    def to_dict(self) -> dict:
        d = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.name:
            d["name"] = self.name
        if self.function_call:
            d["function_call"] = self.function_call
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                if hasattr(tc, 'id') else tc
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)
    
    @classmethod
    def user_with_image(cls, text: str, image_base64: str, mime_type: str = "image/png") -> "Message":
        """Create user message with text and image (multimodal)"""
        return cls(
            role="user",
            content=[
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}", "detail": "high"}}
            ]
        )
    
    @classmethod
    def user_multimodal(cls, content_parts: list) -> "Message":
        """Create user message with multiple content parts (text, images, etc.)
        
        Args:
            content_parts: List of dicts like:
                [{"type": "text", "text": "..."}, 
                 {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]
        """
        return cls(role="user", content=content_parts)
    
    @classmethod
    def assistant(cls, content: str = None, tool_calls: list = None) -> "Message":
        return cls(role="assistant", content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool(cls, content: str, tool_call_id: str) -> "Message":
        """Create tool response message"""
        return cls(role="tool", content=content, tool_call_id=tool_call_id)


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    model: str
    finish_reason: str = "stop"  # stop, length, function_call, tool_calls
    usage: dict = field(default_factory=dict)  # prompt_tokens, completion_tokens, total_tokens
    function_call: Optional[dict] = None
    tool_calls: Optional[list] = None
    raw_response: Optional[Any] = None
    latency: float = 0.0  # seconds
    
    @property
    def prompt_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0)
    
    @property
    def completion_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", 0)


class BaseLLMClient(ABC):
    """
    Base LLM Client
    
    All LLM providers must implement this interface
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._logger = logging.getLogger(f"LLM.{config.provider.value}")
    
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        functions: Optional[list[dict]] = None,
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send chat completion request
        
        Args:
            messages: List of chat messages
            temperature: Sampling temperature (overrides config)
            max_tokens: Maximum tokens to generate (overrides config)
            stop: Stop sequences
            functions: Function definitions for function calling
            tools: Tool definitions for tool use
            
        Returns:
            LLM response
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Send streaming chat completion request
        
        Yields:
            Response content chunks
        """
        pass
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Simple completion interface
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLM response
        """
        messages = []
        if system_prompt:
            messages.append(Message.system(system_prompt))
        messages.append(Message.user(prompt))
        return await self.chat(messages, **kwargs)
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Common rate limit indicators
        rate_limit_keywords = [
            "rate_limit", "rate limit", "ratelimit",
            "429", "too many requests",
            "resource_exhausted", "resourceexhausted",
            "quota", "exceeded",
            "throttl",
        ]
        
        for keyword in rate_limit_keywords:
            if keyword in error_str or keyword in error_type:
                return True
        
        # Check for HTTP 429 status code
        if hasattr(error, 'status_code') and error.status_code == 429:
            return True
        if hasattr(error, 'code') and error.code == 429:
            return True
            
        return False
    
    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """Try to extract retry-after time from error"""
        error_str = str(error)
        
        # Try to find retry-after in error message (e.g., "retry after 60 seconds")
        import re
        patterns = [
            r'retry.?after[:\s]+(\d+)',
            r'wait[:\s]+(\d+)',
            r'(\d+)\s*seconds?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str.lower())
            if match:
                return float(match.group(1))
        
        return None
    
    async def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = None,
        **kwargs
    ) -> Any:
        """Retry with exponential backoff and smart rate limit handling"""
        max_retries = max_retries or self.config.retry_attempts
        last_error = None
        
        # For rate limits, we may want more retries with longer delays
        rate_limit_extra_retries = 3
        rate_limit_base_delay = 30  # Start with 30 seconds for rate limits
        
        attempt = 0
        total_attempts = max_retries
        
        while attempt < total_attempts:
            try:
                attempt_start = datetime.now()
                self._logger.debug(f"[LLM] Attempt {attempt + 1}/{total_attempts} starting...")
                result = await func(*args, **kwargs)
                elapsed = (datetime.now() - attempt_start).total_seconds()
                self._logger.info(f"[LLM] Attempt {attempt + 1} succeeded in {elapsed:.1f}s")
                return result
            except Exception as e:
                elapsed = (datetime.now() - attempt_start).total_seconds()
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)[:200]  # Truncate long errors
                
                is_rate_limit = self._is_rate_limit_error(e)
                
                if attempt < total_attempts - 1:
                    if is_rate_limit:
                        # For rate limits, use longer delays and add extra retries
                        retry_after = self._extract_retry_after(e)
                        if retry_after:
                            delay = retry_after + 5  # Add 5 seconds buffer
                        else:
                            # Exponential backoff starting from rate_limit_base_delay
                            delay = rate_limit_base_delay * (2 ** min(attempt, 3))  # Cap at 240s
                        
                        # Add extra retries for rate limits if we haven't already
                        if attempt == max_retries - 1 and rate_limit_extra_retries > 0:
                            total_attempts = max_retries + rate_limit_extra_retries
                            self._logger.info(f"[LLM] Rate limit detected, extending retries to {total_attempts}")
                        
                        self._logger.warning(
                            f"[LLM] Rate limit hit on attempt {attempt + 1}. "
                            f"Sleeping {delay:.0f}s before retry... [{error_type}] {error_msg}"
                        )
                    else:
                        # Normal exponential backoff for other errors
                        delay = self.config.retry_delay * (2 ** attempt)
                        self._logger.warning(
                            f"[LLM] Attempt {attempt + 1} failed after {elapsed:.1f}s: "
                            f"[{error_type}] {error_msg}. Retrying in {delay}s..."
                        )
                    
                    await asyncio.sleep(delay)
                else:
                    self._logger.error(f"[LLM] All {total_attempts} attempts failed. Last error: [{error_type}] {error_msg}")
                
                attempt += 1
        
        raise last_error


class OpenAIClient(BaseLLMClient):
    """OpenAI API Client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
            
            self._client = AsyncOpenAI(
                api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=self.config.api_base,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        functions: Optional[list[dict]] = None,
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()

        # Always sanitize outgoing content (redact keys/tokens/password-like lines).
        safe_messages: list[Message] = [
            Message(role=m.role, content=_sanitize_message_content(m.content), name=m.name, function_call=m.function_call, tool_calls=m.tool_calls, tool_call_id=m.tool_call_id)
            for m in messages
        ]
        
        # Determine token parameter name based on model
        model_name = self.config.model_name
        use_completion_tokens = model_name.startswith(("gpt-5", "o1", "o3"))
        token_param = "max_completion_tokens" if use_completion_tokens else "max_tokens"
        
        request_params = {
            "model": model_name,
            "messages": [m.to_dict() for m in safe_messages],
            "temperature": temperature or self.config.temperature,
            token_param: max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
        }
        
        if stop:
            request_params["stop"] = stop
        if functions:
            request_params["functions"] = functions
        if tools:
            request_params["tools"] = tools
        
        request_params.update(kwargs)
        
        start_time = datetime.now()
        
        # Log request info for debugging
        msg_count = len(safe_messages)
        total_content_len = sum(len(str(m.content or "")) for m in safe_messages)
        tool_count = len(tools) if tools else 0
        self._logger.info(f"[LLM Request] model={model_name}, messages={msg_count}, content_chars={total_content_len}, tools={tool_count}")
        
        async def _call_with_progress():
            """Wrapper that logs progress during long waits"""
            warn_interval = 60  # Log warning every 60 seconds
            call_start = datetime.now()
            
            async def _do_call():
                return await client.chat.completions.create(**request_params)
            
            # Create task so we can check on it
            task = asyncio.create_task(_do_call())
            
            while not task.done():
                try:
                    # Wait for up to warn_interval seconds
                    return await asyncio.wait_for(asyncio.shield(task), timeout=warn_interval)
                except asyncio.TimeoutError:
                    elapsed = (datetime.now() - call_start).total_seconds()
                    self._logger.warning(f"[LLM] Still waiting for API response... elapsed={elapsed:.0f}s")
                    # Continue waiting
                    continue
            
            return await task
        
        async def _call():
            return await _call_with_progress()
        
        def _is_invalid_prompt_error(e: Exception) -> bool:
            msg = str(e).lower()
            return ("invalid_prompt" in msg) or ("flagged as potentially violating" in msg) or ("usage policy" in msg)

        def _compact_for_retry(msgs: list[Message]) -> list[Message]:
            # Keep at most one system message and the last user message.
            sys_msg = next((m for m in msgs if m.role == "system"), None)
            last_user = next((m for m in reversed(msgs) if m.role == "user"), None)
            keep = [m for m in [sys_msg, last_user] if m is not None]
            # Aggressively truncate to avoid long tool/error dumps being re-sent.
            compacted: list[Message] = []
            for m in keep:
                c = m.content
                if isinstance(c, str) and len(c) > 15000:
                    c = c[:14900] + "\n...(truncated)\n"
                compacted.append(Message(role=m.role, content=c, name=m.name))
            return compacted

        try:
            response = await self._retry_with_backoff(_call)
        except Exception as e:
            # OpenAI can reject a prompt as 'invalid_prompt' (policy filter). Try one safe fallback instead of crashing.
            if _is_invalid_prompt_error(e):
                self._logger.warning("OpenAI rejected prompt (invalid_prompt). Retrying once with sanitized+compacted context...")
                request_params["messages"] = [m.to_dict() for m in _compact_for_retry(safe_messages)]
                async def _call2():
                    return await client.chat.completions.create(**request_params)
                try:
                    response = await self._retry_with_backoff(_call2, max_retries=2)
                except Exception as e2:
                    if _is_invalid_prompt_error(e2):
                        raise RuntimeError(
                            "OpenAI rejected the prompt as invalid_prompt (policy filter) even after sanitization/compaction. "
                            "This usually indicates the prompt contains sensitive data or other policy-triggering content."
                        ) from e2
                    raise
            else:
                raise
        latency = (datetime.now() - start_time).total_seconds()
        
        choice = response.choices[0]
        message = choice.message
        
        # Log response summary
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        has_tool_calls = bool(message.tool_calls)
        self._logger.info(f"[LLM Response] latency={latency:.1f}s, prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, tool_calls={has_tool_calls}, finish={choice.finish_reason}")
        
        return LLMResponse(
            content=message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            function_call=message.function_call.model_dump() if message.function_call else None,
            tool_calls=[tc.model_dump() for tc in message.tool_calls] if message.tool_calls else None,
            raw_response=response,
            latency=latency,
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        client = self._get_client()
        
        request_params = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        
        if stop:
            request_params["stop"] = stop
        
        request_params.update(kwargs)
        
        response = await client.chat.completions.create(**request_params)
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(BaseLLMClient):
    """Anthropic API Client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError("Please install anthropic: pip install anthropic")
            
            self._client = AsyncAnthropic(
                api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY"),
                timeout=self.config.timeout,
            )
        return self._client
    
    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        
        # Extract system message
        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        request_params = {
            "model": self.config.model_name,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }
        
        if system_content:
            request_params["system"] = system_content
        if stop:
            request_params["stop_sequences"] = stop
        if tools:
            request_params["tools"] = tools
        
        request_params.update(kwargs)
        
        start_time = datetime.now()
        
        async def _call():
            return await client.messages.create(**request_params)
        
        response = await self._retry_with_backoff(_call)
        latency = (datetime.now() - start_time).total_seconds()
        
        # Extract content
        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })
        
        return LLMResponse(
            content=content,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            tool_calls=tool_calls if tool_calls else None,
            raw_response=response,
            latency=latency,
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        client = self._get_client()
        
        # Extract system message
        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})
        
        request_params = {
            "model": self.config.model_name,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "stream": True,
        }
        
        if system_content:
            request_params["system"] = system_content
        if stop:
            request_params["stop_sequences"] = stop
        
        request_params.update(kwargs)
        
        async with client.messages.stream(**request_params) as stream:
            async for text in stream.text_stream:
                yield text


class LocalLLMClient(BaseLLMClient):
    """
    Local LLM Client (Ollama, vLLM, etc.)
    
    Uses OpenAI-compatible API format
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization using httpx"""
        if self._client is None:
            try:
                import httpx
            except ImportError:
                raise ImportError("Please install httpx: pip install httpx")
            
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base or "http://localhost:11434",
                timeout=self.config.timeout,
            )
        return self._client
    
    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> LLMResponse:
        client = self._get_client()
        
        # Ollama format
        request_data = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        if stop:
            request_data["options"]["stop"] = stop
        
        start_time = datetime.now()
        
        response = await client.post("/api/chat", json=request_data)
        response.raise_for_status()
        data = response.json()
        
        latency = (datetime.now() - start_time).total_seconds()
        
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", self.config.model_name),
            finish_reason="stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            raw_response=data,
            latency=latency,
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        client = self._get_client()
        
        request_data = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        if stop:
            request_data["options"]["stop"] = stop
        
        async with client.stream("POST", "/api/chat", json=request_data) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]


class GoogleClient(BaseLLMClient):
    """
    Google Gemini Client
    
    Uses the native google-generativeai SDK for full Gemini 3 support
    including automatic thought_signature handling for function calls.
    Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
    
    Install: pip install google-generativeai
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
        self._model = None
    
    def _get_client(self):
        """Lazy initialization of Google GenAI client"""
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
            
            api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
            
            self._client = genai.Client(api_key=api_key)
            self._types = types
        return self._client
    
    def _convert_openai_tools_to_google(self, tools: list[dict]) -> list:
        """Convert OpenAI-style tool definitions to Google format"""
        from google.genai import types
        
        def convert_schema(schema: dict) -> types.Schema:
            """Recursively convert JSON schema to Google Schema"""
            if not schema:
                return types.Schema(type="STRING")
            
            # Handle type - can be string or list (e.g., ["string", "null"] for nullable)
            raw_type = schema.get("type", "string")
            if isinstance(raw_type, list):
                # Take the first non-null type
                schema_type = next((t for t in raw_type if t != "null"), "string").upper()
            else:
                schema_type = raw_type.upper()
            type_map = {
                "STRING": "STRING",
                "NUMBER": "NUMBER", 
                "INTEGER": "INTEGER",
                "BOOLEAN": "BOOLEAN",
                "ARRAY": "ARRAY",
                "OBJECT": "OBJECT",
            }
            google_type = type_map.get(schema_type, "STRING")
            
            kwargs = {
                "type": google_type,
                "description": schema.get("description", ""),
            }
            
            # Handle enum
            if "enum" in schema:
                kwargs["enum"] = schema["enum"]
            
            # Handle array items - Google requires this for ARRAY type
            if google_type == "ARRAY":
                items = schema.get("items", {"type": "string"})
                kwargs["items"] = convert_schema(items)
            
            # Handle object properties
            if google_type == "OBJECT" and "properties" in schema:
                props = schema.get("properties", {})
                kwargs["properties"] = {
                    k: convert_schema(v) for k, v in props.items()
                }
                if "required" in schema:
                    kwargs["required"] = schema["required"]
            
            return types.Schema(**kwargs)
        
        google_tools = []
        function_declarations = []
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                params = func.get("parameters", {})
                
                # Convert parameters schema
                param_schema = None
                if params and params.get("properties"):
                    param_schema = convert_schema(params)
                
                function_declarations.append(
                    types.FunctionDeclaration(
                        name=func.get("name", ""),
                        description=func.get("description", ""),
                        parameters=param_schema,
                    )
                )
        
        # Google prefers all functions in a single Tool
        if function_declarations:
            google_tools.append(types.Tool(function_declarations=function_declarations))
        
        return google_tools
    
    def _convert_messages_to_google(self, messages: list[Message]) -> tuple:
        """Convert OpenAI-style messages to Google format
        
        Returns: (system_instruction, contents)
        """
        from google.genai import types
        
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content if isinstance(msg.content, str) else str(msg.content)
            elif msg.role == "user":
                if isinstance(msg.content, list):
                    # Multimodal content
                    parts = []
                    for part in msg.content:
                        if part.get("type") == "text":
                            parts.append(types.Part.from_text(text=part.get("text", "")))
                        elif part.get("type") == "image_url":
                            # Handle base64 images
                            url = part.get("image_url", {}).get("url", "")
                            if url.startswith("data:"):
                                # Extract base64 data
                                import base64
                                # Format: data:image/png;base64,<data>
                                header, data = url.split(",", 1)
                                mime_type = header.split(":")[1].split(";")[0]
                                parts.append(types.Part.from_bytes(
                                    data=base64.b64decode(data),
                                    mime_type=mime_type
                                ))
                    contents.append(types.Content(role="user", parts=parts))
                else:
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg.content or "")]
                    ))
            elif msg.role == "assistant":
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        if hasattr(tc, 'function'):
                            func = tc.function
                            args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                            thought_sig = getattr(tc, 'thought_signature', None)
                            if thought_sig:
                                # Create Part with thought_signature for Gemini 3
                                parts.append(types.Part(
                                    function_call=types.FunctionCall(name=func.name, args=args),
                                    thought_signature=thought_sig
                                ))
                            else:
                                parts.append(types.Part.from_function_call(
                                    name=func.name,
                                    args=args
                                ))
                        elif isinstance(tc, dict):
                            func = tc.get("function", {})
                            args = func.get("arguments", {})
                            if isinstance(args, str):
                                args = json.loads(args)
                            thought_sig = tc.get("thought_signature")
                            if thought_sig:
                                # Create Part with thought_signature for Gemini 3
                                parts.append(types.Part(
                                    function_call=types.FunctionCall(name=func.get("name", ""), args=args),
                                    thought_signature=thought_sig
                                ))
                            else:
                                parts.append(types.Part.from_function_call(
                                    name=func.get("name", ""),
                                    args=args
                                ))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif msg.role == "tool":
                # Tool response
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=msg.name or "tool",
                        response={"result": msg.content}
                    )]
                ))
        
        return system_instruction, contents
    
    async def chat(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        functions: Optional[list[dict]] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat request to Gemini using native SDK"""
        client = self._get_client()
        from google.genai import types
        
        # Always sanitize outgoing content
        safe_messages: list[Message] = [
            Message(role=m.role, content=_sanitize_message_content(m.content), name=m.name, function_call=m.function_call, tool_calls=m.tool_calls, tool_call_id=m.tool_call_id)
            for m in messages
        ]
        
        # Convert messages to Google format
        system_instruction, contents = self._convert_messages_to_google(safe_messages)
        
        # Convert tools if provided
        google_tools = None
        if tools:
            google_tools = self._convert_openai_tools_to_google(tools)
        elif functions:
            google_tools = self._convert_openai_tools_to_google([{"type": "function", "function": f} for f in functions])
        
        # Build generation config
        gen_config = types.GenerateContentConfig(
            temperature=temperature if temperature is not None else self.config.temperature,
            max_output_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
            system_instruction=system_instruction,
            tools=google_tools,
        )
        
        if stop:
            gen_config.stop_sequences = stop
        
        start_time = datetime.now()
        
        # Log request info
        msg_count = len(safe_messages)
        total_content_len = sum(len(str(m.content or "")) for m in safe_messages)
        tool_count = len(tools) if tools else 0
        self._logger.info(f"[LLM Request] model={self.config.model_name}, messages={msg_count}, content_chars={total_content_len}, tools={tool_count}")
        
        async def _call_with_progress():
            """Wrapper that logs progress during long waits"""
            warn_interval = 60
            call_start = datetime.now()
            
            def _do_call():
                return client.models.generate_content(
                    model=self.config.model_name,
                    contents=contents,
                    config=gen_config,
                )
            
            # Run sync call in thread pool
            task = asyncio.get_event_loop().run_in_executor(None, _do_call)
            
            while True:
                try:
                    return await asyncio.wait_for(asyncio.shield(task), timeout=warn_interval)
                except asyncio.TimeoutError:
                    elapsed = (datetime.now() - call_start).total_seconds()
                    self._logger.warning(f"[LLM] Still waiting for API response... elapsed={elapsed:.0f}s")
                    if task.done():
                        return task.result()
                    continue
        
        async def _call():
            return await _call_with_progress()
        
        response = await self._retry_with_backoff(_call)
        latency = (datetime.now() - start_time).total_seconds()
        
        # Extract content and tool calls from response
        content = ""
        tool_calls = []
        finish_reason = "stop"
        
        if response.candidates:
            candidate = response.candidates[0]
            finish_reason = str(candidate.finish_reason) if candidate.finish_reason else "stop"
            
            for part in candidate.content.parts:
                if hasattr(part, 'text') and part.text:
                    content += part.text
                elif hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tc = {
                        "id": f"call_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": fc.name,
                            "arguments": json.dumps(dict(fc.args)) if fc.args else "{}",
                        }
                    }
                    # Preserve thought_signature for Gemini 3 multi-turn function calling
                    if hasattr(part, 'thought_signature') and part.thought_signature:
                        tc["thought_signature"] = part.thought_signature
                    tool_calls.append(tc)
        
        # Get usage stats
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
        
        has_tool_calls = bool(tool_calls)
        if has_tool_calls:
            finish_reason = "tool_calls"
        
        self._logger.info(f"[LLM Response] latency={latency:.1f}s, prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, tool_calls={has_tool_calls}, finish={finish_reason}")
        
        return LLMResponse(
            content=content,
            model=self.config.model_name,
            finish_reason=finish_reason,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            tool_calls=tool_calls if tool_calls else None,
            raw_response=response,
            latency=latency,
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat response from Gemini"""
        client = self._get_client()
        from google.genai import types
        
        # Convert messages
        system_instruction, contents = self._convert_messages_to_google(messages)
        
        gen_config = types.GenerateContentConfig(
            temperature=temperature or self.config.temperature,
            max_output_tokens=max_tokens or self.config.max_tokens,
            system_instruction=system_instruction,
        )
        
        if stop:
            gen_config.stop_sequences = stop
        
        def _stream():
            return client.models.generate_content_stream(
                model=self.config.model_name,
                contents=contents,
                config=gen_config,
            )
        
        # Run in thread pool since SDK is sync
        stream = await asyncio.get_event_loop().run_in_executor(None, _stream)
        
        for chunk in stream:
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        yield part.text


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """
    Factory function to create LLM client based on config
    
    Args:
        config: LLM configuration
        
    Returns:
        Appropriate LLM client instance
    """
    provider_map = {
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.ANTHROPIC: AnthropicClient,
        LLMProvider.GOOGLE: GoogleClient,  # Gemini via OpenAI-compatible API
        LLMProvider.AZURE: OpenAIClient,  # Azure uses OpenAI-compatible API
        LLMProvider.LOCAL: LocalLLMClient,
        LLMProvider.CUSTOM: LocalLLMClient,  # Custom endpoints use OpenAI-compatible API
    }
    
    client_class = provider_map.get(config.provider)
    if not client_class:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    return client_class(config)


# Convenience class for easy usage
class LLM:
    """
    High-level LLM interface
    
    Usage:
        llm = LLM(config)
        response = await llm.chat("What is 2+2?")
        
        # Or with system prompt
        response = await llm.chat(
            "Translate to French: Hello",
            system="You are a translator."
        )
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = create_llm_client(config)
        self._history: list[Message] = []
    
    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        history: bool = False,
        **kwargs
    ) -> str:
        """
        Simple chat interface
        
        Args:
            prompt: User message
            system: System prompt
            history: Whether to include conversation history
            
        Returns:
            Assistant response content
        """
        messages = []
        
        if system:
            messages.append(Message.system(system))
        
        if history:
            messages.extend(self._history)
        
        user_msg = Message.user(prompt)
        messages.append(user_msg)
        
        response = await self._client.chat(messages, **kwargs)
        
        if history:
            self._history.append(user_msg)
            self._history.append(Message.assistant(response.content))
        
        return response.content
    
    async def chat_with_response(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Chat and return full response object
        """
        messages = []
        if system:
            messages.append(Message.system(system))
        messages.append(Message.user(prompt))
        
        return await self._client.chat(messages, **kwargs)
    
    async def chat_messages(
        self,
        messages: list[Message],
        **kwargs
    ) -> LLMResponse:
        """
        Chat with explicit message list
        """
        return await self._client.chat(messages, **kwargs)
    
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming chat
        """
        messages = []
        if system:
            messages.append(Message.system(system))
        messages.append(Message.user(prompt))
        
        async for chunk in self._client.chat_stream(messages, **kwargs):
            yield chunk
    
    def clear_history(self) -> None:
        """Clear conversation history"""
        self._history.clear()
    
    @property
    def client(self) -> BaseLLMClient:
        """Get underlying client for advanced usage"""
        return self._client

