"""test_run_command_grants.py — operator session grants for run_command.

Covers: the grant store + secret refusal, the sandbox widening (granted reads / network),
that dispatch INJECTS the operator grant and STRIPS anything the AI supplied (the model can't
self-grant), and the operator chat-command surface.
"""
import os
import shutil
import tempfile

import pytest

from executor.tool_dispatch.tools.run_command import RunCommandTool, _bwrap_argv
from orchestrator.executor_client import execute_tool
from orchestrator import run_command_grants as G
from orchestrator.http.chat_endpoint import _handle_grant_command

pytestmark = pytest.mark.skipif(
    shutil.which("bwrap") is None, reason="bubblewrap (bwrap) not installed"
)

_rc = RunCommandTool()


@pytest.fixture
def granted_dir():
    """A dir OUTSIDE the workspace (under home, not ~/.gorgon) with a file to read."""
    G.clear()
    d = tempfile.mkdtemp(dir=os.path.expanduser("~"), prefix="grant_test_")
    with open(os.path.join(d, "data.txt"), "w") as f:
        f.write("GRANTED_CONTENT")
    yield d
    G.clear()
    shutil.rmtree(d, ignore_errors=True)


def test_refuses_secret_paths():
    """The VM base and any ancestor of it are refused — whatever the VM base currently IS.

    ⇒⇒ **THIS ASSERTED A LITERAL AND NOW ASSERTS THE INVARIANT** (2026-09-19). It read
      `add_read(expanduser("~/.gorgon"))`, hardcoding the production path. When the executor's
      directories were re-rooted under `GORGON_HOME` so the suite would stop binding the
      operator's real storage, the module's own base moved to the sandbox and the test went red
      against a path the module no longer guards — **reporting a regression where there was
      none**. Checked both ways at the time: production still refuses `~/.gorgon` and `~`, and
      the sandbox refuses its own home.

    ⇒ The rule was never about that string. It is *the VM base is secret, and so is anything
      containing it*, and reading it off `G.VM_BASE_DIR` tests exactly that.
    """
    base = G.VM_BASE_DIR
    assert G.add_read(base)["success"] is False                    # the home itself
    assert G.add_read(os.path.dirname(base))["success"] is False   # an ancestor of it
    assert G.add_read("/definitely/missing/xyz")["success"] is False   # nonexistent


def test_ungranted_read_blocked(granted_dir):
    f = os.path.join(granted_dir, "data.txt")
    r = _rc.run({"code": f"cat {f} 2>&1"}, None)   # no grant
    assert "GRANTED_CONTENT" not in r["stdout"]


def test_granted_read_works(granted_dir):
    f = os.path.join(granted_dir, "data.txt")
    G.add_read(granted_dir)
    r = _rc.run({"code": f"cat {f}", "_grants": G.snapshot()}, None)
    assert "GRANTED_CONTENT" in r["stdout"]


def test_dispatch_injects_operator_grant_and_strips_ai_fake(granted_dir):
    """execute_tool must ignore an AI-supplied _grants and inject the real operator grant."""
    f = os.path.join(granted_dir, "data.txt")
    G.add_read(granted_dir)                                   # operator grant
    fake = {"read_paths": ["/etc"], "net": True}             # AI tries to self-grant more
    res = execute_tool("run_command", {"code": f"cat {f}", "_grants": fake}, verbose=True)
    out = res.get("result", res)
    assert "GRANTED_CONTENT" in out.get("stdout", "")        # operator grant applied
    # and the AI's fake didn't leak /etc write/read or net — verified structurally below


def test_net_gated_by_grant():
    G.clear()
    assert "--unshare-net" in _bwrap_argv(["/bin/sh", "-c", "x"], G.snapshot())   # off by default
    G.set_net(True)
    assert "--unshare-net" not in _bwrap_argv(["/bin/sh", "-c", "x"], G.snapshot())  # on when granted
    G.clear()


def test_chat_intercept(granted_dir):
    assert "GRANTED" in _handle_grant_command(f"grant read {granted_dir}")
    assert granted_dir in _handle_grant_command("grants")
    assert "network access GRANTED" in _handle_grant_command("grant net")
    assert "revoked" in _handle_grant_command("revoke")
    assert _handle_grant_command("list all my vms") is None   # not a grant command → falls through


def test_grant_read_usage():
    assert "Usage" in _handle_grant_command("grant read")
