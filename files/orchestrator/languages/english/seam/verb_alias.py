"""The verb-alias store — a learnable MASK over a lab operation.

The noun archive (`archive.py`) turns an unknown NOUN into a manifest-shaped row. This is its
verb-side mirror: it turns a learned WORD into an OPERATION the lab ALREADY OWNS.

    relab        ->  reset_lab
    contain it   ->  container_mode(<the patient the surface names>)

The word is a MASK; the expansion is the real verb. Two invariants make the mask safe, and both
are copied straight from siblings that already earned them:

  ⇒ **A MASK CARRIES NO AUTHORITY OF ITS OWN.** The expansion emits a real `Operation`, and the
    authority gate (gate 3 / gate 4) checks THAT operation's operator — never the mask word. A
    mask can do nothing a plain call to the operation could not. This holds ONLY because the
    consult+expand step runs BEFORE the gates (the pipeline slot at `pass2.operations_for`); an
    expansion that reached the model as prose, or landed after the gate, would smuggle authority.

  ⇒ **A MASK MAY NEVER SHADOW A VERB THE LAB OWNS**, the same guard `CONTRACT_VERBS` uses
    (`governing.py`): the consult site asks `word not in manifest_verbs(board)` first, so a
    lab-owned verb always wins and no alias can quietly repaint an order.

The lifecycle is the archive's, to the letter — because the risk is the archive's: one misspoken
alias becoming permanent and silent.

  · `propose()` files a PENDING alias. It DESCRIBES; it does not yet permit.
  · `ratify()` is the operator's signature. Only then does the alias `routes`.
  · `known()` is the only reader anything may route on.
  · `retract()` is the UNALIAS/withdraw path — supersede, never delete, so the store audits back.

This module is the STORE only (surface-agnostic). The declaration surface (what phrase teaches an
alias), the pipeline consult+expand step, and the withdraw verb list are wired in a later,
operator-approved step — see `tmp/verb-alias-design.md`.
"""

import json
import os
import pathlib
import time
from typing import List, NamedTuple, Optional, Tuple

# ⇒ WHO SAID IT. Only a TOLD alias may ever be ratified into routing; a bulk/IMPORTED one
#   describes and never permits — the same rule, and the same words, as the noun archive.
TOLD, IMPORTED = "told", "imported"

PENDING, RATIFIED, SUPERSEDED = "pending", "ratified", "superseded"


class AliasEntry(NamedTuple):
    """One mask word, the lab operation it unfolds to, and how the surface binds to it."""
    word: str                                  # THE MASK — lowercased ("relab", "contain")
    operation: str                             # the manifest operation it expands to ("reset_lab")
    # ⇒ DOES THE SURFACE OBJECT FILL THE OPERATION'S PATIENT? `contain IT` — the `it` the sentence
    #   names becomes the patient of `container_mode`. `relab` binds nothing (it takes no object).
    binds_patient: bool = False
    description: str = ""
    source: str = TOLD
    status: str = PENDING
    said: str = ""                             # the sentence it came from — provenance
    who: Optional[str] = None
    at: Optional[float] = None

    @property
    def routes(self) -> bool:
        """May this alias settle a reading? Only if a person ratified it AND it was told."""
        return self.status == RATIFIED and self.source == TOLD


