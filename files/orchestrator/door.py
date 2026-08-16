"""door.py — WHAT IS TRUE OF THIS REQUEST, BEFORE ANYTHING DECIDES WHERE IT GOES.

    facts("stop every vm that has over 6gb of ram")
        kinds=('vm',) acting=('stop',) universal=True filtered=True says=order

# ⇒⇒ THIS FILE COMPUTES FACTS AND RETURNS NO VERDICT, AND THAT IS THE WHOLE DESIGN

N1 asks which regime a request wants — a tool, a stored procedure, an assembled program, a
question to the operator, or none of those because the request is not about the lab at all.
**That decision is the LADDER, and it is not here.** What is here is every fact the ladder
reads, computed once, from the authorities that already own them.

⇒ **WHY SPLIT IT AT ALL.** A router that computes and decides in one pass cannot be measured:
  a wrong destination could be a wrong lookup or a wrong rule and nothing separates them. The
  same argument `plan.py` makes for printing every stage — *"a wrong answer says WHICH half was
  wrong"* — and the same one that made the two-pass seam legible.

# ⇒⇒ THE HARD CONSTRAINT: ZERO MODEL CALLS. THE DOOR RUNS BEFORE THE MODEL DOES

`pipeline.run` is the obvious source for all of this and it is the wrong one: its own docstring
says *"two model calls' worth of questions in pass 1, one in pass 2."* **The door decides
whether the program regime should run, so it cannot be the program regime's front half** — and
it runs on every request that arrives, including *"good morning"*.

⇒ So every fact below is a LOOKUP: closed classes, the manifest, the registries this system
  declares, and the world's own member names. The one rule the ladder inherits from
  [[gorgon-vague-request-ladder]] is *compute what can be computed, ask only what cannot*, and
  that rule applies to the door before it applies to anything the door routes to.

# ⇒⇒ NOTHING HERE IS A SECOND OPINION. EVERY LOOKUP NAMES ITS OWNER

    the clause split        `speech_act.clauses` -> `pass2.clauses_of`. A private splitter
                            would be the twin-owner defect; the member-list rule took a
                            recorded bug to get right and is not being rewritten
    what was said           `speech_act.read` / `verdict` — order · question · neither, from
                            closed classes and one manifest lookup, and NO model
    acting vs asking        `speech_act.changes_the_world`, which is `effects.actors` minus
                            the probes. THREE-VALUED: None means the manifest does not know
                            the verb, and that is a finding
    the kinds               `scan.kinds_named` / `scan._index` — the manifest's own noun index
    the counts              `scan.ENUMERATORS` and `scan.COMPARATORS`, declared tables
    achieve vs do           `linguistics.mood_of` — the postcondition signal
    words nobody owns       `scan.uncovered`, the same mechanism pass 1 finds `n1` and
                            `golden` with
    the stored library      `planner.procedures.LIBRARY.names()`
    the phrase book         the REPL shortcut registry, asked whether it WOULD match. Never run

⇒ ⚠ **AND ONE OF THOSE DEPENDENCIES IS KNOWN-FRAGILE AND IS BEING DEEPENED ON PURPOSE.**
  `scan._operation_words` carries hand-added English — `make`, `put`, `take`, `ping`, `spin`,
  `boot` — which is Gorgon's English rather than the manifest's, and is filed as the thing that
  would break first against a second manifest (D5, D6). It is REUSED here rather than copied,
  so the two cannot drift and one fix repairs both. The alternative was a private word list,
  which is worse in every direction.

# ⇒⇒ THE ONE VOCABULARY THIS FILE DECLARES, AND THE TEST THAT ADMITS IT

The lab's nouns come from the manifest. **Gorgon's own nouns come from nowhere** — no registry
states that `model`, `password` or `mission` name things this system owns, and the object test
the whole SELF/GOVERNANCE side rests on needs them: *a contract, a mission, a model, a password
are not manifest kinds.*

⇒ **SO THEY ARE DECLARED, AND `governing.py` ALREADY SETTLED WHAT MAKES THAT LEGITIMATE.** Its
  own note, on `treat X as Y`: *"declare that in THIS system, `treat X as Y` names an act of
  governing. That is a fact about the system, which the admission test accepts; 'treat is a
  synonym for regard' would be a fact about English, which it refuses."* Every entry below is
  a fact about this system, and each names the surface that owns it.

⇒ ⚠ **WHAT IS NOT DECLARED IS DERIVED, AND THAT ORDER MATTERS.** The shortcut registry and the
  procedure library are READ, never listed, so a new shortcut or a new procedure is visible to
  the door the day it lands. Only the nouns no registry states are written down.

# ⇒ WHAT THIS FILE DELIBERATELY CANNOT SEE, RECORDED RATHER THAN GUESSED

    A COMPARATIVE       *"over 6gb"*, *"the biggest"* — `scan.COMPARATORS` declares the COUNT
                        comparators (`at least`, `exactly`) and nothing declares the magnitude
                        ones. That is Part 2's comparative qualifier, already on the open list,
                        and inventing a word list here would be the fix that hides it
    A GOAL-MATCHED      `Store.covering()` matches a stored procedure to a goal STRUCTURALLY,
    PROCEDURE           and a goal needs pass 2, which needs the model. So the door can see a
                        procedure NAMED and not a procedure that would COVER — see `procedure`
    A SECOND TURN       every fact is computed from one string. Anaphora and ellipsis have no
                        antecedent here, exactly as Part 3 says
"""
import re
from typing import Dict, NamedTuple, Optional, Sequence, Tuple

