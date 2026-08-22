"""codex.py — THE LANGUAGE CODEX: every closed class the English scaffold reads with.

One place for the words (operator, 2026-08-22: *"move all the seam hardcoded to one big
language codex config"*). A seam module imports its classes from here and holds no English of
its own; `tests/test_language_layer.py` enforces that. Sectioned by the READER that consumes
each class, in the order the reader defines them, with each class's original design note moved
with it — the WHY travels with the words.

⇒ WHAT IS NOT HERE, on purpose: check names (`OWNS` / `TAKES` — the gates' vocabulary),
  speech-act kind names, manifest segments derived from the board, and in-module fixtures
  (`EXPECTED`, `CASES`, `WANT`). Those are the model's words, not the language's.
⇒ NEAR-DUPLICATES ARE KEPT DISTINCT. Five names were shared across modules and only ONE pair
  was identical (RELATIVIZERS — deduped). The others differ by a word or a type and are named
  apart here so the difference is visible: NEGATORS (3) vs NEGATOR_TOKENS (+"n't");
  BOUNDARY_WORDS (set, bare) vs BOUNDARY_SEPARATORS (tuple, space-padded); ALWAYS_NEVER vs
  FREQUENCY_ADVERBS; COPULA vs TESTIMONY_COPULAS; PRONOUNS vs REFERRING_PRONOUNS; SHAPE_NEGATION
  vs CUT_NEGATION (+"no"). Merging any of them is a READING change — the operator's call.
⇒ THIS IS A PYTHON MODULE, NOT JSON, because order and type are behaviour: longest-match-first
  tuples, membership-only frozensets, a contraction map keyed by spelling. Proven byte-identical
  on the v3 eval at the consolidation (results/, 2026-08-22, seed 1).
⇒ A SECOND LANGUAGE writes its own codex with these section names — and declares the classes it
  does not have. See orchestrator/languages/README.md.
"""
from typing import Dict, Tuple



# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ THE ARCHIVE — verbs that withdraw an ENTRY (scoped to the store, never the lab)
# ═   (consumer: archive.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒⇒ **THE ARCHIVE'S OWN OPERATIONS, DECLARED THE WAY THE MANIFEST DECLARES A KIND'S — and
#   the operator drew this line: *"forgetting is specific for `words`, forget plus its
#   synonyms."***
#
#   I had removed `forget` as an English list and that was the wrong correction. The test this
#   project uses is *is it a fact about ENGLISH, or a fact about THE WORLD* — and **which verb
#   names an operation of MY store is the second kind.** `vm.nouns` says this lab calls a
#   machine a `box`; nothing about English says so, and nobody would expect the model to know
#   it. This is that declaration for a store the manifest does not cover.
#
#   ⇒ **WHAT MADE THE FIRST VERSION WRONG WAS PLACEMENT, NOT EXISTENCE.** It sat inline in
#     `effect_of` as a bare set, next to `delete`/`remove` which the MANIFEST already owns —
#     so it was both a second source for a derivable fact and an undeclared vocabulary for a
#     non-derivable one. Split: the manifest's deleters are READ, and the archive's own verbs
#     are DECLARED here, once, where the operation is defined.
#
#   ⇒ ⚠ **AND IT IS SCOPED TO THIS STORE.** These verbs mean *withdraw an ENTRY*; they say
#     nothing about the lab, where removal is `delete_vm` and friends. A word here can never
#     authorise anything — `effect_of` only ever reaches `retract`, which un-signs a fact.
#   ⇒ ⚠ **`erase` WAS HERE AND THE OPERATOR TOOK IT OUT: *"erase is a deleting verb not a
#     forgetting one."*** Right, and the distinction is the whole design — these three name an
#     operation on THIS STORE and nothing else. A verb that means *destroy a thing in the lab*
#     borrowed for *withdraw a word* would make the two removals indistinguishable, which is
#     exactly the confusion `AMBIGUOUS_REMOVAL` below exists to refuse to guess at.
FORGET_VERBS: Tuple[str, ...] = ("forget", "unlearn", "discard")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ GATE 4 — the words a legality check reads
# ═   (consumer: gate4.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ THE COMPLETE SET OF ENGLISH RECIPROCAL PRONOUNS. Two of them, and there is no third —
#   closed the way `INDEFINITE`/`DEFINITE` are closed, which is what separates this from a
#   curated content-word list like `ACHIEVE_MARKERS`.
RECIPROCAL = ("each other", "one another")

DESTRUCTIVE_WORDS = ("delete", "remove", "destroy", "tear down", "get rid",
                     "wipe", "drop", "kill off", "clear out")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ GOVERNING — the contract verbs that declare a rule
# ═   (consumer: governing.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒⇒ **THIS STORE'S OWN VERBS, DECLARED AT THE OPERATION — the same move the archive makes for
#   `forget`, and the operator's call both times.**
#
#   *"treat prod as read-only"* carries no closed-class marker at all: no deontic modal, no
#   frequency adverb, no universal. It is legislation and nothing in its grammar says so. The
#   only honest way to read it is the way `vm.nouns` works — **declare that in THIS system,
#   `treat X as Y` names an act of governing.** That is a fact about the system, which the
#   admission test accepts; *"treat is a synonym for regard"* would be a fact about English,
#   which it refuses.
#
#   ⇒ **THE `as` COMPLEMENT IS REQUIRED, AND IT IS WHAT KEEPS THIS TIGHT.** `treat X AS Y`
#     assigns a category; *"treat it carefully"* assigns nothing and is not a rule. Without
#     that test the verb alone would claim any sentence it opened.
#
#   ⇒ ⚠ **AND IT CANNOT COLLIDE WITH A LAB ORDER**, which is the risk a verb list always
#     carries. `mark alpha as a template` is the same *X as Y* shape and is an ORDER — because
#     `mark` IS a manifest verb (`mark_as_template`) and these three are not. The manifest is
#     checked first, so a declared verb can never shadow one the lab owns.
CONTRACT_VERBS: Tuple[str, ...] = ("treat", "regard", "consider")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ ISO — stance markers: hedges, emphasis, backchannel, trouble, apology, filled pauses
# ═   (consumer: iso.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ THE EPISTEMIC ADVERBS. A closed class, and the same licence `FREQUENCY` claims for
#   `never`/`always`: English has these and gains none.
#   ⇒ ⚠ THE MODALS ARE DELIBERATELY ABSENT. `may` and `might` are epistemic AND deontic, and
#     `DEONTIC` already spends them on permission — a word claimed twice is how a reading
#     starts disagreeing with itself.
HEDGES = frozenset({"maybe", "perhaps", "probably", "possibly", "presumably", "apparently",
                    "likely", "seemingly"})

