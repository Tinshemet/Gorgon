# Compatibility shim — replaces this module in sys.modules with the live
# orchestrator.http.api_server object so mock.patch("server.http.api_server.*")
# patches the same module the FastAPI app runs from.
import sys
import importlib

_real = importlib.import_module("orchestrator.http.api_server")
sys.modules[__name__] = _real