from planner.formula.legal import Board

# ⇒⇒ GORGON'S OWN OBJECTS — the half of the object test no manifest can answer.
#
#   Each entry names the SURFACE THAT OWNS IT, because a noun with no owner is a word list and
#   a noun with an owner is a fact about this system. Read `governing.py`'s admission test
#   before adding one: *does this state a fact about Gorgon, or a fact about English?*
#
#   ⇒ ⚠ **`profile` AND `template` ARE ABSENT AND THAT IS THE POINT.** Both read like settings
#     and both are MANIFEST KINDS with their own creators, enumerators and deleters. The tier
#     list this item was briefed from put them here; the manifest says otherwise, and
#     `door_key.check()` asserts it in both directions.
GORGON_NOUNS: Dict[str, str] = {
    "session":      "the chat session",         # clear-session · auto clear · drift
    "conversation": "the chat session",
    "drift":        "the chat session",
    "model":        "the model",                # `gorgon load model` — the A2 axis
    "models":       "the model",
    "password":     "operator credentials",     # login · logout · operator
    "credentials":  "operator credentials",
    "contract":     "the contract",             # forge · sign · amend
    "contracts":    "the contract",
    "mission":      "autonomy",                 # orchestrator.ai.mission
    "missions":     "autonomy",
    "procedure":    "the library",              # planner.procedures
    "procedures":   "the library",
    "rule":         "the rule of law",          # proposals · referendum · amendment
    "rules":        "the rule of law",
    "policy":       "the rule of law",
    "word":         "the archive",              # orchestrator.seam.archive
    "words":        "the archive",
    "verbose":      "the display",
    "system":       "the host",
}

# ⇒ THE WH-WORDS THAT ASK FOR A NUMBER. Two, and English gains no more — the same closed-class
#   licence `speech_act.WH_WORDS` claims, narrowed to the pair that make a request a COUNT.
COUNTING = ("how many", "how much")

# ⇒ EXCLUSION. One word, and it is the only thing that makes rung 8 a filtered set rather than
#   a universal one. Declared here because `scan` reads it as a span boundary, not as a signal.
EXCEPTING = frozenset({"except", "excluding", "apart"})

# ⇒⇒ THE UNIVERSAL PRONOUNS, AND THEY ARE A DIFFERENT WORD CLASS FROM `scan.UNIVERSAL`.
#
#   `scan.UNIVERSAL` and `scan.ENUMERATORS` own the DETERMINERS — `every vm`, `all machines`,
#   `each one`. Nothing owns the PRONOUNS, and *"just stop everything"* is a population act
#   whose object is one of them. Measured against the key: with these absent it was
#   indistinguishable from `stop alpha`, one call against every machine in the lab.
#
#   ⇒ **THE LICENCE IS THE ONE `speech_act.WH_WORDS` CLAIMS — a CLOSED class.** English has
#     these and gains no more, exactly as it has nine wh-words. They are declared HERE and not
#     added to `scan.UNIVERSAL` because a determiner table that answers to a pronoun would
#     change what pass 1 scans, and the seam is not this item's to move.
UNIVERSAL_PRONOUNS = frozenset({"everything", "everyone", "everybody",
                                "anything", "anyone", "anybody"})


