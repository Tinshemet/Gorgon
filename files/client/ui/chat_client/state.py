"""
chat_client/state.py — shared mutable state for the curses chat TUI.

Every module reads/writes the SAME objects here: import the module
(``from client.ui.chat_client import state``) and touch ``state.waiting`` etc.
— never ``from state import waiting`` (that copies the binding and desyncs the
draw loop, the HTTP/mission worker threads, and dispatch). ``lock`` guards the
scrollback ``history``; ``resp_q`` carries worker results back to the main
thread; ``quit_event`` ends the loop.
"""

import queue
import threading

history       = []                 # (curses_attr, text) tuples
lock          = threading.Lock()
resp_q        = queue.Queue()      # HTTP / mission worker puts results here
quit_event    = threading.Event()
waiting       = False              # True while an HTTP call is in flight
needs_confirm = False              # True when the server returned needs_input
is_confirm    = False              # whether a pending confirm is auto_confirm
is_password   = False              # True when the server asked for a masked password (forge wizard)
allow_empty   = False              # True when the server's prompt accepts an empty answer
pending_kill  = ""                 # VM name waiting for force-kill confirmation
pending_claim = None               # (action, fact) waiting for operator password
session_id    = ""

# sync data (refreshed from /sync)
remote_vms      = []
remote_profiles = []
commands        = []               # command catalog (help source of truth)
allowed_tools   = set()            # executor allowed-tools list for help filtering

# shortcut command sets — defaults, overridable from /sync
sc_list      = {"list", "vms", "ls"}
sc_system    = {"system"}
sc_profiles  = {"profiles"}
sc_templates = {"templates"}
sc_drift     = {"drift"}
sc_clear     = {"clear session", "forget", "/clear"}
sc_help      = {"help", "?", "/help"}
exit_cmds    = {"exit", "quit", "q", "bye"}