EMPHATIC = frozenset({"definitely", "certainly", "surely", "obviously", "clearly",
                      "undoubtedly", "absolutely"})

# ⇒⇒ **FEEDBACK — TWO WHOLE DIMENSIONS WE EMITTED NOTHING FOR, AND THEY ARE A QUARTER OF REAL
#   DIALOGUE.** Measured against DialogBank's gold Map Task annotations, 2026-08-16: 165
#   autoFeedback and 50 alloFeedback segments out of 779, and we answered GREETING to every one.
#
#   ⇒ **THE STRUCTURAL KEY IS POSITION, AND IT REUSES A CLASS ALREADY DECLARED.** A discourse
#     particle that IS the whole utterance is feedback; the same particle in front of a clause
#     is an opener. `speech_act.OPENERS` already holds `ok`, `okay`, `yeah`, `well` and calls
#     them *"leading particles that carry no proposition"* — standing alone they carry one
#     proposition exactly: **I am still with you.**
#
#   ⇒ **AND THE GOLD SAYS THE CLASS IS SMALL.** Seven forms cover ~150 of the 165: `right` (75),
#     `okay` (33), `mmhmm` (13), `uh-huh` (13), `right okay` (10), `yeah`, `oh`. A closed class
#     in the strong sense — English adds a backchannel about once a generation.
BACKCHANNEL = frozenset({"right", "mmhmm", "mmhm", "mhm", "mm", "uh-huh", "uhhuh", "uhuh",
                         "aye", "sure", "gotcha", "indeed", "quite", "i see", "got it"})

# ⇒ AND THE NEGATIVE HALF — *I did NOT follow that.* Far rarer in the gold (7 of 165) and the
#   one that matters most, because it is the operator saying the reading went wrong.
TROUBLE = frozenset({"sorry", "pardon", "what", "huh", "again", "eh"})

# ⇒⇒ ⚠ **AND A BARE `sorry` IS AN APOLOGY, NOT A REQUEST TO REPEAT** — measured, and it cost
#   every Social Obligations segment in the corpus. All four gold SOM segments in the Map Task
#   set are the single word `sorry`, and sweeping it into TROUBLE took us from 4 of 4 to 0.
#   ⇒ **THE MARK SPLITS IT, WHICH IS THE RULE ALREADY USED ONE CLASS UP.** `right` reports and
#     `right?` asks; `sorry` apologises and `sorry?` asks. I built that discrimination for the
#     backchannels and failed to apply it to the word beside them.
APOLOGY = frozenset({"sorry", "apologies", "oops", "my bad"})

# ⇒⇒ **THE FILLED PAUSES — HESITATION, AND IT IS NOT A BACKCHANNEL.** `er` · `um` · `uh` ·
#   `ehm` are 27 of the 29 Time Management segments in the gold, all of them `stalling`: the
#   speaker holding the floor while they think. A closed class, and one English has had
#   unchanged for as long as anybody has written it down.
#   ⇒ ⚠ **AND THEY ARE THE SAME TOKENS THE GOLD ALSO MARKS `turnKeep`**, because a filled pause
#     does two jobs at once — that is ISO's multidimensionality, not an ambiguity. We emit the
#     TIME reading only: it is the one we can establish from the word alone. Claiming the turn
#     reading too would score better and mean less, because we cannot see whose turn it was.
FILLED_PAUSE = frozenset({"er", "erm", "ehm", "um", "uhm", "uh", "eh", "hmm", "hm"})

# the whether-`if` guard: `tell me IF the db vm restarted` asks, it does not condition.
# The word BEFORE the `if` separates them, and the askers are a small closed set.
WHETHER_HOSTS = frozenset({"me", "us", "know", "check", "see", "ask", "wonder", "whether"})

# focus adverbs that may sit in FRONT of a subordinator without unseating it: `ONLY if`
FOCUS_PARTICLES = frozenset({"only", "even", "just"})


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ LINGUISTICS — light verbs and ACHIEVE markers (the courtesy hazard lives here)
# ═   (consumer: linguistics.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ A CLOSED CLASS OF ENGLISH, the same status `COMPARATORS` and `ENUMERATORS` hold. A light
#   verb contributes almost no meaning, so the NOUN beside it carries the predicate.
#
#   ⇒ **AND IT IS A POSITIVE ASSERTION ONLY — ABSENCE FROM THE MANIFEST DOES NOT MEAN LIGHT.**
#     The tempting move is to delete this list and derive it: a contentful verb is one the
#     manifest declares, so anything else is light. That is wrong in the exact place it matters.
#     *"find me a snapshot"* — `find` is not a declared operation, so absence would call it
#     light and read the snapshot as an ACTION, when it is plainly an object being selected.
#     Absence means *"either light, or an operation this lab does not have"*, and those two
#     need opposite treatment.
LIGHT_VERBS = frozenset({"take", "takes", "give", "gives", "make", "makes", "do", "does",
                         "get", "gets", "have", "has", "carry", "carries",
                         "perform", "performs", "conduct", "conducts"})

