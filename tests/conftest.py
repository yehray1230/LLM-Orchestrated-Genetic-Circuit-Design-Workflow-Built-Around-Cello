from __future__ import annotations

import sys
import types
import os


os.environ.setdefault("MPLBACKEND", "Agg")

litellm_stub = types.ModuleType("litellm")
litellm_stub.completion = lambda **_: None

litellm_exceptions_stub = types.ModuleType("litellm.exceptions")
for name in ["AuthenticationError", "RateLimitError", "BadRequestError", "APIError"]:
    setattr(litellm_exceptions_stub, name, type(name, (Exception,), {}))
litellm_stub.exceptions = litellm_exceptions_stub

litellm_caching_stub = types.ModuleType("litellm.caching")
litellm_caching_stub.Cache = lambda **_: object()

sys.modules["litellm"] = litellm_stub
sys.modules["litellm.exceptions"] = litellm_exceptions_stub
sys.modules["litellm.caching"] = litellm_caching_stub