class AliasStore:
    """The mask store. Append-only, superseded rather than overwritten, keyed by the word."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self._rows: List[AliasEntry] = []
        if self.path and self.path.exists():
            self.load()

    # ── writing ──────────────────────────────────────────────────────────────────────────
    def propose(self, word: str, operation: str, binds_patient: bool = False,
                description: str = "", source: str = TOLD, said: str = "",
                who: Optional[str] = None) -> AliasEntry:
        """File a PENDING alias. It describes; it does not yet permit.

        ⇒ SUPERSESSION RATHER THAN OVERWRITE: a prior ratified alias for the word stays and is
          marked when a newer one is ratified, so a changed mask is always auditable backwards.
        """
        entry = AliasEntry(word=str(word).strip().lower(), operation=str(operation).strip(),
                           binds_patient=bool(binds_patient),
                           description=str(description).strip(), source=source,
                           status=PENDING, said=str(said), who=who, at=time.time())
        self._rows.append(entry)
        return entry

    def ratify(self, word: str, who: Optional[str] = None) -> Optional[AliasEntry]:
        """The operator's signature. The newest pending alias for a word starts routing."""
        word = str(word).strip().lower()
        fresh = [e for e in self._rows if e.word == word and e.status == PENDING]
        if not fresh:
            return None
        keep = fresh[-1]
        out: List[AliasEntry] = []
        for e in self._rows:
            if e.word == word and e.status == RATIFIED:
                e = e._replace(status=SUPERSEDED)      # the old mask is kept, not deleted
            elif e is keep:
                e = e._replace(status=RATIFIED, who=who or e.who)
            elif e.word == word and e.status == PENDING:
                e = e._replace(status=SUPERSEDED)      # an older proposal never silently wins
            out.append(e)
        self._rows = out
        return self.known(word)

    def retract(self, word: str) -> Optional[AliasEntry]:
        """The UNALIAS path. Withdraw the routing alias by superseding it — the row survives."""
        word = str(word).strip().lower()
        gone = None
        out: List[AliasEntry] = []
        for e in self._rows:
            if e.word == word and e.status == RATIFIED:
                gone = e
                e = e._replace(status=SUPERSEDED)
            out.append(e)
        self._rows = out
        return gone

    # ── reading ──────────────────────────────────────────────────────────────────────────
    def known(self, word: str) -> Optional[AliasEntry]:
        """The RATIFIED alias for this word, or None. The only reader anything may route on."""
        word = str(word).strip().lower()
        for e in reversed(self._rows):
            if e.word == word and e.routes:
                return e
        return None

    def reject(self, word: str) -> int:
        """Refuse the PENDING proposals for a word — the ones nobody signed. Returns how many."""
        word = str(word).strip().lower()
        n = 0
        out: List[AliasEntry] = []
        for e in self._rows:
            if e.word == word and e.status == PENDING:
                e = e._replace(status=SUPERSEDED); n += 1
            out.append(e)
        self._rows = out
        return n

    def ratified(self) -> List[AliasEntry]:
        """Every mask in force (routing), newest per word."""
        seen, out = set(), []
        for e in reversed(self._rows):
            if e.routes and e.word not in seen:
                seen.add(e.word); out.append(e)
        return list(reversed(out))

    def pending(self) -> List[AliasEntry]:
        """Every mask waiting for a signature — proposed, not yet ratified."""
        return [e for e in self._rows if e.status == PENDING]

    # ── persistence ──────────────────────────────────────────────────────────────────────
    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([e._asdict() for e in self._rows], indent=2))

    def load(self) -> None:
        try:
            rows = json.loads(self.path.read_text())
        except Exception:
            return
        self._rows = [AliasEntry(**{k: r.get(k) for k in AliasEntry._fields}) for r in rows]


def _alias_home() -> str:
    """Where the masks live — `GORGON_HOME` then `~/.gorgon`, the same root the archive uses."""
    base = os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon")
    return os.path.join(base, "aliases.json")


# ⇒ THE PROCESS-WIDE MASK STORE, mirroring `archive.ARCHIVE`. Loaded on first import, saved by
#   whoever writes — a store nobody can audit is the failure the archive names.
ALIASES = AliasStore(_alias_home())


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ DECLARATION — reading `define <word> as <operation>`, and filing it as a pending mask
# ═══════════════════════════════════════════════════════════════════════════════════════

import re as _re

from ..codex import ALIAS_VERBS


