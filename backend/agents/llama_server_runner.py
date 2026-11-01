"""
Standalone subprocess entrypoint to launch llama-server via llama-server-impl.dll.
"""
import argparse
import ctypes
import os
import sys
from pathlib import Path

from backend.config import DEFAULT_LLAMA_SERVER_DLL


def main():
    parser = argparse.ArgumentParser(description="AnyRAG Llama Server Runner")
    parser.add_argument("--model", type=str, required=True, help="Path to GGUF model")
    parser.add_argument("--port", type=str, default="8080", help="Port to listen on")
    parser.add_argument("--ctx", type=str, default="4096", help="Context size")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    parser.add_argument("--ngl", type=str, default="33", help="GPU layers to offload")
    args = parser.parse_args()

    model_abs = str(Path(args.model).resolve())
    runtime_dir = str(DEFAULT_LLAMA_SERVER_DLL.parent)

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(runtime_dir)
    os.chdir(runtime_dir)

    # Preload ggml backend
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
        b"-m", model_abs.encode("utf-8"),
        b"--port", args.port.encode("utf-8"),
        b"--host", args.host.encode("utf-8"),
        b"-c", args.ctx.encode("utf-8"),
        b"-ngl", args.ngl.encode("utf-8"),
    ]
    arr = (ctypes.c_char_p * len(cli_args))(*cli_args)
    sys.exit(server_func(len(cli_args), arr))


if __name__ == "__main__":
    main()