# ⇒ THE MOOD MARKERS. A request in the ACHIEVE mood states a state that must HOLD; pass 2 only
#   knows how to DO. Every rung filed as a "reasoning error" — 7, 9, 14 — is one of these.
ACHIEVE_MARKERS = ("make sure", "makes sure", "ensure", "ensures", "there should be",
                   "should be", "must be", "make certain", "verify that", "confirm that")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ PASS 1 — distinctness, exclusion, plural pronouns
# ═   (consumer: pass1.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ THE DISTINCTNESS MARKERS — a CLOSED class of English, the same standing as `COMPARATORS`
#   and `ENUMERATORS`. Each one says *not the one just mentioned*, which is the only thing
#   that separates a second object from a second mention of the first.
DISTINCT = ("different", "another", "separate", "second", "other", "own", "its own",
            "their own", "a new", "fresh")

EXCLUDERS = ("except", "excluding", "besides", "apart from", "other than", "but not")

PLURAL_PRONOUNS = {"ones", "them", "they", "those", "these", "all", "both", "rest", "others"}


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ PASS 2 — clause words and the cut sets
# ═   (consumer: pass2.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

CLAUSE_WORDS = (" and then ", " then ", " and ", " but ")

CUT_DETERMINERS = frozenset({"a", "an", "the", "every", "each", "all", "any", "both", "no",
                       "it", "them", "me", "us"})

CUT_NEGATION = frozenset({"don't", "not", "never", "do", "no"})


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ READING ANSWERS — yes / no / like
# ═   (consumer: reading_answers.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ CLOSED FUNCTION-WORD CLASSES, and that is why they may be written down at all. Negation and
#   comparison are grammar: finite, stable, and the same for every speaker. A list of NOUNS that
#   might mean `vm` would be the other kind of list, the kind that rots.
NEGATION = {"not", "isn't", "isnt", "no", "nope", "nah", "never", "neither",
            "nor", "n't", "don't", "dont"}

SIMILE = {"like", "similar", "resembles", "sort", "kind"}   # "like a vm", "sort of like a vm"

# ⇒ AFFIRMATION IS A CLOSED CLASS TOO, and that is the whole licence for writing it down. These
#   are the particles English uses to agree; a list of VERBS meaning "go ahead" would be the
#   other kind of list, and would rot.
AFFIRMATION = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "aye", "please", "do", "y"}


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ RESIDUE — relational words the sanitiser must not drop
# ═   (consumer: residue.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ A CLOSED CLASS OF ENGLISH, AND IT IS THE WEAKEST THING IN THIS FILE — SAID OUT LOUD.
#   `except`, `instead`, `together` carry a set operation, so they are neither descriptors nor
#   junk; they belong to pass 2, and rung 8's `except` is already a known-open gate 3 question.
#   This is the same KIND of list as `COMPARATORS` and `ENUMERATORS` — closed English, not lab
#   vocabulary — but unlike those two it has no manifest behind it. When pass 2 declares its
#   set operations, THIS LIST IS DELETED AND READ FROM THERE (rule W5).
RELATIONAL_WORDS = frozenset({
    "except", "excluding", "besides", "instead", "rather",
    "together", "apart", "separately", "own", "different", "same",
})


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ SCAN — the grammar of the object phrase: openers, determiners, comparators, enumerators, magnitude, naming
# ═   (consumer: scan.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ THE COMPARATOR IS PART OF THE ENUMERATOR REGION, and it is the `(eq, 3)` the program needs.
#   Longest first, so "no more than" wins over "no".
COMPARATORS: Dict[str, str] = {
    "no more than": "max", "at most": "max", "not more than": "max", "up to": "max",
    "no fewer than": "min", "at least": "min",
    "exactly": "eq", "precisely": "eq", "just": "eq",
}

ENUMERATORS: Dict[str, object] = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "both": 2, "no": 0,
    "every": "all", "all": "all", "each": "all", "any": "all",
}

# a clause ends here, and a span may never cross one
# `of` ENDS A PHRASE AND OPENS ANOTHER. "a snapshot OF every running vm" is two things, and
# without this the snapshot's span swallowed the machines, which then folded away as a
# collision — rung 12 declared one object where the request names two.
# ⇒ `except` joined 2026-08-18: *"stop every vm EXCEPT the db vm"* fused into ONE row with
#   no comma to cut it — the certified set's neg-0001, whose gold is two spans (patient +
#   excluded). Rung 8's carve-out had always arrived comma-separated, so the boundary was
#   never missed until a bare `except` appeared.
BOUNDARY_WORDS = {",", ";", ".", "and", "then", "but", "except", "—", "–", "of"}

# the phrasal PARTICLES a verb strands on its edge — closed class, ONE copy (the span
# walk and the imperative shape both read it)
PARTICLES = frozenset({"up", "down", "off", "out", "over", "away", "back", "sure"})

# every word that can OPEN an object NP — the determiner set plus its own grammar
# family: quantifiers, universals, pro-forms. Closed classes, not vocabulary. The
# certified terse cell died on the family members: `most of vms` · `everything` · `ones`
OBJECT_OPENERS = frozenset({
    "a", "an", "the", "every", "each", "all", "any", "both", "no",
    "it", "them", "me", "us",
    "most", "some", "several", "few", "many", "half", "everything", "one", "ones"})

SHAPE_NEGATION = frozenset({"don't", "do", "not", "never"})

