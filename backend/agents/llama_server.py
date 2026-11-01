import atexit
import ctypes
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.config import (
    DEFAULT_LLAMA_SERVER_PATH,
    DEFAULT_LLAMA_SERVER_DLL,
    DEFAULT_GGUF_MODEL_PATH,
    DEFAULT_LLAMA_SERVER_PORT,
    DEFAULT_LLAMA_SERVER_URL,
    DEFAULT_LLAMA_SERVER_CTX,
)

logger = logging.getLogger("anyrag.llama_server")


class LlamaServerManager:
    """
    Manages a warm background llama-server process.
    Provides sub-second inference by avoiding model weight reloading on every query.
    """

    _instance: Optional["LlamaServerManager"] = None

    def __init__(
        self,
        model_path: Optional[Path] = None,
        port: int = DEFAULT_LLAMA_SERVER_PORT,
        ctx_size: int = DEFAULT_LLAMA_SERVER_CTX,
        server_url: Optional[str] = None,
    ):
        self.model_path = Path(model_path or DEFAULT_GGUF_MODEL_PATH)
        self.port = port
        self.ctx_size = ctx_size
        self.server_url = (server_url or f"http://127.0.0.1:{self.port}").rstrip("/")
        self.process: Optional[subprocess.Popen] = None
        self._owns_process = False

    @classmethod
    def get_instance(cls) -> "LlamaServerManager":
        """Singleton accessor for shared warm process across queries."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_healthy(self) -> bool:
        """Check if llama-server is currently running and ready to accept requests."""
        url = f"{self.server_url}/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AnyRAG"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("status") in ["ok", "no slot available"]
                return False
        except urllib.error.HTTPError as e:
            # 503 means model is still loading
            return False
        except Exception:
            return False

    def ensure_running(self, timeout: float = 60.0) -> bool:
        """
        Ensure the warm llama-server process is active.
        If not active, launches it and waits until /health reports ready.
        """
        if self.is_healthy():
            return True

        if not self.model_path.exists():
            logger.warning(f"GGUF model file not found at {self.model_path}")
            return False

        logger.info(f"Starting warm llama-server on port {self.port}...")
        started = self._spawn_server()
        if not started:
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.process is not None and self.process.poll() is not None:
                logger.error(f"llama-server process exited prematurely with code {self.process.poll()}")
                return False
            if self.is_healthy():
                logger.info(f"Warm llama-server is ready on {self.server_url} ({time.time() - start_time:.1f}s).")
                return True
            time.sleep(0.5)

        logger.error(f"Timeout waiting for llama-server to become healthy after {timeout}s.")
        return False

    def _spawn_server(self) -> bool:
        """Spawns the llama-server background process."""
        abs_model = str(self.model_path.resolve())
        # Check if prebuilt executable exists
        if DEFAULT_LLAMA_SERVER_PATH.exists():
            cmd = [
                str(DEFAULT_LLAMA_SERVER_PATH),
                "-m", abs_model,
                "--port", str(self.port),
                "--host", "127.0.0.1",
                "-c", str(self.ctx_size),
                "-ngl", "33",
            ]
        elif DEFAULT_LLAMA_SERVER_DLL.exists():
            # Launch through dedicated runner module
            cmd = [
                sys.executable,
                "-m", "backend.agents.llama_server_runner",
                "--model", abs_model,
                "--port", str(self.port),
                "--ctx", str(self.ctx_size),
            ]
        else:
            logger.warning("No llama-server binary or DLL found.")
            return False

        try:
            # Set up DLL search directory in environment for child process
            env = dict(os.environ)
            runtime_dir = str(DEFAULT_LLAMA_SERVER_DLL.parent)
            env["PATH"] = runtime_dir + os.pathsep + env.get("PATH", "")

            self.process = subprocess.Popen(
                cmd,
                cwd=runtime_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            self._owns_process = True
            atexit.register(self.stop)
            return True
        except Exception as e:
            logger.error(f"Failed to spawn llama-server process: {e}")
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 384,
        temperature: float = 0.3,
    ) -> str:
        """
        Sends completion request to warm llama-server.
        Uses OpenAI-compatible /v1/chat/completions endpoint.
        """
        if not self.ensure_running():
            from backend.agents.llm_client import LLMConnectionError
            raise LLMConnectionError(f"llama-server is not running and could not be started on {self.server_url}")

        url = f"{self.server_url}/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "AnyRAG"},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return ""
        except Exception as e:
            from backend.agents.llm_client import LLMGenerationError
            raise LLMGenerationError(f"llama-server request failed: {e}") from e

    def stop(self):
        """Terminates the spawned llama-server process if owned by this manager."""
        if self._owns_process and self.process is not None:
            logger.info("Stopping warm llama-server process...")
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
            self._owns_process = False


def _run_server_main():
    """
    Subprocess entry point to run llama-server via llama-server-impl.dll.
    Invoked with: python -m backend.agents.llama_server --model <path> --port <port> --ctx <ctx>
    """
    import argparse
    parser = argparse.ArgumentParser(description="AnyRAG Llama Server Runner")
    parser.add_argument("--model", type=str, required=True, help="Path to GGUF model")
    parser.add_argument("--port", type=str, default="8080", help="Port to listen on")
    parser.add_argument("--ctx", type=str, default="4096", help="Context size")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    parser.add_argument("--ngl", type=str, default="33", help="GPU layers to offload")
    args = parser.parse_args()

    runtime_dir = str(DEFAULT_LLAMA_SERVER_DLL.parent)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(runtime_dir)
    os.chdir(runtime_dir)

    # Preload llama backend
    try:
        llama_dll = ctypes.CDLL(os.path.join(runtime_dir, "llama.dll"))
        if hasattr(llama_dll, "ggml_backend_load_all"):
            llama_dll.ggml_backend_load_all()
    except Exception:
        pass

    dll = ctypes.CDLL(os.path.join(runtime_dir, "llama-server-impl.dll"))
    server_func = getattr(dll, "?llama_server@@YAHHPEAPEAD@Z")
    server_func.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
    server_func.restype = ctypes.c_int

    cli_args = [
        b"llama-server",
        b"-m", args.model.encode("utf-8"),
        b"--port", args.port.encode("utf-8"),
        b"--host", args.host.encode("utf-8"),
        b"-c", args.ctx.encode("utf-8"),
        b"-ngl", args.ngl.encode("utf-8"),
    ]
    arr = (ctypes.c_char_p * len(cli_args))(*cli_args)
    sys.exit(server_func(len(cli_args), arr))


if __name__ == "__main__":
    _run_server_main()
