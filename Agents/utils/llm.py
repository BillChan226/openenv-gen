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

from .config import LLMConfig, LLMProvider


@dataclass
class Message:
    """Chat message"""
    role: str  # "system", "user", "assistant", "function"
    content: str
    name: Optional[str] = None  # For function messages
    function_call: Optional[dict] = None  # For assistant function calls
    tool_calls: Optional[list] = None  # For tool calls
    
    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.function_call:
            d["function_call"] = self.function_call
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role="system", content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role="assistant", content=content)


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
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    self._logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        
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
        
        request_params = {
            "model": self.config.model_name,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
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
        
        async def _call():
            return await client.chat.completions.create(**request_params)
        
        response = await self._retry_with_backoff(_call)
        latency = (datetime.now() - start_time).total_seconds()
        
        choice = response.choices[0]
        message = choice.message
        
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