GRAMMAR = {"a", "an", "the", "of", "on", "in", "to", "for", "and", "then", "but", "with",
           "that", "which", "is", "are", "be", "it", "its", "them", "they", "their", "there",
           "should", "must", "can", "each", "other", "into", "from", "at", "by", "so", "do",
           "does", "not", "was", "were", "this", "those", "these", "up", "out", "all", "own",
           "same", "different", "already", "currently", "still", "also", "sure", "left"}

# the noun and function-word segments an operation NAME sheds before any of its segments
# may count as a verb — shared with pass 2's licence map, one copy (D5's root)
NON_VERB_SEGMENTS = frozenset({
    "network", "snapshot", "template", "profile", "file", "vm",
    "networks", "snapshots", "templates", "profiles", "files", "vms",
    "to", "of", "as", "on", "in", "from", "with", "at", "by", "for", "the"})

# ── THE DETERMINER DECIDES EXISTENCE, WHERE IT DECIDES AT ALL ─────────────────────────
#
# ⇒⇒ WHY THIS IS NOT THE WORD LIST THE OPERATOR RULED OUT. The 2026-08-11 critique:
#   *"SSOT of nouns and verbs worked in the tool regime because each tool only has finite slots
#   and words related to it, while in the program regime one noun is still legal due to how the
#   sentence is structured."* Right — and it applies to CONTENT words, which are open class and
#   cannot be enumerated. **DETERMINERS ARE A CLOSED FUNCTION-WORD CLASS**: about thirty words,
#   fixed for centuries, and independent of the manifest. A new kind or an unlisted verb does
#   not change them, which is exactly what `ACHIEVE_MARKERS` cannot say for itself.
#
# ⇒ WHAT IT FIXES: rung 6's verdict was a COIN. `existence` is asked of the model at 85% with
#   every error toward NEW, and two complementary checks — `unverifiable` (gate 2, EXISTING) and
#   `uncreated-declaration` (gate 1, NEW) — fire on opposite faces of it. Measured n=3: BOUNCE,
#   BOUNCE, ASK on BYTE-IDENTICAL operations. The coin decided only WHO GOT TOLD.
#
# ⇒ *"put the blue ones on A DIFFERENT network"* — an indefinite with no prior referent IS a new
#   one. Nothing needs asking.
INDEFINITE = {"a", "an", "another", "some"}

DEFINITE = {"the", "this", "that", "these", "those", "its", "their", "his", "her", "our", "your"}

UNIVERSAL = {"every", "all", "each", "any", "both"}

# ⇒⇒ **AND THE QUANTIFIER BETWEEN ONE AND ALL, WHICH NOTHING HAS EVER READ.** ISO 24617-2
#   carries PARTIALITY as one of its four qualifiers on a dialogue act, and we had UNIVERSAL
#   and the cardinals with a hole between them: *"stop MOST of the vms"* read as *stop the
#   vms*, which is every machine instead of a majority nobody has identified.
#   ⇒ **IT SITS HERE BECAUSE `scan` OWNS DETERMINERS**, beside the class it is the complement
#     of — a second quantifier table somewhere else is how the two would drift.
#   ⇒ ⚠ AND IT NAMES AN AMOUNT NOBODY CAN COMPUTE. Unlike `every` or `3`, a partial quantifier
#     does not say WHICH members, so the honest reading is a QUALIFIER on the act and a
#     question to the operator — never a set the writer picks.
PARTIAL = {"most", "some", "several", "few", "half", "many", "part", "majority", "couple"}

# CONTRASTIVE determiners — they introduce a referent the sentence has not mentioned.
#
# ⇒⇒ **TRIMMED FROM EIGHT WORDS TO TWO, 2026-08-11, AND THE SIX WERE MY OWN SSOT VIOLATION.**
#   Measured by emptying the set and re-reading every corpus span: exactly TWO entries change
#   any answer — `own` BLOCKS a wrong reading (*their own network* would otherwise read
#   `existing`, because `their` is definite) and `new` SUPPLIES a right one (*3 new vms*).
#   `different`, `separate`, `second`, `spare`, `fresh`, `extra` changed nothing: rung 6's
#   *"a different network"* is settled by the indefinite article alone.
#
#   ⇒ I justified this file's determiner sets as a CLOSED FUNCTION-WORD CLASS, which is true of
#     INDEFINITE / DEFINITE / UNIVERSAL and **false of these** — contrastive adjectives are open
#     class, so `provisioned`, `standalone`, `dedicated` are missing and always would be. That is
#     the unfinishable word list the operator ruled out, shipped hours later at small enough
#     scale to look harmless.
#   ⇒ AND IT REMOVES A DRIFT HAZARD: `different` and `same` also live in `GRAMMAR` and in
#     `residue.RELATIONAL_WORDS`. Three copies of one idea, and R2's correctness rested on
#     this one. Dropping them here leaves each word with a single owner.
NOVEL = {"new", "own"}

# ── MODIFIERS INTO CONDITIONS, where the manifest can settle it ────────────────────────
LINKING = {"called", "named", "labelled", "labeled", "tagged", "marked", "is", "are", "be",
           "the", "a", "an", "with", "on", "in", "to", "of", "that", "do", "does", "and",
           "currently", "already", "its", "their"}

# A NAMING CUE POINTS AT THE KIND'S KEY, whatever that key happens to be called.
#
# "a vm NAMED alpha" worked only by luck — `named` stems to `nam`, which prefixes the attribute
# `name`, and a vm's key IS `name`. A network's key is `net_name`, and `called` stems to
# nothing that prefixes it, so "a network CALLED lab" produced no condition at all. The cue
# should point at the KEY the manifest declares, not at an attribute that happens to be spelt
# similarly.
NAMING_CUES = {"called", "named", "titled", "known"}

