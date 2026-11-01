import json
import logging
import os
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from backend.config import (
    DEFAULT_LLAMA_CLI_PATH,
    DEFAULT_LLAMA_SERVER_DLL,
    DEFAULT_LLAMA_SERVER_PATH,
    DEFAULT_GGUF_MODEL_PATH,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL_ALIASES,
)

logger = logging.getLogger("anyrag.llm_client")


class LLMError(Exception):
    """Base exception for all LLM errors in AnyRAG."""
    pass


class LLMConnectionError(LLMError):
    """Raised when an LLM service or server is unreachable or offline."""
    pass


class LLMGenerationError(LLMError):
    """Raised when an LLM provider fails to generate a valid response."""
    pass


class LLMClient:
    """
    Unified LLM client supporting:
    1. Primary Cloud: OpenRouter (Kimi / DeepSeek via high-speed API)
    2. Local Fallback: Warm standalone llama-server (sub-second local inference with phi-4-mini GGUF)
    3. Secondary Remote: Ollama (if service running) or OpenAI-compatible API
    4. Offline Emergency Fallback: Smart grounded extractive synthesis with explicit API notice banner
    """

    def __init__(
        self,
        provider: str = "auto",  # 'auto', 'openrouter', 'llamacpp', 'ollama', 'openai', 'gemini', 'fallback'
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        openrouter_base_url: Optional[str] = None,
    ):
        self.provider = provider

        # OpenRouter configuration (Primary cloud endpoint)
        self.openrouter_api_key = (
            openrouter_api_key
            or os.getenv("OPENROUTER_API_KEY")
            or OPENROUTER_API_KEY
        )
        self.openrouter_base = (
            openrouter_base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or DEFAULT_OPENROUTER_BASE_URL
        )
        raw_or_model = (
            openrouter_model
            or os.getenv("ANYRAG_OPENROUTER_MODEL")
            or os.getenv("ANYRAG_CLOUD_MODEL")
            or DEFAULT_OPENROUTER_MODEL
        )
        self.openrouter_model = OPENROUTER_MODEL_ALIASES.get(raw_or_model.lower(), raw_or_model)

        # General / Ollama / OpenAI configuration
        self.model_name = (
            model_name
            or os.getenv("ANYRAG_LLM_MODEL")
            or os.getenv("ANYRAG_OLLAMA_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or DEFAULT_OLLAMA_MODEL
        )

        # If user explicitly passed a model_name like 'kimi', 'deepseek', or full 'moonshotai/kimi-k2'
        if model_name:
            resolved_or = OPENROUTER_MODEL_ALIASES.get(model_name.lower(), model_name)
            if "/" in resolved_or or model_name.lower() in OPENROUTER_MODEL_ALIASES:
                self.openrouter_model = resolved_or

        self.api_base = api_base or os.getenv("OLLAMA_HOST") or os.getenv("LLM_API_BASE") or DEFAULT_OLLAMA_HOST
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")

    def generate(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate a response given system prompt, user prompt, and context chunks.
        Follows the exact production chain:
        1. Primary Cloud: OpenRouter (Kimi / DeepSeek)
        2. Local Fallback: Warm standalone llama-server (Phi-4-mini GGUF)
        3. Secondary Remote: Ollama (if service running)
        4. Standard OpenAI-compatible API (if api_key available)
        5. Emergency Grounded Extractive Fallback (with explicit API notice banner)
        """
        # Explicit single-provider invocations
        if self.provider == "openrouter":
            return self._call_openrouter(system_prompt, user_prompt, context_chunks)

        if self.provider == "ollama":
            return self._call_ollama(system_prompt, user_prompt, context_chunks)

        if self.provider == "llamacpp":
            return self._call_llama_server(system_prompt, user_prompt, context_chunks)

        if self.provider in ["openai", "gemini"]:
            return self._call_openai(system_prompt, user_prompt, context_chunks)

        if self.provider == "fallback":
            return self._smart_offline_synthesis(system_prompt, user_prompt, context_chunks)

        # Provider == 'auto': Cascade through the exact resilient chain
        errors = []

        # 1. Primary Cloud: OpenRouter (Kimi / DeepSeek)
        if self.openrouter_api_key or os.getenv("OPENROUTER_API_KEY"):
            try:
                result = self._call_openrouter(system_prompt, user_prompt, context_chunks)
                if result:
                    return result
            except Exception as e:
                logger.info(f"OpenRouter cloud attempt ({self.openrouter_model}) failed: {e}. Falling back to local offline model...")
                errors.append(f"openrouter: {e}")

        # 2. Local Fallback: Standalone warm llama-server (Phi-4-mini GGUF)
        if (DEFAULT_LLAMA_SERVER_PATH.exists() or DEFAULT_LLAMA_SERVER_DLL.exists()) and DEFAULT_GGUF_MODEL_PATH.exists():
            try:
                result = self._call_llama_server(system_prompt, user_prompt, context_chunks)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Local llama-server fallback attempt failed: {e}. Trying CLI / remote...")
                errors.append(f"llama-server: {e}")
                if DEFAULT_LLAMA_CLI_PATH.exists():
                    try:
                        result = self._call_llama_cli(system_prompt, user_prompt, context_chunks)
                        if result:
                            return result
                    except Exception as cli_e:
                        errors.append(f"llama-cli: {cli_e}")

        # 3. Secondary: Ollama (if running)
        try:
            result = self._call_ollama(system_prompt, user_prompt, context_chunks)
            if result:
                return result
        except Exception as e:
            errors.append(f"ollama: {e}")

        # 4. Secondary: Direct OpenAI API (if separate key provided)
        if self.api_key and self.api_key != self.openrouter_api_key:
            try:
                result = self._call_openai(system_prompt, user_prompt, context_chunks)
                if result:
                    return result
            except Exception as e:
                errors.append(f"openai: {e}")

        # 5. Offline Grounded Extractive Synthesis Fallback
        if context_chunks is not None:
            return self._smart_offline_synthesis(system_prompt, user_prompt, context_chunks)

        raise LLMGenerationError(
            f"All LLM providers failed and no context was provided for offline synthesis. Details: {'; '.join(errors)}"
        )

    def _call_openrouter(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 1024,
        model: Optional[str] = None
    ) -> str:
        """
        Execute high-speed inference against OpenRouter API.
        Primary cloud provider for Kimi (moonshotai/kimi-k2) and DeepSeek (deepseek/deepseek-chat).
        """
        api_key = self.openrouter_api_key or self.api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise LLMConnectionError("OPENROUTER_API_KEY is not configured for OpenRouter cloud provider.")

        target_model = model or self.openrouter_model
        target_model = OPENROUTER_MODEL_ALIASES.get(target_model.lower(), target_model)

        api_url = f"{self.openrouter_base.rstrip('/')}/chat/completions"
        context_text = ""
        if context_chunks:
            context_text = "\n\nRelevant Context:\n" + "\n---\n".join(
                f"[Score: {c.get('score', 0):.2f} | Section: {c.get('section_title') or 'General'}]\n{c['content']}"
                for c in context_chunks
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n{context_text}" if context_text else user_prompt}
        ]

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/anyrag",
            "X-Title": "AnyRAG"
        }

        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    if content:
                        return content.strip()
                if "error" in data:
                    raise LLMGenerationError(f"OpenRouter API returned error: {data['error']}")
                raise LLMGenerationError(f"Unexpected response structure from OpenRouter: {data}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if e.code in (401, 403):
                raise LLMConnectionError(f"OpenRouter authentication failure ({e.code}): {err_body}") from e
            elif e.code in (402, 429):
                raise LLMConnectionError(f"OpenRouter credit exhausted / rate limit ({e.code}): {err_body}") from e
            raise LLMGenerationError(f"OpenRouter HTTP error ({e.code}): {err_body}") from e
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Could not connect to OpenRouter at {api_url}: {e}") from e
        except Exception as e:
            raise LLMGenerationError(f"OpenRouter generation failed: {e}") from e

    def _call_llama_server(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]]) -> str:
        """Execute inference against warm llama-server."""
        from backend.agents.llama_server import LlamaServerManager

        server = LlamaServerManager.get_instance()
        context_text = ""
        if context_chunks:
            context_text = "\n\nRelevant Context:\n" + "\n---\n".join(
                f"[{c.get('section_title') or 'General'}]\n{c['content']}" for c in context_chunks
            )

        full_prompt = f"{user_prompt}\n{context_text}" if context_text else user_prompt
        try:
            return server.generate(prompt=full_prompt, system_prompt=system_prompt)
        except (LLMConnectionError, LLMGenerationError):
            raise
        except Exception as e:
            raise LLMGenerationError(f"llama-server generation failed: {e}") from e

    def _call_llama_cli(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]]) -> str:
        """Legacy standalone llama-cli execution (used as secondary fallback if server unavailable)."""
        if not (DEFAULT_LLAMA_CLI_PATH.exists() and DEFAULT_GGUF_MODEL_PATH.exists()):
            raise LLMConnectionError(f"llama-cli binary or model not found at {DEFAULT_LLAMA_CLI_PATH}")

        context_text = ""
        if context_chunks:
            context_text = "\n\nRelevant Context:\n" + "\n---\n".join(
                f"[{c.get('section_title') or 'General'}]\n{c['content']}" for c in context_chunks
            )

        formatted_prompt = (
            f"<|system|>\n{system_prompt}<|end|>\n"
            f"<|user|>\n{user_prompt}\n{context_text}<|end|>\n"
            f"<|assistant|>\n"
        )

        cmd = [
            str(DEFAULT_LLAMA_CLI_PATH),
            "-m", str(DEFAULT_GGUF_MODEL_PATH),
            "-p", formatted_prompt,
            "-n", "384",
            "-ngl", "33",
            "--simple-io",
            "--no-display-prompt"
        ]

        try:
            res = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=90
            )
            if res.returncode == 0 and res.stdout.strip():
                out = res.stdout.strip()
                return out.replace("<|end|>", "").replace("<|endoftext|>", "").strip()
            raise LLMGenerationError(f"llama-cli returned code {res.returncode}: {res.stderr.strip()[:200]}")
        except subprocess.TimeoutExpired as e:
            raise LLMGenerationError("llama-cli timed out after 90 seconds.") from e
        except Exception as e:
            raise LLMGenerationError(f"llama-cli execution error: {e}") from e

    def _get_installed_ollama_models(self) -> List[str]:
        """Fetch models installed in local Ollama instance."""
        try:
            url = f"{self.api_base.rstrip('/')}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def _call_ollama(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]]) -> str:
        url = f"{self.api_base.rstrip('/')}/api/generate"
        try:
            target_model = self.model_name
            # Only match against local tags if running against local daemon without explicit model set
            if ("localhost" in self.api_base or "127.0.0.1" in self.api_base) and not os.getenv("ANYRAG_OLLAMA_MODEL"):
                installed = self._get_installed_ollama_models()
                if installed and target_model not in installed:
                    matched = [m for m in installed if target_model.split(":")[0] in m]
                    target_model = matched[0] if matched else target_model

            context_text = ""
            if context_chunks:
                context_text = "\n\nRelevant Context:\n" + "\n---\n".join(
                    f"[Score: {c.get('score', 0):.2f} | Section: {c.get('section_title') or 'General'}]\n{c['content']}"
                    for c in context_chunks
                )

            full_prompt = f"{user_prompt}\n{context_text}" if context_text else user_prompt
            payload = {
                "model": target_model,
                "prompt": full_prompt,
                "system": system_prompt,
                "stream": False
            }

            headers = {"Content-Type": "application/json"}
            auth_token = self.api_key or os.getenv("OLLAMA_API_KEY")
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Could not connect to Ollama at {self.api_base}: {e}") from e
        except Exception as e:
            raise LLMGenerationError(f"Ollama generation failed: {e}") from e

    def _call_openai(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]]) -> str:
        if not self.api_key:
            raise LLMGenerationError("API key not configured for OpenAI/Gemini provider.")

        api_url = self.api_base if "openai" in self.api_base else "https://api.openai.com/v1/chat/completions"
        context_text = ""
        if context_chunks:
            context_text = "\n\nRelevant Context:\n" + "\n---\n".join(
                f"[{c.get('section_title') or 'General'}]\n{c['content']}" for c in context_chunks
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n{context_text}"}
        ]

        payload = {
            "model": self.model_name if self.model_name != "phi4-mini" else "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.3
        }

        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Could not connect to API at {api_url}: {e}") from e
        except Exception as e:
            raise LLMGenerationError(f"API generation error: {e}") from e

    def _smart_offline_synthesis(self, system_prompt: str, user_prompt: str, context_chunks: Optional[List[Dict[str, Any]]]) -> str:
        """
        Grounded extractive fallback that operates 100% locally
        when no LLM API or local model service is reachable.
        Explicitly flags that the API is unavailable while providing
        the exact retrieved text excerpts.
        """
        if not context_chunks:
            return (
                "⚠️ [API Unavailable]: Live LLM service could not be reached, and no relevant "
                f"document excerpts were found addressing: '{user_prompt}'."
            )

        lines = [
            "⚠️ **[Notice: LLM API Unavailable]**",
            "Live generation services could not be reached. Displaying exact grounded excerpts extracted from the document:",
            ""
        ]

        for idx, c in enumerate(context_chunks, 1):
            title = c.get('section_title') or f"Excerpt {idx}"
            score = c.get('score', 0.0)
            page_info = f" (Page/Slide {c['page_number']})" if c.get('page_number') else ""
            lines.append(f"**{title}**{page_info} [Relevance: {score:.2f}]:")
            clean_content = c['content'].replace("\n", " ").strip()
            if len(clean_content) > 350:
                clean_content = clean_content[:350] + "..."
            lines.append(f"> {clean_content}")
            lines.append("")

        lines.append("---")
        lines.append(
            f"ℹ️ *Status*: API unavailable. Extracted {len(context_chunks)} source excerpt(s) directly from document for '{user_prompt}'."
        )
        return "\n".join(lines)