class Facts(NamedTuple):
    """Everything true of one request that a lookup can establish. NO VERDICT LIVES HERE.

    ⇒ A field is `None` or empty when nothing settled it, never when something was guessed.
      `acting` holding a verb the manifest does not know would be an inference; it holds only
      verbs `changes_the_world` returned True for, and `unsettled_verbs` holds the rest.
    """
    request: str
    # ── what was said ────────────────────────────────────────────────────────────────
    clauses: Tuple[str, ...]
    acts: Tuple[Optional[str], ...]     # the speech act of each clause, in spoken order
    says: str                           # order · question · neither
    mood: str                           # do · achieve
    # ── the lab ──────────────────────────────────────────────────────────────────────
    kinds: Tuple[str, ...]              # manifest kinds the request names
    members: Tuple[str, ...]            # things the WORLD holds, named by name
    acting: Tuple[str, ...]             # verbs naming an operation that CHANGES the world
    asking: Tuple[str, ...]             # verbs naming an operation that only READS
    # ── the shape ────────────────────────────────────────────────────────────────────
    universal: bool                     # every · all · each · any · both
    numeral: Optional[int]              # the largest declared count, or None
    comparator: str                     # max · min · eq, from scan.COMPARATORS
    counted: bool                       # `how many` · `how much`
    filtered: bool                      # a relative clause, or an exclusion
    ordered: bool                       # more than one clause
    postcondition: bool                 # mood is achieve
    # ── gorgon's own surfaces ────────────────────────────────────────────────────────
    addressed: bool                     # the request calls the agent by its own name
    governs: Tuple[str, ...]            # clauses that LEGISLATE rather than instruct
    shortcut: str                       # the shortcut that WOULD take this, or ""
    gorgon: Tuple[str, ...]             # Gorgon's own objects the request names
    procedure: str                      # a stored procedure named outright, or ""
    # ── what nobody owns ─────────────────────────────────────────────────────────────
    unknown: Tuple[str, ...]            # content words no vocabulary accounts for

    @property
    def lab(self) -> bool:
        """Does the request name anything the lab holds? A fact, and not a destination."""
        return bool(self.kinds or self.acting or self.asking)


def facts(request: str, board: Optional[Board] = None, world=None) -> Facts:
    """Every fact the ladder reads, computed once. No model call, no verdict, no dispatch.

    `world` is optional and degrades exactly as the seam's does: without a lab, member names
    like `alpha` and `db` cannot be recognised, so they land in `unknown` — which is honest,
    and is what `plan --seam` already prints as *"no lab — every bare name stays kindless"*.
    """
    from .seam import scan, speech_act
    from .seam.linguistics import mood_of

    board = board or Board()
    low = request.lower()
    words = _words(low)

    parts = tuple(speech_act.clauses(request))
    acts = tuple(a for _, a in speech_act.read(request, board, world))

    acting, asking = _verbs(words, board, speech_act)
    numeral, universal = _counts(words)

    return Facts(
        request=request,
        clauses=parts,
        acts=acts,
        says=speech_act.verdict(request, board, world),
        mood=mood_of(request),
        kinds=tuple(scan.kinds_named(request, board)),
        members=_members(words, world),
        acting=acting,
        asking=asking,
        universal=universal,
        numeral=numeral,
        comparator=_comparator(low, scan),
        counted=any(c in low for c in COUNTING),
        filtered=_filtered(parts, speech_act),
        ordered=len(parts) > 1,
        postcondition=mood_of(request) == "achieve",
        addressed=_agent_name() in words if _agent_name() else False,
        governs=_governs(request, board, world),
        shortcut=_shortcut(low),
        gorgon=tuple(w for w in dict.fromkeys(words) if w in GORGON_NOUNS),
        procedure=_procedure(low),
        unknown=_unknown(request, board, world, scan),
    )


# ── the lookups, one owner each ──────────────────────────────────────────────────────


def _words(low: str) -> Tuple[str, ...]:
    """The request's word tokens. A NAME KEEPS ITS DIGITS; A NUMBER STANDS ALONE.

    ⇒⇒ ⚠ **THIS FILE SHIPPED THE 2026-08-16 TOKENIZER BUG BACK, IN THE ONE PLACE THAT BITES.**
      `[a-z']+|[0-9]+` splits `n3` into `n` and `3` — recorded that day as *"harmless for the
      mood; fatal the moment something COUNTED them"* — and `_counts` is something that counts.
      Measured against the key: *"delete the vm called n3"* came back `numeral=3` and became
      indistinguishable from *"clone golden into three new machines"*, one call against three.
      **The warning was quoted in this docstring while the regex under it was the bug.**

    ⇒ So a token that OPENS on a letter absorbs its digits (`n3`, `vm1`, `6gb` -> `6` + `gb`,
      which is the comparative Part 2 owns), and only a standalone run of digits is a number.
    """
    return tuple(re.findall(r"[a-z][a-z0-9_']*|[0-9]+", low))