# ⇒⇒ THE MAGNITUDE COMPARATORS — a closed class of English, and NOT the ones above.
#   `COMPARATORS` declares the COUNT comparators (`at most`, `exactly`) and they answer *how
#   many things*. These answer *how big a value*, which is a different question over a
#   different slot, and nothing has ever declared them.
#   ⇒ Longest first, so `more than` wins over `more`.
MAGNITUDE: Dict[str, str] = {
    "no more than": "le", "no less than": "ge", "greater than": "gt", "more than": "gt",
    "less than": "lt", "fewer than": "lt", "at or above": "ge", "at or below": "le",
    "over": "gt", "above": "gt", "under": "lt", "below": "lt", "beyond": "gt",
}

NEGATOR_TOKENS = frozenset({"not", "n't", "never", "no"})


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ SCHEMA — referring pronouns, restrictors, determiners, separators
# ═   (consumer: schema.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# A BARE PRONOUN REFERS; A RESTRICTED ONE DOES NOT. Closed set, so this is arithmetic.
#
# The operator, 2026-08-08: *"or not even by name, through context — 'create X then put it in
# Y' is actually 2 X references, one is X as create and then 'it' is also a reference to X."*
#
# The model already shows this. Rung 2 came back as `vm` / `beta` / `it`, with `it` declared
# as an object of its own.
#
# ⇒ **BUT ONLY A BARE PRONOUN FOLDS.** *"the ones that do not answer"* is NOT a reference to
#   *"every vm"* — it is a different set, restricted. Folding on the word `ones` alone would
#   silently merge a subset into its superset, which is rung 11's whole distinction destroyed.
#   So the match must be the WHOLE name, with nothing else in it.
# ⇒⇒ MEASURED REGRESSION, 2026-08-08, AND IT WAS TWO OF THESE MECHANISMS COMPOUNDING.
#
# `one`, `ones`, `that`, `those` and `these` USED TO BE IN THIS SET. They are the HEADS OF
# RESTRICTED DESCRIPTIONS, not pro-forms: *"the ones that do not answer"*. The naming question
# chunks that phrase down to the bare token `ones` — and the fold then merged `ones` into
# `vm`, correctly by its own rule, destroying rung 11's subset.
#
#     pre-fold   ping · vm · ones          <- three rows, `ones` badly representing the subset
#     folded     ping · vm                 <- the subset GONE, refs=['ones'] on `vm`
#
# The guard checked the whole name for a restriction, but the chunker had ALREADY stripped it.
# So: only unambiguous pro-forms are listed, AND the request is consulted for a restrictor.
REFERRING_PRONOUNS = frozenset({
    "it", "its", "them", "they", "their", "theirs", "both",
    "all of them", "each of them", "every one of them",
})

# a word that turns a noun phrase into a RESTRICTED description — "the ones THAT do not answer"
RESTRICTORS = ("that", "which", "who", "whose", "with", "without", "not")

# ── A TRUNCATED NAME IS REPAIRED FROM THE REQUEST, NOT RE-ASKED ────────────────────────
DETERMINERS = ("the", "a", "an", "every", "all", "each", "both", "any", "some", "no",
               "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")

BOUNDARY_SEPARATORS = (",", ";", " and ", " then ", " but ", "—", " - ")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ SELF-REPAIR — retractions, corrections, dangling
# ═   (consumer: self_repair.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ WHAT WITHDRAWS THE WHOLE REQUEST. Complete instructions in themselves.
RETRACTIONS = ("never mind", "nevermind", "forget it", "forget that", "cancel that",
               "disregard that", "disregard it", "ignore that", "scratch that",
               "belay that", "as you were")

# ⇒ WHAT REPLACES PART OF IT. `i mean` is the core; the rest are the frames it appears in.
#   ⇒ ⚠ `sorry` IS ABSENT ON PURPOSE — see the module note.
CORRECTIONS = ("i mean", "i meant", "no wait", "wait no", "rather", "correction",
               "make that", "or rather", "not that")

# ⇒⇒ **A WORD THAT CANNOT END AN UTTERANCE.** A speaker who breaks off mid-constituent has
#   abandoned the phrase — `just at the`, `there's`, `i'll`, `and it's got a`. Determiners,
#   prepositions, auxiliaries and conjunctions all DEMAND a complement, so ending on one is
#   structure telling you the turn was cut short. No vocabulary of repair words is involved.
DANGLING = frozenset({
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "its", "their",
    "at", "on", "in", "to", "of", "with", "from", "by", "for", "into", "onto", "over",
    "and", "or", "but", "so", "just", "very", "quite",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "will", "would", "can", "could", "shall", "should", "do", "does",
    "i'll", "i've", "i'm", "there's", "we're", "we'll", "you're", "it's", "that's",
})


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ SPEECH ACT — the closed classes that decide order / question / statement
# ═   (consumer: speech_act.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ── the closed classes ───────────────────────────────────────────────────────────────
#
# ⇒⇒ NINE WH-WORDS. ENGLISH HAS NO MORE AND GAINS NONE — which is the whole licence for
#   writing them down, and the same one `INDEFINITE` and `AFFIRMATION` already claim.
WH_WORDS = frozenset({"who", "whom", "whose", "what", "which",
                      "when", "where", "why", "how"})

# ⇒ THE AUXILIARIES THAT INVERT to make a yes-no question. Closed, and closed in the strong
#   sense: a new English verb never becomes one.
AUXILIARIES = frozenset({"do", "does", "did", "can", "could", "will", "would",
                         "shall", "should", "may", "might", "must",
                         "is", "are", "was", "were", "am", "be", "been",
                         "have", "has", "had"})