def aliases_from(request: str, board=None, world=None) -> List[dict]:
    """Every mask this request declares. Reported, never filed — the caller decides.

    ⇒ **READ ON THE WHOLE REQUEST, NOT CLAUSE BY CLAUSE.** Unlike `treat X as Y` (where Y is a
      category), a mask's expansion is an OPERATION PHRASE — and it usually opens on an
      imperative verb (`define relab as LIST the vms`), which the clause splitter tears off into
      its own clause. So the `define … as …` frame is matched over the full text.

    ⇒ **THE SEAM READS AND THE DOOR FILES.** The manifest is checked first: a mask may never
      shadow a verb the lab owns, and the mask WORD may not itself be a lab verb.
    """
    from .linguistics import manifest_verbs
    from planner.formula.legal import Board

    board = board or Board()
    lab = manifest_verbs(board)
    verbs = "|".join(_re.escape(v) for v in ALIAS_VERBS)
    # ⇒ an alias verb that is itself a lab verb could not open a declaration — skip the whole
    #   frame (defensive: none of ALIAS_VERBS is a manifest verb today).
    if any(v in lab for v in ALIAS_VERBS):
        return []
    out: List[dict] = []
    for m in _re.finditer(rf"\b(?:{verbs})\s+(\w+)\s+as\s+(.+?)(?=$|[.;])", request, _re.I):
        word, operation = m.group(1).strip().lower(), m.group(2).strip()
        # ⇒ the mask WORD may not itself be a lab verb — you cannot repaint `stop`.
        if word in lab or not operation:
            continue
        out.append({"word": word, "operation": operation, "said": m.group(0).strip()})
    return out


def file_all(aliases: List[dict], who: Optional[str] = None) -> List[str]:
    """Propose each as a PENDING mask and say what happened, in the operator's terms.

    ⇒ A mask permits nothing until the operator ratifies it — `propose` files PENDING, and
      only `ratify` (their signature) makes it `routes`. This is the archive's two-step, and
      the reason is the archive's: one misspoken mask must never become permanent and silent.
    """
    said: List[str] = []
    for a in aliases:
        try:
            entry = ALIASES.propose(a["word"], a["operation"], said=a.get("said", ""), who=who)
        except Exception as e:                      # a malformed proposal is not a crash
            said.append(f"could not file alias {a.get('word')!r} — {e}")
            continue
        said.append(f"filed a pending mask: {entry.word!r} → {entry.operation!r}. "
                    f"It expands nothing until you ratify it.")
    return said


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ USE — expanding a ratified mask into its operation, BEFORE the read (Option B)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ a mask fires only in VERB POSITION: the start of a clause — the request start, or right
#   after a clause delimiter (`. ; ,`) or a coordinating connective. `snapshot the contain vm`
#   must never expand `contain`; it is a name there, not a verb. Same boundaries as the split.
_CONNECTIVES = ("then", "and", "but", "otherwise", "also")
_SPLIT = _re.compile(r"([.;,]\s*|\s+(?:%s)\s+)" % "|".join(_CONNECTIVES))
_HEAD = _re.compile(r"^(\s*(?:%s)?\s*)([a-zA-Z']+)(.*)$" % "|".join(_CONNECTIVES), _re.S | _re.I)


def expand_aliases(request: str, board=None) -> Tuple[str, List[str]]:
    """Rewrite any ratified MASK that opens a clause into its expansion, before anything reads.

    ⇒ **DETERMINISTIC, AND INERT UNTIL A MASK IS RATIFIED.** With no ratified alias the request
      is returned byte-for-byte, so this perturbs no existing read (the same property
      `settle_from_archive` relies on). The rewrite is the SEAM's, never the model's, and the
      expansion re-reads through the ordinary pipeline into REAL operations — so the authority
      gate checks the operation the mask stands for, never the mask. A mask carries no authority
      a plain call to the operation would not.
    """
    request = str(request)
    if not ALIASES._rows:                              # fast path: nothing taught
        return request, []
    from .linguistics import manifest_verbs
    from planner.formula.legal import Board
    lab = manifest_verbs(board or Board())
    notices: List[str] = []

    parts = _SPLIT.split(request)                      # [segment, delim, segment, delim, ...]
    for i in range(0, len(parts), 2):
        m = _HEAD.match(parts[i])
        if not m:
            continue
        lead, verb, rest = m.group(1), m.group(2), m.group(3)
        entry = ALIASES.known(verb.lower())
        # ⇒ never expand a word the lab owns as a verb — the manifest wins (the shadow guard).
        if entry is None or verb.lower() in lab:
            continue
        parts[i] = lead + entry.operation + rest
        notices.append(f"expanded mask {verb!r} -> {entry.operation!r}")
    return "".join(parts), notices