def _verbs(words: Sequence[str], board: Board,
           speech_act) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """The request's words that name a manifest operation, split by what that operation DOES.

    ⇒ **`changes_the_world` IS THE OWNER AND IT IS THREE-VALUED**: True acts, False reports,
      None means the manifest does not know the word. Only the first two are collected.

    ⇒ ⚠ **AND THE THIRD VALUE IS DELIBERATELY NOT A FIELD.** `None` comes back for `the` and
      for `vms` exactly as it does for a verb the lab has never heard of, because nothing here
      knows a verb from a noun — no tagger, no lexicon. A `unsettled_verbs` field was written
      and REMOVED rather than shipped holding every function word in the sentence: a fact that
      cannot be computed honestly is worse as an empty field than as an absent one
      ([[gorgon-built-and-never-called]]).
    """
    from .seam.scan import _index
    nouns = set(_index(board))
    acting, asking = [], []
    for w in dict.fromkeys(words):
        # ⇒⇒ **THE MANIFEST'S NOUNS ARE SUBTRACTED, AND MEASURING IT IS HOW IT WAS FOUND.**
        #   `vm_status` is an asking operation whose HEAD WORD is `vm`, so the noun `vm` came
        #   back as a verb that reads — and *"a jumpbox is a vm"*, a piece of teaching, was
        #   reported as naming a lab read. `_lab_predicate_in` makes the identical subtraction
        #   for the identical reason, and the manifest's own index is what answers it.
        if w in nouns:
            continue
        verdict = speech_act.changes_the_world(w, board)
        if verdict is True:
            acting.append(w)
        elif verdict is False:
            asking.append(w)
    return tuple(acting), tuple(asking)


def _counts(words: Sequence[str]) -> Tuple[Optional[int], bool]:
    """The largest declared count, and whether the request quantifies over the whole population.

    `scan.ENUMERATORS` is the declared table and it holds BOTH — the numerals map to ints and
    `every`/`all`/`each`/`any` map to the string `all`, which is exactly the distinction the
    ladder needs between *five machines* and *every machine*.
    """
    from .seam.scan import ENUMERATORS
    numbers, universal = [], False
    for w in words:
        got = ENUMERATORS.get(w)
        if got == "all" or w in UNIVERSAL_PRONOUNS:
            universal = True
        elif isinstance(got, int):
            numbers.append(got)
        elif w.isdigit():
            numbers.append(int(w))
    return (max(numbers) if numbers else None), universal


def _comparator(low: str, scan) -> str:
    """`max`, `min`, `eq` — the COUNT comparators the manifest's own scanner declares.

    ⚠ NOT the magnitude ones. *"over 6gb"* is Part 2's comparative qualifier and nothing
      declares it; a word list here would hide an item that is already written down.
    """
    for phrase, meaning in scan.COMPARATORS.items():
        if phrase in low:
            return meaning
    return ""


def _filtered(parts: Sequence[str], speech_act) -> bool:
    """Does any clause NARROW a set rather than name it whole?

    Two signals, both closed-class and both already declared: a RELATIVIZER with a predicate
    behind it (*"every vm THAT is stopped"*), and an exclusion (*"every vm EXCEPT db"* — rung
    8's whole shape). A relativizer at the head of a clause is a fragment, not a filter.
    """
    for clause in parts:
        words = _words(clause.lower())
        if any(w in EXCEPTING for w in words):
            return True
        for i, w in enumerate(words):
            if i and w in speech_act.RELATIVIZERS and i + 1 < len(words):
                return True
    return False


def _members(words: Sequence[str], world) -> Tuple[str, ...]:
    """The things the LAB ACTUALLY HOLDS that this request names by name.

    ⇒⇒ **FOUND BY A CONTROL RUN, AND IT IS THE FACT THAT WAS MISSING RATHER THAN A RULE.**
      Supplying a world dissolved one collision and opened another: *"is alpha running?"* and
      *"who are you"* came back with identical facts — both questions, neither naming a kind,
      neither naming an operation, and NEITHER holding an unknown word, because a world makes
      `alpha` known and `you` was always closed-class. **The door knew `alpha` was accounted
      for and not WHAT accounted for it.**

    ⇒ A member is the strongest lab evidence a bare word can carry — stronger than a kind,
      because the lab is the authority that a thing exists at all
      ([[gorgon-declare-dont-infer]]). Without a world this is empty and says nothing, which
      is the same degradation `plan --seam` already prints.
    """
    if world is None:
        return ()
    try:
        held = {str(n).lower() for n in (world.names() or ())}
    except Exception:
        return ()
    return tuple(w for w in dict.fromkeys(words) if w in held)


