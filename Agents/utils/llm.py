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
        sanitized_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                new_part = dict(part)
                new_part["text"] = _redact_secrets(new_part["text"])
                sanitized_parts.append(new_part)
            else:
                sanitized_parts.append(part)
        return sanitized_parts
    return content


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
    
    async def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = None,
        **kwargs
    ) -> Any:
        """Retry with exponential backoff"""
        max_retries = max_retries or self.config.retry_attempts
        last_error = None
        
        for attempt in range(max_retries):
            try:
                attempt_start = datetime.now()
                self._logger.debug(f"[LLM] Attempt {attempt + 1}/{max_retries} starting...")
                result = await func(*args, **kwargs)
                elapsed = (datetime.now() - attempt_start).total_seconds()
                self._logger.info(f"[LLM] Attempt {attempt + 1} succeeded in {elapsed:.1f}s")
                return result
            except Exception as e:
                elapsed = (datetime.now() - attempt_start).total_seconds()
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)[:200]  # Truncate long errors
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    self._logger.warning(f"[LLM] Attempt {attempt + 1} failed after {elapsed:.1f}s: [{error_type}] {error_msg}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    self._logger.error(f"[LLM] All {max_retries} attempts failed. Last error: [{error_type}] {error_msg}")
        
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
    
    Uses OpenAI-compatible API endpoint provided by Google.
    Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Google client via OpenAI-compatible API"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
            
            api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
            
            # Google's OpenAI-compatible endpoint
            base_url = self.config.api_base or "https://generativelanguage.googleapis.com/v1beta/openai/"
            
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
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
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> Message:
        """Send chat request to Gemini"""
        client = self._get_client()
        
        # Build request parameters
        request_params = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
        }
        
        if stop:
            request_params["stop"] = stop
        
        # Handle tools/functions
        if tools:
            request_params["tools"] = tools
            if tool_choice:
                request_params["tool_choice"] = tool_choice
        elif functions:
            # Convert legacy functions format to tools
            request_params["tools"] = [{"type": "function", "function": f} for f in functions]
        
        async def _call():
            response = await client.chat.completions.create(**request_params)
            return response
        
        response = await self._retry_with_backoff(_call)
        choice = response.choices[0]
        
        # Build response message
        return Message.assistant(
            content=choice.message.content or "",
            tool_calls=choice.message.tool_calls
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
        
        request_params = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        
        if stop:
            request_params["stop"] = stop
        
        stream = await client.chat.completions.create(**request_params)
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


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