# ⇒ THE COPULA — a PREDICATION about something, which is what separates *"n1 is the jumpbox"*
#   (teaching) from *"good morning doorman"* (nothing).
COPULA = frozenset({"is", "are", "was", "were", "am", "be", "been", "'s", "'re"})

# ⇒ THE ADDRESSEE. One pronoun, and the entire difference between an order and a question once
#   a sentence has inverted.
ADDRESSEE = frozenset({"you", "u", "ya"})

# ⇒ ⚠ **AND THE CONTRACTED FORMS, WHICH ARE THE SAME PRONOUN.** `i'd like you to …` is the
#   keyed declarative directive and `i'd` is not `i`, so the branch that reads it never fired —
#   found 2026-08-16 when rung 8's own courtesy arm came back UNREAD. A pronoun plus a clitic
#   is a closed class twice over: two pronouns, four clitics, and English adds neither.
FIRST_PERSON = frozenset({"i", "we", "i'd", "i've", "i'll", "i'm",
                          "we'd", "we've", "we'll", "we're"})

# ⇒⇒ **THE CONVERSATION'S OWN PARTICIPANTS — and this is the generalisation the addressee test
#   should always have been.** A request to ACT is aimed at somebody in the room; a question is
#   aimed at the lab. `can YOU stop the vms` and `can WE stop the vms` are the same request
#   with a different pronoun, and only the first was read as one:
#
#       can you stop the vms      the addressee        -> an ORDER
#       can we stop the vms       speaker AND hearer   -> an ORDER, and it read as a QUESTION
#       let's stop the vms        the same, hortative  -> an ORDER
#       is alpha running          a LAB THING          -> a QUESTION
#
#   ⇒ **FOUR SENTENCES WERE ONE DEFECT.** `do it again`, `let's …`, `let me …` and `can we …`
#     were recorded as four unrelated curiosities until the operator asked what was still open;
#     every one is the subject test knowing only `you`. Personal pronouns are a closed class,
#     and *who is in the conversation* is the honest boundary.
#   ⇒ ⚠ **AND IT IS THE PLURAL, NOT THE FIRST PERSON.** The first cut took every participant
#     and read *"SHOULD I delete db or keep it?"* as an order — a deliberative question, the
#     speaker weighing their own act. **The speaker ALONE is deliberating; the speaker WITH US
#     is proposing**, and grammatical number is exactly that line:
#
#         can WE stop the vms       joint action     -> an ORDER
#         should I delete db        deliberation     -> a QUESTION
#
#     `i`/`me` are therefore deliberately absent. `let me …` still reads as an order, from the
#     hortative branch, because `let` asks us to permit rather than asking us what to think.
PARTICIPANTS = ADDRESSEE | frozenset({"we", "us"})

# ⇒ THE QUESTION'S WRAPPER — `tell me if X` asks what `did X?` asks; the wrapper marks
#   nothing (the operator's cc-0003 rulings, both of them, 08-18). `show me` is NOT here:
#   `show` acts on a THING and stays an action. Closed, two entries, each one ruled.
WRAPPERS = ("tell me", "let me know")

# ⇒ COURTESY — an adjunct that defers, marks nothing, grants nothing
#   ([[gorgon-courtesy-escalates-intent]] is what happens when a reader treats it as
#   content). Promoted from pass 1's inline literals 2026-08-19 so the front door and
#   the consumption list read ONE copy.
COURTESY = ("when you get a chance", "if you get a chance")

# ⇒⇒ THE RECIPIENT. *"show ME the vms"* — and **nothing in this lab can be handed to a person
#   except information.** A vm cannot be given to the operator; a list of vms can. That is what
#   makes a first-person indirect object an interrogative signal in this domain, where in
#   general English it is not.
#   ⇒ ⚠ AND IT COSTS ONE READING, KEYED AS SUCH: *"make me a vm"* is a BENEFACTIVE — build it
#     FOR me — and this rule cannot tell that from a recipient. It fails toward asking.
RECIPIENT = frozenset({"me", "us"})

# ⇒ THE DEONTIC MODALS — obligation and permission. Every one is already a member of
#   `AUXILIARIES`; naming them again here is not a second list but a SUBSET of one, because
#   what separates *"must keep a snapshot"* from *"is keeping a snapshot"* is which auxiliary
#   it is. Closed, and closed in the strong sense: English gains no new modal.
DEONTIC = frozenset({"must", "should", "shall", "may", "ought"})

# ⇒ AND THE FREQUENCY ADVERBS. **A rule quantifies over TIME** — that is what makes *"never
#   delete a vm"* a standing rule and *"don't delete the vms"* an instruction about now. Two
#   words, closed, and the distinction they draw is the whole of the declaration reading.
ALWAYS_NEVER = frozenset({"never", "always"})

# ⇒ LEADING PARTICLES that carry no proposition. Stripped before the clause is read, because
#   `please stop every vm` is `stop every vm` and nothing else.
OPENERS = frozenset({"please", "kindly", "just", "now", "then", "also",
                     "and", "but", "so", "ok", "okay", "well", "yeah"})

# ⇒ ANAPHORA — a pronoun REFERS to what an earlier clause named, and a clause is read on its
#   own. Without this `ping every vm and stop THE ONES that do not answer` reads its second
#   clause as naming nothing, i.e. as talk about the conversation rather than an instruction.
#   Pronouns and demonstratives are closed classes; this is the same licence as everything else
#   in this file.
#   ⇒ ⚠ **`that` AND `this` ARE NOT IN IT, AND THAT IS A MEASURED EXCLUSION.** They are
#     demonstratives that just as often stand in SUBJECT position — *"thanks, THAT worked"* —
#     and counting them as a named object read a pleasantry as an order to act. A false serve
#     produced by a pronoun list that was one entry too generous.
ANAPHORA = frozenset({"it", "them", "they", "those", "these", "one", "ones"})