def _agent_name() -> str:
    """The agent's own name — `pass1.agent_name`, which resolves it from the selection.

    ⇒⇒ **A REQUEST THAT CALLS THE AGENT BY NAME IS TALKING TO SOMEBODY, NOT ABOUT THE LAB**,
      and the seam already built this rule at the operator's ask on 2026-08-14: *"gate 2 is a
      world check, and we have nothing to check for the agent's name."* Before it,
      *"good morning doorman"* was declared as a row, typed `vm` by the affordance rule, and
      gate 2 asked whether to create a machine called doorman.

    ⇒ Measured against the key: without this fact a greeting is indistinguishable from
      *"sort out n1"* — both are a handful of words nothing owns. It is the same lookup, asked
      one stage earlier.
    """
    from .seam.pass1 import agent_name
    try:
        return agent_name()
    except Exception:
        return ""


def _governs(request: str, board: Board, world) -> Tuple[str, ...]:
    """The clauses that LEGISLATE rather than instruct, read by the store that owns them.

    ⇒⇒ **AND `speech_act` ALONE IS NOT ENOUGH, WHICH IS WHY THIS ASKS `governing`.** A deontic
      rule — *"never delete a vm without asking me"* — comes back DECLARATION from the speech
      act and needs nothing more. *"treat prod as read-only"* comes back EXPRESSIVE, because it
      carries no closed-class marker at all: no modal, no frequency adverb, no universal.
      `governing.CONTRACT_VERBS` is the declaration that in THIS system `treat X as Y` names an
      act of governing, and it lives there on purpose so the reader stays free of one store's
      vocabulary. The door asks the owner rather than learning the frame twice.
    """
    try:
        from .seam.governing import rules_from
        return tuple(str(r.get("text", "")) for r in rules_from(request, board, world))
    except Exception:
        return ()


def _shortcut(low: str) -> str:
    """The REPL shortcut that WOULD take this input, asked and never run.

    ⇒⇒ **THE CHEAPEST AND MOST CERTAIN FACT AVAILABLE, AND ALSO THE NARROWEST.** A match means
      Gorgon already answers to this EXACT phrase — `list all vms` is one of nine spellings in
      `shortcut_commands`, and `list all the vms` is not, which is the whole reason the door
      has to compute anything at all.
    ⇒ **A MATCH IS NOT A DESTINATION.** `ListShortcut` runs `list_vms`, which is a LAB READ, so
      a shortcut hit says *a surface exists*, never *this is not the lab*. The ladder decides.
    ⇒ IMPORTED LAZILY AND FORGIVINGLY: the registry drags in the whole REPL, and the door must
      stay importable from a bench that has no terminal.
    """
    try:
        from .ai.chat.shortcuts import _REGISTRY
    except Exception:
        return ""
    for cmd in _REGISTRY:
        try:
            if cmd.matches(low):
                return type(cmd).__name__
        except Exception:
            continue
    return ""


def _procedure(low: str) -> str:
    """A stored procedure the request NAMES. Not one that would cover it.

    ⇒ ⚠ **RUNG 2 OF THE LADDER SPLITS IN TWO, AND ONLY ONE HALF IS A DOOR FACT.** *Does a
      verified artifact already cover this?* is answered structurally by `Store.covering()`,
      which takes a GOAL — and a goal costs pass 2, which costs the model. So the covering
      half already exists one layer down, on the writer's own hot path, and cannot move up
      here. What the door can see is the operator naming the procedure, spelled as stored or
      with underscores relaxed.
    """
    try:
        from planner.procedures import LIBRARY
        stored = LIBRARY.names()
    except Exception:
        return ""
    for name in stored:
        if name.lower() in low or name.lower().replace("_", " ") in low:
            return name
    return ""


