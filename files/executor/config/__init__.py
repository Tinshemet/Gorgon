"""
executor/config — Configuration for the executor SERVER role (loader + data).

The settings the executor process needs to serve the orchestrator: its bind address,
its incoming token, and the streaming/limit constants for disk delivery and
run_command.

  server_config.defaults.json  — the single manifest of every setting + default
  server_config.json           — this machine's overrides (win on merge)

Same shape as shared/, client/, admin/ and orchestrator/config: this file holds no
literal setting values, so callers say `config.RUN_COMMAND_TIMEOUT_S` instead of
repeating `_CFG.get("run_command_timeout_s", 60)` at each site.

NOT to be confused with the two OTHER executor configs, which stay where they are on
purpose (placement follows dependencies):
  * executor/api/config.json          — VM/QEMU hardware facts, read by ~10 modules
                                        that all live inside executor/api/
  * executor/tool_dispatch/config/    — the tool layer's own config, already a folder

The EXECUTOR_TOKEN environment variable still wins over both files.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path: str) -> dict:
    """Load a JSON file, returning an empty dict on any error."""
    try:
        return json.load(open(path))
    except Exception:
        return {}


_DEFAULTS  = load_json(os.path.join(_HERE, "server_config.defaults.json"))
_OVERRIDES = load_json(os.path.join(_HERE, "server_config.json"))
_CFG       = {**_DEFAULTS, **_OVERRIDES}   # machine overrides win


def _c(key: str):
    """Fetch a merged setting; KeyError if the defaults manifest is missing it."""
    return _CFG[key]


HOST  = _c("host")
PORT  = _c("port")
TOKEN = _c("token")

IO_CHUNK_BYTES  = _c("io_chunk_bytes")    # disk stream chunk
TAR_CHUNK_BYTES = _c("tar_chunk_bytes")   # bundle tar.gz chunk

RUN_COMMAND_TIMEOUT_S        = _c("run_command_timeout_s")
RUN_COMMAND_MAX_OUTPUT_BYTES = _c("run_command_max_output_bytes")


def as_dict() -> dict:
    """The merged config, defaults ∪ overrides."""
    return dict(_CFG)
