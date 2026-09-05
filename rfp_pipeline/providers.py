"""Pluggable LLM provider layer.

Select with LLM_PROVIDER env var: openai | azure | anthropic | ollama | mock.
When no provider is configured (or explicitly 'mock'), a deterministic mock
provider is used so the whole pipeline runs offline with repeatable output.
"""
import json
import os
import urllib.request


def get_provider(name=None):
    name = (name or os.environ.get("LLM_PROVIDER") or "mock").lower()
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAIProvider(key)
    if name == "azure":
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        key = os.environ.get("AZURE_OPENAI_API_KEY")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        if not (endpoint and key and deployment):
            raise RuntimeError("Azure OpenAI needs AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT")
        return AzureOpenAIProvider(endpoint, key, deployment)
    if name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(key)
    if name == "ollama":
        return OllamaProvider(os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                              os.environ.get("OLLAMA_MODEL", "llama3.1"))
    return MockProvider()


class BaseProvider:
    label = "base"

    def complete(self, system, prompt):
        raise NotImplementedError

    def _post(self, url, payload, headers):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", **headers})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())


class OpenAIProvider(BaseProvider):
    label = "openai"

    def __init__(self, key):
        self.key = key
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, system, prompt):
        data = self._post("https://api.openai.com/v1/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }, {"Authorization": f"Bearer {self.key}"})
        return data["choices"][0]["message"]["content"]


class AzureOpenAIProvider(BaseProvider):
    label = "azure-openai"

    def __init__(self, endpoint, key, deployment):
        self.url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version=2024-08-01-preview"
        self.key = key

    def complete(self, system, prompt):
        data = self._post(self.url, {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }, {"api-key": self.key})
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(BaseProvider):
    label = "anthropic"

    def __init__(self, key):
        self.key = key
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def complete(self, system, prompt):
        data = self._post("https://api.anthropic.com/v1/messages", {
            "model": self.model, "max_tokens": 4096, "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }, {"x-api-key": self.key, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in data["content"])


class OllamaProvider(BaseProvider):
    label = "ollama"

    def __init__(self, host, model):
        self.host = host.rstrip("/")
        self.model = model

    def complete(self, system, prompt):
        data = self._post(f"{self.host}/api/chat", {
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }, {})
        return data["message"]["content"]


class MockProvider(BaseProvider):
    """Deterministic offline provider. Extracts structure from the RFP text with
    rules instead of a model, so runs are repeatable and need no keys."""

    label = "mock"

    def complete(self, system, prompt):
        # The pipeline stages pass structured extraction requests; the mock
        # answers them from keyword/regex evidence in the prompt itself.
        from . import mock_brain
        return mock_brain.answer(system, prompt)