def _unknown(request: str, board: Board, world, scan) -> Tuple[str, ...]:
    """Content words no vocabulary accounts for — the ladder's own vagueness measure.

    ⇒⇒ **THE LADDER SHOULD BE ENTERED BY A COUNT, NEVER BY A VIBE** — [[gorgon-vague-request-
      ladder]]'s own correction of itself. `scan.uncovered` is the mechanism pass 1 finds `n1`,
      `golden` and `db` with, and with no spans claimed it returns every content word the
      grammar, the manifest and the operation words leave over.

    ⇒ **THEN THE WORLD, THE ARCHIVE AND GORGON'S OWN NOUNS ARE SUBTRACTED**, because a word one
      of those accounts for is not unknown — it is merely not a kind. `alpha` is a machine the
      lab holds; `jumpbox` may be a word somebody taught; `contract` is a thing this system
      owns. What survives is `grubnash` and `security issues`, which is the distinction the
      ladder draws between VAGUE and JUNK.
    """
    left = [w for w in scan.uncovered(request, [], board) if not w.isdigit()]
    if not left:
        return ()
    known = set(GORGON_NOUNS) | _declared(board) | {_agent_name()} - {""}
    if world is not None:
        try:
            known |= {str(n).lower() for n in (world.names() or ())}
        except Exception:
            pass
    return tuple(w for w in left if w not in known and not _taught(w))


def _declared(board: Board) -> set:
    """Every word some declared vocabulary already accounts for. ASSEMBLED, NEVER LISTED.

    ⇒⇒ **WITHOUT THIS, `unknown` FIRES ON EVERYTHING AND THE ASK RUNG IS USELESS.** Measured
      on the first run of this module: *"how many vms are running"* came back
      `unknown=('how', 'many', 'running')` — a wh-word, a quantifier and a DECLARED STATE
      VALUE, none of which is a word nobody owns. The vagueness count would have said that a
      perfectly ordinary question names three things the lab has never heard of.

    ⇒ **EVERY MEMBER IS READ FROM ITS OWNER**, so a class that gains a word gains it here:

          the closed classes   `speech_act`'s fifteen frozensets — the wh-words, the
                               auxiliaries, the participants, the relativizers, the deontics
          the scanner's tables `scan`'s determiners, enumerators, comparators, linking words
                               and naming cues
          the manifest         each kind's ATTRIBUTES, its aliases, and its declared VALUES.
                               `running` and `stopped` are lab vocabulary the same way `vm`
                               is, and `config.values_for` is what states them

    ⚠ `many` and `much` are the only words added by hand, and they are `COUNTING`'s own — the
      pair that turns a wh-word into a request for a number, declared at the top of this file.
    """
    from .seam import scan as SC, speech_act as SA
    from planner.ir import config as _config

    out = set(SA.WH_WORDS | SA.AUXILIARIES | SA.COPULA | SA.ADDRESSEE | SA.FIRST_PERSON
              | SA.PARTICIPANTS | SA.HORTATIVE | SA.EXISTENTIAL | SA.WHETHER | SA.RECIPIENT
              | SA.DEONTIC | SA.FREQUENCY | SA.OPENERS | SA.ANAPHORA | SA.RELATIVIZERS)
    out |= set(SC.ENUMERATORS) | SC.INDEFINITE | SC.DEFINITE | SC.UNIVERSAL | SC.NOVEL
    out |= set(SC.LINKING) | set(SC.NAMING_CUES)
    out |= {w for phrase in SC.COMPARATORS for w in phrase.split()}
    out |= {w for phrase in COUNTING for w in phrase.split()}
    out |= EXCEPTING | UNIVERSAL_PRONOUNS

    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        out |= {str(a).lower() for a in (spec.get("attrs") or ())}
        out |= {str(a).lower() for a in (spec.get("aliases") or {})}
        for attr in (spec.get("attrs") or ()):
            out |= {str(v).lower() for v in (_config.values_for(kind, attr) or ())}
        for attr, table in (spec.get("value_aliases") or {}).items():
            out |= {str(v).lower() for v in table}
    return {w for w in out if w}


def _taught(word: str) -> bool:
    """Has the archive been taught this word AND has somebody signed it?

    ⇒ ⚠ **`ARCHIVE.known` AND NOT `ARCHIVE.rows`, WHICH IS THE WHOLE SAFETY PROPERTY.** A
      PROPOSED entry describes and never permits — `known()` returns ratified-and-told only.
      Counting a pending proposal here would let an unsigned sentence quietly make a request
      look less vague than it is, which is [[gorgon-courtesy-escalates-intent]] wearing a
      lexicon: a word grants nothing until a person signs it.
    """
    try:
        from .seam.archive import ARCHIVE
        return ARCHIVE.known(word) is not None
    except Exception:
        return False