# ⇒ THE RELATIVIZERS. They open a SUBORDINATE clause, so a copula behind one is not the
#   sentence's own predication — *"launch every vm THAT IS currently stopped"* is an order, and
#   without this test the copula rule below would call it a piece of teaching.
RELATIVIZERS = frozenset({"that", "which", "who", "whom", "whose", "where", "when"})

# ⇒⇒ THE FUNCTION WORDS, WHICH ARE THE WHOLE TEST FOR *"IS THIS AN IMPERATIVE"*.
#
#   An English imperative has NO SUBJECT — it opens on its verb. So the test is not *"is this
#   word a verb"*, which would need an open-class lexicon nobody can finish; it is **is this
#   word a function word**, and the complement is what an imperative can start with. Every set
#   below is closed, and the determiners are imported rather than re-listed.
#
#   ⇒ **AND THE ALTERNATIVE WAS TRIED AND REJECTED IN THE SAME HOUR.** `scan._operation_words`
#     looks like the verb list this wants — it holds `put`, `ping`, `take`, `make` — and it
#     also holds `from`, `to`, `as`, `label`, `vms`. Reading `FROM now on every new vm gets the
#     'fleet' label` as an imperative would turn a standing RULE into an order to act now: a
#     false serve, produced by a list that was never meant to answer this question.
PREPOSITIONS = frozenset({"of", "on", "in", "at", "to", "from", "with", "without", "by",
                          "for", "into", "onto", "over", "under", "about", "after",
                          "before", "between", "through", "per", "as", "than", "since",
                          "until", "upon", "off", "out", "up", "down", "along", "across"})

CONJUNCTIONS = frozenset({"and", "or", "but", "if", "unless", "while", "because",
                          "although", "though", "except", "nor", "yet", "whether"})

PRONOUNS = frozenset({"i", "we", "you", "he", "she", "it", "they", "them", "him", "her",
                      "us", "me", "my", "our", "your", "his", "its", "their", "there",
                      "this", "that", "these", "those", "one", "ones", "something",
                      "anything", "nothing", "everything", "someone", "anyone"})

# ⇒ THE NEGATORS an imperative can carry. `don't` expands to these two before anything reads
#   position, so a negative imperative is not mistaken for an inversion.
NEGATORS = frozenset({"not", "never", "no"})

# ⇒ AUXILIARY CONTRACTIONS, expanded so POSITION can be read. `don't start` is `do not start`
#   — an imperative — and without expansion its first token is neither an auxiliary nor a verb.
#   Contractions of function words are as closed as the function words themselves.
# ⇒⇒ **THE APOSTROPHE-LESS FORM IS THE ONE PEOPLE ACTUALLY TYPE, AND HALF OF THEM WERE
#   MISSING.** `dont` and `cant` were here; `isnt`, `doesnt`, `arent` were not — so *"kaya isnt
#   a vm"* kept `isnt` as one unknown token, the clause looked like a verb-initial imperative,
#   and a DENIAL read as **directive-act**. A false serve produced by a table that was
#   inconsistent rather than wrong.
#   ⇒ Contractions of function words are as closed as the function words themselves, so the
#     completion is a lookup and not a vocabulary.
CONTRACTIONS = {
    "don't": ("do", "not"), "dont": ("do", "not"),
    "doesn't": ("does", "not"), "doesnt": ("does", "not"),
    "didn't": ("did", "not"), "didnt": ("did", "not"),
    "can't": ("can", "not"), "cant": ("can", "not"),
    "won't": ("will", "not"), "wont": ("will", "not"),
    "wouldn't": ("would", "not"), "wouldnt": ("would", "not"),
    "shouldn't": ("should", "not"), "shouldnt": ("should", "not"),
    "couldn't": ("could", "not"), "couldnt": ("could", "not"),
    "isn't": ("is", "not"), "isnt": ("is", "not"),
    "aren't": ("are", "not"), "arent": ("are", "not"),
    "wasn't": ("was", "not"), "wasnt": ("was", "not"),
    "weren't": ("were", "not"), "werent": ("were", "not"),
    "haven't": ("have", "not"), "havent": ("have", "not"),
    "hasn't": ("has", "not"), "hasnt": ("has", "not"),
    "hadn't": ("had", "not"), "hadnt": ("had", "not"),
    "what's": ("what", "is"), "who's": ("who", "is"), "where's": ("where", "is"),
    "how's": ("how", "is"), "that's": ("that", "is"), "it's": ("it", "is"),
    "i'd": ("i", "would"), "i'll": ("i", "will"), "i'm": ("i", "am"), "i've": ("i", "have"),
    "we'd": ("we", "would"), "we'll": ("we", "will"), "we've": ("we", "have"),
    "you'd": ("you", "would"), "you'll": ("you", "will"), "you've": ("you", "have"),
    "let's": ("let", "us"),
}

# ⇒ THE WH-WORD NAMES THE ANSWER, and this is the second job the closed class does. `which`
#   asks for the members; `how many` asks for a number. Same nine words, read for a different
#   question — no new vocabulary, and no way for the two readings to drift apart.
#   ⇒ ⚠ **`where` IS NOT ONE OF THEM, AND THAT IS A CORRECTION.** It was listed here and
#     *"where is alpha"* routed to a select or a meaning lookup — neither of which is a
#     LOCATION. It joins `when` and `why` in the honest branch below: three wh-words whose
#     answers are a place, a time and a reason, and this system can produce none of the three.
#     Saying so is better than answering a different question confidently.
MEMBER_WORDS = frozenset({"which", "what", "who", "whom", "whose"})

