from typing import Protocol, Optional, Dict, Any


class LLMClient(Protocol):
    """Protocol contract for LLM structured JSON generation."""

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Send prompts to LLM and return parsed JSON dictionary."""
        ...


class MockLLMClient:
    """Mock LLM client for deterministic, offline testing."""

    def __init__(self, response_dict: Optional[Dict[str, Any]] = None):
        self.response_dict = response_dict or {}
        self.last_system_prompt: Optional[str] = None
        self.last_user_prompt: Optional[str] = None

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response_dict


class AnthropicLLMClient:
    """Production LLM client utilizing Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        import json
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_content = response.content[0].text
        # Clean any accidental markdown code fences
        cleaned = text_content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