# ⇒ THE PERSONAL PRONOUNS THAT CAN BE A CLAUSE'S SUBJECT. Closed, and the whole of the
#   subordinate-wh test below.
SUBJECT_PRONOUNS = frozenset({"i", "you", "we", "he", "she", "it", "they"})

# ⇒⇒ **THE SUBORDINATING CONJUNCTIONS — A SUBSET OF A CLASS THIS FILE ALREADY DECLARES**, and
#   not a new list. `CONJUNCTIONS` holds both kinds; these are the ones that open a clause
#   BENEATH another, and the coordinating members — `and`, `or`, `but`, `nor`, `yet` — are
#   deliberately absent, because a clause joined by one of those IS a main clause.
#   ⇒ The same move `DEONTIC` makes on `AUXILIARIES`: a subset, named where it is used.
#   ⇒ `since`, `until`, `after` and `before` are in `PREPOSITIONS` and do this job too when a
#     SUBJECT follows them; they are included here for the copula test only, where a bare
#     preposition reading cannot arise.
SUBORDINATING = frozenset({"if", "unless", "while", "because", "although", "though",
                           "whether", "since", "until", "after", "before", "once",
                           "whenever"}) | RELATIVIZERS


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ TEMPORAL — units, clock and calendar words, recurrence, standing
# ═   (consumer: temporal.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# ⇒ THE UNITS THE STORE CAN HOLD, spelled in English. `procedures._SECONDS` is the authority
#   for which four exist; a fifth here would be a schedule nobody could file.
UNITS = frozenset({"second", "seconds", "minute", "minutes", "hour", "hours",
                   "day", "days"})

# ⇒ AND THE UNITS THE OPERATOR USES THAT THE STORE DOES NOT NAME. A night is a day and a week
#   is seven of them — both are expressible as a span, so both are admitted; a MONTH is not
#   (they differ in length), and it is deliberately absent rather than rounded.
COARSE = frozenset({"night", "nights", "week", "weeks"})

# ⇒ THE FREQUENCY ADVERBS — a unit and a recurrence folded into one word. Closed, and derived:
#   each one is a unit above with `-ly` on it, which is why the set cannot drift from `UNITS`.
FREQUENCY_ADVERBS = frozenset({"hourly", "daily", "nightly", "weekly"})

# ⇒ THE DEICTICS — time named relative to now. English has these and has never added one.
#   ⇒ ⚠ `now` AND `currently` ARE NOT HERE, AND THAT IS THE WHOLE POINT OF THE CLASS. They fix
#     the time as THIS MOMENT, which is the one time that is not a schedule — *"launch every vm
#     that is CURRENTLY stopped"* is rung 5 and runs now, correctly.
DEICTIC = frozenset({"tomorrow", "tonight", "yesterday", "overnight"})

# ⇒ THE CALENDAR. Seven and twelve, and neither list grows.
WEEKDAYS = frozenset({"monday", "tuesday", "wednesday", "thursday",
                      "friday", "saturday", "sunday"})

MONTHS = frozenset({"january", "february", "march", "april", "may", "june", "july",
                    "august", "september", "october", "november", "december"})

# ⇒ WHAT MAKES A TIME A RECURRENCE RATHER THAN AN INSTANT. `every` is `scan.UNIVERSAL`'s own
#   word doing a second job — over OCCASIONS instead of over members — and `each` behaves the
#   same way. The distinction is not in the word; it is in what follows it.
RECURRING = frozenset({"every", "each"})

# ⇒⇒ THE EVENT SUBORDINATORS — the words that say *something happening starts this*. Closed,
#   and this is the half the operator called the meta-declaration: *"the rule is 'delete vm'
#   triggered by 'stop vm/being done with it'."*
#
#   ⇒ ⚠ **`when` IS ABSENT FROM THE SET AND HANDLED SEPARATELY, BECAUSE IT IS TWO WORDS.**
#     *"WHEN did you stop it"* asks about the past and *"WHEN you get a chance"* is an adjunct
#     — a distinction that already cost this project a defect on 2026-08-16, in the other
#     direction. Inversion is what separates them, and `events_in` asks for a subject.
EVENTS = frozenset({"after", "whenever", "once"})

EVENT_PHRASES = ("every time", "each time", "as soon as", "any time")

ALWAYS_STANDING_PHRASES = ("every time", "each time", "any time")

# ⇒ THE STANDING FRAME. A trigger is a RULE plus an event; this is the phrase that makes a
#   sentence standing when no modal or frequency adverb does it. The operator's own example
#   opens with it.
STANDING = ("from now on", "from here on", "going forward", "in future", "in the future")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ═ TESTIMONY — the negated modals and copulas of a symptom
# ═   (consumer: testimony.py)
# ═══════════════════════════════════════════════════════════════════════════════════════

# the negated forms, closed: modals whose complement is a bare verb by grammar, and the
# copula/do forms whose complement must then be tested for verbality
NEG_MODALS = frozenset({"won't", "wont", "can't", "cant", "cannot", "couldn't",
                        "wouldn't", "shan't"})

NEG_DO = frozenset({"doesn't", "don't", "didn't"})

TESTIMONY_COPULAS = frozenset({"is", "are", "was", "were", "isn't", "aren't", "wasn't", "weren't"})

ITERATIVES = frozenset({"keeps", "keep", "kept"})

# R2 (operator-ordered 2026-08-19): the indefinite pronoun + copula IS the malfunction
# marker — "SOMETHING IS WRONG with the dmz network". Closed pronouns, closed copulas;
# the complement word is free because the FRAME carries the meaning.
INDEFINITES = frozenset({"something", "anything", "nothing"})
