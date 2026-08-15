"""speech_act.py — WHAT KIND OF THING WAS SAID, READ FROM CLOSED CLASSES AND THE MANIFEST.

    after the clause split, before anything is built

# ⇒⇒ THE GAP THIS FILLS, STATED AS A MEASUREMENT

`linguistics.mood_of` returns two values, `do` and `achieve`, and every sentence English has
falls into one of them. So a question is an instruction, a greeting is an instruction, and a
rule about future behaviour is an instruction. Measured live on 2026-08-14:

    "how many vms are there"                   neither  BOUNCE  ops=0 goals=0
    "list the vms"                             neither  BOUNCE  ops=0 goals=0
    "which vms are running"                    neither  BOUNCE  ops=0 goals=0
    "how many machines carry the fleet label"  **act**  ASK     -> add_label(fleet_vms, fleet)

**A question read as an instruction to apply labels.** `produces()` can return `ask`, `QUERY`
is enforced end to end, and gate 4's `answer-not-act` is wired — and none of it is reachable,
because nothing upstream ever says *this was a question*.

# ⇒⇒ WHY A LOOKUP AND NOT A MODEL CALL — MEASURED, AND DO NOT RE-TRY IT

Asked in a vacuum, one closed question with options chosen to partition, over the same four
arms this is scored on: **30/60, which is chance**, and **0 of 14 polite orders** read as
instructions. It called *"would you mind stopping the web server"* a question. Third time in
one day a model judgement came back near-chance where a lookup was exact
([[gorgon-sentence-processing]]).

⇒ **AND THE SIGNAL IS CLOSED-CLASS, WHICH IS THIS PROJECT'S OWN LICENCE FOR A WRITTEN LIST.**
  Nine wh-words; English gains no more. The auxiliaries that invert. The pronouns. Stated in
  four places already — `scan.INDEFINITE`, `reading_answers.NEGATION`, `AFFIRMATION`,
  `gate4`'s RECIPROCAL — and never once applied to the interrogative.

# ⇒⇒ THE RULE, AND THE ONE THAT NEARLY SHIPPED WRONG

The morning's draft was *"inversion + no wh-word + a MANIFEST VERB -> an order"*. Writing the
key first ([[tests.bench.sentence_key]]) killed it: **"is alpha running?"** is inverted, has
no wh-word, and `run` IS a manifest verb — so that rule serves a plain question. A false serve
cannot be taken back; a false avoid costs a question.

⇒ **THE DISCRIMINATOR IS THE INVERTED SUBJECT.** A polite imperative inverts over the
  ADDRESSEE; a yes-no question inverts over anything else:

      can YOU delete the vms       the addressee   -> an ORDER
      is ALPHA running             a lab thing     -> a QUESTION
      are THERE any stopped vms    existential     -> a QUESTION

  `you` is a pronoun. Still a lookup, still no content-word list.

# ⇒⇒ AND ONE CASE IS NOT GRAMMAR AT ALL

    list the vms          bare verb, no wh-word, no inversion — grammatically IDENTICAL to
    stop the vms          `stop the vms`, and one of them asks while the other acts.

Nothing in the sentence separates them. What separates them is **whether the operation the
verb names changes the world**, which `effects.actors` already computes as the complement of
the observers — the same set `produces()` reads. So the interrogative reader is closed classes
**plus one manifest lookup**, and the lookup is not a second opinion about an existing one.

# ⇒ WHAT THIS SETTLES AND WHAT IT REFUSES TO GUESS

    DIRECTIVE_ACT · DIRECTIVE_INFORM · META_CONTROL · EXPRESSIVE · ASSERTIVE     settled
    DECLARATION · COMMISSIVE                                                     None, for now
    ANSWER                                                                       NOT OURS

⇒ **`None` IS A REAL ANSWER, exactly as `verb_kind`'s UNKNOWN is.** A clause this cannot read
  stays unread, and the caller keeps whatever it would have done — so adding this file can
  only replace a guess with a reading, never remove one. That is what makes it safe to land
  before anything routes on it.
⇒ **AND `ANSWER` IS DELIBERATELY ABSENT.** `reading_answers.settle` owns the operator's reply
  and has since 2026-08-13. A second reader for it would be the twin-owner defect this project
  has now filed more than a dozen times; an answer only exists in reply to a question we asked,
  and this file never knows that.
"""
from typing import List, Optional, Sequence, Tuple

from planner.formula.legal import Board

# ⇒ THE TYPES. Named for WHAT CAN BE BUILT from the clause, never for what it means — the one
#   method that has held all session ([[gorgon-sentence-processing]]).
#
# ⇒⇒ **DECLARED HERE AND NOT IMPORTED FROM THE KEY, DELIBERATELY, TWICE OVER.** The first cut
#   of this file imported them from `tests.bench.sentence_key` and that is wrong in two
#   independent ways: production importing from `tests/` is the upward edge `test_layering`
#   forbids, and a key that shares a symbol with the thing it grades has stopped being a key.
#   The two vocabularies are plain strings and agree BY VALUE; the probe asserts it, so a
#   rename cannot drift them silently.
DIRECTIVE_ACT = "directive-act"
DIRECTIVE_INFORM = "directive-inform"
ASSERTIVE = "assertive"
DECLARATION = "declaration"
META_CONTROL = "meta-control"
EXPRESSIVE = "expressive"
COMMISSIVE = "commissive"

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
FIRST_PERSON = frozenset({"i", "we"})

# ⇒ EXISTENTIAL `there` — the inverted subject of *"are there any stopped vms"*. It names
#   nothing, so the subject test needs it by name or it reads as an unknown thing.
EXISTENTIAL = frozenset({"there"})

# ⇒ THE POLAR COMPLEMENTIZER. `whether` introduces an EMBEDDED yes-no question and does nothing
#   else in English — *"check whether alpha is running"*. A closed class of one, for this
#   purpose; `if` shares the job and also means the conditional, so it is deliberately absent.
WHETHER = frozenset({"whether"})

# ⇒⇒ THE RECIPIENT. *"show ME the vms"* — and **nothing in this lab can be handed to a person
#   except information.** A vm cannot be given to the operator; a list of vms can. That is what
#   makes a first-person indirect object an interrogative signal in this domain, where in
#   general English it is not.
#   ⇒ ⚠ AND IT COSTS ONE READING, KEYED AS SUCH: *"make me a vm"* is a BENEFACTIVE — build it
#     FOR me — and this rule cannot tell that from a recipient. It fails toward asking.
RECIPIENT = frozenset({"me", "us"})

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
CONTRACTIONS = {
    "don't": ("do", "not"), "dont": ("do", "not"),
    "doesn't": ("does", "not"), "didn't": ("did", "not"),
    "can't": ("can", "not"), "cant": ("can", "not"),
    "won't": ("will", "not"), "wouldn't": ("would", "not"),
    "shouldn't": ("should", "not"), "couldn't": ("could", "not"),
    "isn't": ("is", "not"), "aren't": ("are", "not"),
    "wasn't": ("was", "not"), "weren't": ("were", "not"),
    "haven't": ("have", "not"), "hasn't": ("has", "not"), "hadn't": ("had", "not"),
    "what's": ("what", "is"), "who's": ("who", "is"), "where's": ("where", "is"),
    "how's": ("how", "is"), "that's": ("that", "is"), "it's": ("it", "is"),
    "i'd": ("i", "would"), "i'll": ("i", "will"), "i'm": ("i", "am"), "i've": ("i", "have"),
    "we'd": ("we", "would"), "we'll": ("we", "will"), "we've": ("we", "have"),
    "you'd": ("you", "would"), "you'll": ("you", "will"), "you've": ("you", "have"),
    "let's": ("let", "us"),
}


def words_of(clause: str) -> List[str]:
    """The clause as tokens, with auxiliary contractions expanded so POSITION can be read."""
    import re
    out: List[str] = []
    # ⇒⇒ **AN IDENTIFIER IS ONE TOKEN.** `[a-z']+|[0-9]+` split `n1` into `n` and `1`, so every
    #   bare name the corpus uses — `n1`, `n2`, `n3`, `mesh0`, `vm1` — arrived as TWO words. It
    #   read harmlessly for the mood (both halves are content words), and it broke the moment
    #   something counted them: the archive asks whether the subject is exactly ONE word, and
    #   *"n1 is the jumpbox"* looked like a two-word phrase and was declined.
    #   ⇒ A BARE NUMBER STAYS ITS OWN TOKEN — `5 vms` is a count and `_is_function_word` reads
    #     it as one. Only a digit ATTACHED to a word joins it.
    for raw in re.findall(r"[a-z][a-z0-9']*|[0-9]+", str(clause).lower()):
        token = raw.strip("'")
        if not token:
            continue
        out.extend(CONTRACTIONS.get(raw, CONTRACTIONS.get(token, (token,))))
    return out


def _after_openers(words: Sequence[str]) -> List[str]:
    """Drop leading particles that carry no proposition — `please`, `and`, `so`, `ok`."""
    i = 0
    while i < len(words) and words[i] in OPENERS:
        i += 1
    return list(words[i:])


# ── the manifest half — one lookup, and it is not a second opinion ───────────────────
def _readers(board: Optional[Board] = None) -> set:
    """Every operation that only LOOKS — asked of the manifest, owned by `effects.askers`.

    ⇒⇒ **THIS HELD ITS OWN COPY FOR AN AFTERNOON, AND THE COPY WAS THE BUG REPORT.** When
      `list the vms` read as nothing at all, the cause was that `askers` knew about probes and
      nothing else — so the enumerators were added HERE, in the seam, because that was the
      file being worked on. Two answers to *"does this tool change the world"*, which is the
      twin-owner shape this project has filed more than a dozen times.

    ⇒ **THE FACT BELONGS TO THE MANIFEST AND NOW LIVES THERE** (`acts.<name>.reads`, plus the
      kinds' `list`), so this is one call. The seam asks; it does not decide.
    """
    from planner.ir import config as _config, effects as _effects
    return set(_effects.askers(_config.KINDS))


def _verb_ops(verb: str, board: Optional[Board] = None) -> List[str]:
    """Every manifest operation whose head word is this verb. `list` -> the four `list_*`."""
    from planner.ir import config as _config, effects as _effects
    verb = str(verb).lower()
    every = set(_effects.tools_of(_config.KINDS)) | _readers(board)
    return [op for op in every
            if str(op).lower().split("_")[0] == verb or str(op).lower() == verb]


def changes_the_world(verb: str, board: Optional[Board] = None) -> Optional[bool]:
    """Does the operation this verb names CHANGE anything — True, False, or None if unknown.

    ⇒⇒ **THE ONLY THING THAT SEPARATES `list the vms` FROM `stop the vms`.** Both are bare
      imperatives over a manifest kind; the grammar is identical and the intent is opposite.
      `effects.actors` is *every tool the manifest names, minus the probes*, so a verb whose
      operations are all outside it can only report.

    ⇒ **NONE MEANS THE MANIFEST DOES NOT KNOW THE VERB**, which is a finding rather than a
      default — it is what tells an imperative apart from an instruction about the conversation
      (*"don't start any changes"* — `start` names no operation at all).
    """
    from planner.ir import config as _config, effects as _effects
    ops = _verb_ops(verb, board)
    if not ops:
        return None
    acting = _effects.actors(_config.KINDS) - _readers(board)
    return any(op in acting for op in ops)


def names_something(words: Sequence[str], board: Optional[Board] = None, world=None) -> bool:
    """Does this clause name a KIND the lab keeps, or a member the world holds?

    ⇒ **THE OBJECT IS THE DISCRIMINATOR FOR META-CONTROL**, and it is structural rather than
      lexical: *"stop the vms"* takes a kind, *"don't start any changes"* does not, because
      `changes` is not a kind. Nothing has to be listed for that to work — the manifest's own
      index answers it, and a lab that gains a kind gains the word for free.
    """
    from .scan import _index
    index = _index(board or Board())
    if any(w in index for w in words):
        return True
    # ⇒ A PRONOUN NAMES WHAT AN EARLIER CLAUSE NAMED. `stop THE ONES that do not answer` is an
    #   instruction about machines; only the clause split hides that, and the split is right.
    if any(w in ANAPHORA for w in words):
        return True
    known = set()
    if world is not None:
        try:
            known = {str(n).lower() for n in getattr(world, "names", lambda: [])()}
        except Exception:
            known = set()
    return bool(known & set(words))


# ── the reader ───────────────────────────────────────────────────────────────────────
def act_of(clause: str, board: Optional[Board] = None, world=None) -> Optional[str]:
    """The speech act of ONE clause, or None when nothing settles it.

    ⇒⇒ **THE ORDER OF THESE TESTS IS THE DESIGN.** Each one is a position test over a closed
      class; the first that fires wins, and they are sequenced so the narrow shapes are read
      before the broad ones. Moving any of them changes answers — `launch every vm THAT IS
      currently stopped` holds a copula, and reading copulas before imperatives would call
      rung 5 a piece of teaching.
    """
    words = _after_openers(words_of(clause))
    if not words:
        return None
    head = words[0]

    # ⇒ 1 · WH-HEADED. The most direct signal English has for a question — and the exception
    #   that eats it is the addressee: *"why don't you stop the vms"* is wh-headed and is an
    #   ORDER. Read the exception first or the rule is wrong on the one case that costs.
    if head in WH_WORDS and not _subordinate_wh(words, clause):
        # ⇒⇒ **THE EXCLAMATIVE IS A WH-WORD AND IS NOT A QUESTION** — the mirror of the polite
        #   imperative, and the reason the wh rule cannot stand alone in either direction.
        #   *"what a mess"* and *"how odd"* are the two English exclamative frames, and both
        #   are PREDICATELESS: no copula, no auxiliary, no verb the lab knows. A question
        #   always has one, even a fragment one (*"what about db?"* carries the mark instead).
        if not _asks_outright(clause) and not _has_predicate(words, board):
            return EXPRESSIVE
        # ⇒⇒ **THE WH-QUESTION THAT IS AN ORDER, AND IT IS ONE IDIOM RATHER THAN A PATTERN.**
        #   *"why don't you stop the vms"* is a suggestion in interrogative clothes — but the
        #   first cut of this test was *any wh + addressee + acting verb*, and that read **"when
        #   did you stop it?"** as an ORDER TO STOP SOMETHING. A question about the past,
        #   answered by doing the thing again: a false serve, and the expensive kind.
        #   ⇒ THE FRAME IS `why` PLUS A NEGATION — *why don't you*, *why not*. Both closed
        #     class, and narrow on purpose: every other wh-word with an addressee is asking.
        if (head == "why" and any(w in NEGATORS for w in words)
                and _addressed_to_us(words) and _acting_verb_in(words, board)):
            return DIRECTIVE_ACT           # "why don't you stop the vms"
        return DIRECTIVE_INFORM

    # ⇒ 2 · INVERSION. An auxiliary in first position, and THE SUBJECT DECIDES. This is the
    #   test that nearly shipped inverted — see the module note on `is alpha running?`.
    if head in AUXILIARIES:
        subject = _inverted_subject(words)
        if subject in ADDRESSEE:
            return DIRECTIVE_ACT           # "can you delete the vms"
        if subject is None:
            # ⇒ AN AUXILIARY WITH NO SUBJECT AT ALL IS A NEGATIVE IMPERATIVE, not a question:
            #   `do not start any changes`. It falls through to the imperative reading below.
            return _imperative(_strip_imperative_frame(words), board, world)
        return DIRECTIVE_INFORM            # "is alpha running" · "are there any stopped vms"

    # ⇒ 3 · THE DECLARATIVE DIRECTIVE. *"i'd like you to take a snapshot of db"* has no
    #   inversion and no imperative verb in first position, and is plainly an order. Two
    #   pronouns settle it — the speaker and the addressee — and both are closed class.
    if head in FIRST_PERSON and _addressed_to_us(words) and _acting_verb_in(words, board):
        return DIRECTIVE_ACT

    # ⇒ 3b · THE EMBEDDED QUESTION UNDER A FIRST-PERSON MATRIX. *"i want to know WHICH vms are
    #   stopped"* is a declarative sentence containing an interrogative clause — no inversion,
    #   no initial wh, no question mark, and plainly asking. The speaker plus a subordinate
    #   wh-word is the whole signal, and both are closed classes.
    if head in FIRST_PERSON and any(w in WH_WORDS for w in words[1:]):
        return DIRECTIVE_INFORM

    # ⇒⇒ 3c · **THE EMBEDDED QUESTION UNDER AN IMPERATIVE — THE FALSE SERVE THIS CLOSES.**
    #   *"show me the vms"* has no wh-word, no inversion and no mark. It is an imperative, and
    #   before this rule it read as an ORDER and would have been carried out. What marks it is
    #   the RECIPIENT: the speaker is being handed something, and nothing in a lab can be
    #   handed to a person except information.
    #   ⇒ POSITION MATTERS — the recipient is the verb's FIRST argument. *"give THEM the fleet
    #     label"* has a recipient too and it is not the speaker, so it stays an act.
    if len(words) > 1 and words[1] in RECIPIENT:
        return DIRECTIVE_INFORM

    # ⇒ 3d · AND THE EMBEDDED POLAR QUESTION — *"check whether alpha is running"*. `whether`
    #   introduces one and does nothing else in English, so its presence anywhere settles it.
    if any(w in WHETHER for w in words):
        return DIRECTIVE_INFORM

    # ⇒⇒ 4 · THE ACHIEVE MOOD IS A DIRECTIVE, and `linguistics.mood_of` already reads it.
    #   *"make sure n1, n2 and n3 can all ping each other"* names no kind at all — every noun
    #   in it is a bare name only the lab can identify — so every test below reads it as
    #   nothing. Asking for a STATE to hold is asking for the lab to change, which is the one
    #   thing `mood_of` exists to say. Reusing it keeps one owner for that question rather than
    #   a second opinion about the same words.
    #   ⇒ AFTER the wh test, deliberately: *"how do i make sure exactly 3 vms carry 'prod'?"* is
    #     ACHIEVE and is a QUESTION, and the wh-word is what says so.
    from .linguistics import ACHIEVE, mood_of
    if mood_of(clause) == ACHIEVE:
        return DIRECTIVE_ACT

    # ⇒ 5 · THE IMPERATIVE, when the manifest knows the verb. What the operation DOES decides
    #   whether this acts, asks, or is about the conversation — `list the vms` vs `stop the vms`.
    if changes_the_world(head, board) is not None:
        return _imperative(words, board, world)

    # ⇒⇒ 5b · **THE MARK, AND ONLY NOW THAT EVERY ORDER-SHAPE HAS HAD ITS TURN.** This is where
    #   the rising declarative, the tag, the echo and the fragment all land:
    #
    #       alpha is running?                 declarative — intonation in speech, the mark in text
    #       alpha is running, isn't it?       tag — a declarative plus an inverted tag
    #       you deleted what?                 echo — the wh stays in situ, so position says nothing
    #       and the network?                  elliptical — no verb at all to read
    #
    #   ⇒ **A `?` IS NOT THE SIGNAL FOR A QUESTION; IT IS THE SIGNAL FOR *NOTHING ELSE FIRED*.**
    #     *"can you delete the vms?"* carries one and is an order — which is exactly why this
    #     test sits at position 5b and not position 1. Every shape that can be an order has
    #     already been read by the time we get here, so what is left with a mark on it is
    #     asking. Placement is the rule; the mark is only what remains.
    #   ⇒ AND IT COSTS NOTHING ON THE CORPUS: no literal or filler arm sentence ends in a mark,
    #     so this cannot turn an order into a question on the ladder.
    if _asks_outright(clause):
        return DIRECTIVE_INFORM

    # ⇒ 6 · A PREDICATION IS TEACHING — *"n1 is the jumpbox"*. The MAIN clause's copula, which
    #   means no relativizer may precede it: *"launch every vm THAT IS currently stopped"* is an
    #   order whose copula belongs to a subordinate clause, and rule 5 has already claimed it.
    if _main_clause_copula(words):
        return ASSERTIVE

    # ⇒ 7 · AND WHAT PRODUCES NOTHING IS EXPRESSIVE — no list required, which is the producer
    #   method paying for itself. A greeting holds no manifest verb, no manifest kind and no
    #   name the lab knows, so `hi` / `yo` / `cheers` never has to be enumerated.
    if not _any_manifest_verb(words, board) and not names_something(words, board, world):
        return EXPRESSIVE

    # ⇒⇒ 8 · AN IMPERATIVE THE MANIFEST HAS NO VERB FOR. English imperatives carry NO SUBJECT,
    #   so a clause opening on something that is not a function word is one — and `put`, `ping`,
    #   `take`, `give` are ordinary English the lab performs under other names. The test is the
    #   COMPLEMENT of the closed classes, never a verb list, so nothing has to be enumerated and
    #   nothing rots.
    if not _is_function_word(head):
        return _imperative(words, board, world)

    return None


# ── WHAT SHAPE OF ANSWER THE QUESTION ASKED FOR ──────────────────────────────────────
COUNT, MEMBERS = "count", "members"

# ⇒ THE WH-WORD NAMES THE ANSWER, and this is the second job the closed class does. `which`
#   asks for the members; `how many` asks for a number. Same nine words, read for a different
#   question — no new vocabulary, and no way for the two readings to drift apart.
_MEMBER_WORDS = frozenset({"which", "what", "who", "whom", "whose", "where"})


def answer_shape(clause: str, board: Optional[Board] = None) -> Optional[str]:
    """COUNT, MEMBERS, or None when no select can answer this at all.

    ⇒⇒ **A QUESTION READ IS NOT A QUESTION ANSWERED.** Every asked goal was `shape: count`, so
      *"which vms are running"* would have come back **3** — a number, to a question that asked
      for a list. Read correctly, routed correctly, and answered with the wrong kind of thing.

    ⇒ **NONE IS THE IMPORTANT VALUE AND IT IS NOT A FAILURE.** *"how do i create a vm?"* — the
      whole `asked` arm — wants a PROCEDURE, and neither a count nor a list is that. Emitting a
      count for it would be answering a different question confidently, which is worse than
      saying nothing: `answer_not_act` already has the honest branch for it (*"there is no
      answerable form of it to offer instead"*), and it can only reach that branch if this
      declines.

    ⇒ **AND A POLAR QUESTION IS A COUNT.** *"is alpha running?"* is answered by whether the
      select has any members, which is what a count says. No new shape is needed for yes/no.
    """
    words = _after_openers(words_of(clause))
    if not words:
        return None
    for i, w in enumerate(words):
        if w == "how" and i + 1 < len(words) and words[i + 1] in ("many", "much"):
            return COUNT
    if any(w in _MEMBER_WORDS for w in words):
        return MEMBERS
    # ⇒ A BARE `how` / `why` / `when` ASKS FOR A PROCEDURE, A REASON OR A TIME. No select
    #   answers any of those, so the honest answer is that we have none.
    if any(w in WH_WORDS for w in words):
        return None
    # ⇒ AN INFORMATIONAL IMPERATIVE ASKS FOR THE MEMBERS — `list the vms`, `show me the vms`.
    #   It named a set and no quantity, which is the same thing `which` does.
    if changes_the_world(words[0], board) is False or (
            len(words) > 1 and words[1] in RECIPIENT):
        return MEMBERS
    return COUNT                           # polar: has this select any members, yes or no


# ⇒ THE PERSONAL PRONOUNS THAT CAN BE A CLAUSE'S SUBJECT. Closed, and the whole of the
#   subordinate-wh test below.
SUBJECT_PRONOUNS = frozenset({"i", "you", "we", "he", "she", "it", "they"})


def _subordinate_wh(words: Sequence[str], clause: str) -> bool:
    """Is this wh-word opening a SUBORDINATE clause rather than asking a question?

    ⇒⇒ **`when you get a chance` IS NOT A QUESTION ABOUT WHEN.** It is a temporal adjunct, and
      it is one of the `filler` arm's four courtesy openers — so reading it as interrogative
      turned three polite ORDERS into questions. [[gorgon-courtesy-escalates-intent]] is the
      same shape one harm earlier: a pleasantry deciding what the sentence is FOR.

    ⇒ **THE DISCRIMINATOR IS INVERSION, WHICH IS WHAT ENGLISH ACTUALLY USES.** A main-clause
      wh-question either inverts its auxiliary over the subject, or the wh-phrase IS the
      subject. A subordinate wh does neither — it runs straight into subject-then-verb:

          when DID you stop it?          inverted            -> asking
          how DO i create a vm?          inverted            -> asking
          how many vms are there         wh-phrase IS the subject -> asking
          when YOU get a chance          subject, no inversion    -> an adjunct

    ⇒ AND A QUESTION MARK OVERRIDES IT, because a fragment may invert nothing at all —
      *"what about db?"* has no verb to invert.

    ⇒ ⚠ **THIS WAS MASKED UNTIL 2026-08-15.** `get` looked like an acting verb (`get_vm_logs`
      was miscategorised, see `effects.askers`), so the clause hit the addressee-order branch
      and came out an ORDER — the right answer for the wrong reason. Fixing `askers` removed
      the accident and the latent bug surfaced, which is what a corrected lookup is for.
    """
    if _asks_outright(clause):
        return False
    return len(words) > 1 and words[1] in SUBJECT_PRONOUNS


def _asks_outright(clause: str) -> bool:
    """Does the written clause carry a question mark?

    ⇒ THE ONLY TRACE INTONATION LEAVES IN TEXT. A rising declarative and a falling one are the
      same string otherwise, so where the mark is absent those two are genuinely undecidable
      from form — which is a fact about writing, not a gap in the reader.
    """
    return str(clause).strip().endswith("?")


def _has_predicate(words: Sequence[str], board: Optional[Board] = None) -> bool:
    """Is there anything in this clause that PREDICATES — a copula, an auxiliary, or a verb?

    Used to separate the exclamative (*"what a mess"*) from the question (*"what is the mess"*).
    An exclamative has a wh-word and no predicate at all; every interrogative has one, or a
    question mark standing in for the elided one.
    """
    return any(w in COPULA or w in AUXILIARIES for w in words) \
        or _any_manifest_verb(words, board) or _lab_predicate_in(words, board)


def _is_determiner(word: str) -> bool:
    """The determiner classes, read from `scan` rather than re-listed — one owner."""
    from .scan import DEFINITE, INDEFINITE, NOVEL, UNIVERSAL
    return (word in DEFINITE or word in INDEFINITE or word in UNIVERSAL
            or word in NOVEL or word.isdigit())


def _is_function_word(word: str) -> bool:
    """Closed-class membership — the complement is what an imperative may open on."""
    from .scan import DEFINITE, INDEFINITE, NOVEL, UNIVERSAL
    return (word in WH_WORDS or word in AUXILIARIES or word in PRONOUNS
            or word in PREPOSITIONS or word in CONJUNCTIONS or word in OPENERS
            or word in NEGATORS or word in DEFINITE or word in INDEFINITE
            or word in UNIVERSAL or word in NOVEL or word.isdigit())


def _main_clause_copula(words: Sequence[str]) -> bool:
    """Is there a copula that belongs to THIS clause rather than to one inside it?"""
    for i, w in enumerate(words[1:], start=1):
        if w in RELATIVIZERS:
            return False                   # everything after this belongs to the subordinate
        if w in COPULA:
            return True
    return False


def _imperative(words: Sequence[str], board: Optional[Board] = None,
                world=None) -> Optional[str]:
    """An imperative's own three-way split: report, act, or talk about the conversation."""
    negated = any(w in NEGATORS for w in words)
    words = [w for w in words if w not in NEGATORS]
    if not words:
        return None
    changes = changes_the_world(words[0], board)
    if changes is False:
        return DIRECTIVE_INFORM            # "list the vms" — the operation cannot touch anything
    # ⇒⇒ **A MANIFEST VERB WITH NO ARGUMENT AT ALL IS ADDRESSED TO US.** Bare `stop` shouted at
    #   the agent, versus `stop the vms`. The object's ABSENCE is the whole signal, and absence
    #   is only readable when there is nothing there — not when there is something we failed to
    #   recognise, which is the distinction the next paragraph exists for.
    if changes and len(words) == 1:
        return META_CONTROL
    # ⇒ AN INSTRUCTION THAT NAMES NOTHING THE LAB KEEPS IS ABOUT THE CONVERSATION. Bare `stop`
    #   addressed to the agent, and `don't start any changes` where `changes` is not a kind.
    #   ⇒ **THE OBJECT IS THE DISCRIMINATOR, AND IT IS THE ONLY ONE THAT WORKS.** `stop` is a
    #     manifest verb in both *"stop the vms"* and a bare *"stop"* shouted at the agent; no
    #     property of the VERB separates them, which is why the research named the object.
    # ⇒ AND A VERB THE MANIFEST DOES NOT KNOW STILL ACTS WHEN IT NAMES SOMETHING THE LAB KEEPS.
    #   `put every vm on a network`, `ping every vm`, `take a snapshot` — ordinary English for
    #   operations the manifest spells `add_vm_to_network`, `guest_ping`, `snapshot_create`.
    #   Translating those words is pass 2's job, not this file's; all this says is that an
    #   instruction was given.
    if names_something(words[1:], board, world):
        return DIRECTIVE_ACT
    # ⇒⇒ **AN ACTING VERB THE LAB HAS IS AN ORDER, WHATEVER IT NAMES.** This branch read
    #   *"create a grubnash named alpha"* as a CONVERSATION CONTROL, because `grubnash` is not
    #   a kind the manifest knows — so `consume_meta_control` dropped the row, the operator's
    #   answer *"a grubnash is a vm"* had nothing left to bind to, and a request that should
    #   have become a program stayed REFUSED. Caught by `test_write_back`, which is exactly
    #   the case it was written for.
    #
    #   ⇒ **AN UNKNOWN NOUN IS NOT AN ABSENT ONE** ([[gorgon-unfamiliar-nouns]]: *the verb half
    #     dissolves, the noun half does not*). `create` is the lab's own verb and something was
    #     named; that the lab cannot yet type the word is a question for gate 2, not grounds
    #     for deciding the sentence was never about the lab.
    if changes:
        return DIRECTIVE_ACT
    # ⇒ AN INSTRUCTION THAT NAMES NOTHING THE LAB KEEPS **AND IS NEGATED** IS ABOUT THE
    #   CONVERSATION — *"don't start any changes"*, where `start` names no operation and
    #   `changes` is not a kind. The negation is load-bearing: without it this claimed every
    #   imperative built on a verb the manifest happens not to spell.
    if negated:
        return META_CONTROL
    # ⇒ AND OTHERWISE NOTHING SETTLES IT. `treat prod as read-only` lands here — a DECLARATION,
    #   which has no rule yet and must not be guessed at as an order.
    return None


def _strip_imperative_frame(words: Sequence[str]) -> List[str]:
    """Drop the leading auxiliary of a negative imperative — `do not stop` -> `not stop`.

    ⇒⇒ **THE NEGATOR STAYS, AND IT USED TO GO.** `_imperative` reads the negation to tell a
      conversation control from an order (*"don't start any changes"* vs *"create a grubnash
      named alpha"*), and this stripped it one call earlier — so that test always saw an
      unnegated clause and every negative imperative fell to unsettled. A signal removed by
      the function that prepares the input for the function that needs it.
    """
    out = list(words)
    while out and out[0] in AUXILIARIES:
        out = out[1:]
    return out


def _inverted_subject(words: Sequence[str]) -> Optional[str]:
    """The subject an inverted auxiliary jumped over, or None when there is not one.

    ⇒ NEGATORS AND ADVERBS ARE SKIPPED, because *"can you please delete"* and *"did the
      snapshot really finish"* invert exactly as their bare forms do. A negator with NO subject
      after it is the negative imperative, and returning None is what routes it there.
    """
    negated = False
    for w in words[1:]:
        if w in NEGATORS:
            negated = True
            continue
        if w in OPENERS:
            continue
        # ⇒⇒ **AFTER A NEGATED AUXILIARY, A SUBJECT IS A PRONOUN OR A DETERMINER — OR THERE IS
        #   NO SUBJECT AND THIS IS A PROHIBITION.** The first version asked *"is the next word a
        #   verb?"* and answered it from the lab's vocabulary, so any verb the manifest does not
        #   know came back as a SUBJECT:
        #
        #       don't do anything yet     `do` is an auxiliary  -> read as a QUESTION
        #       don't touch the lab       `touch` is unknown    -> read as a QUESTION
        #
        #   Both are instructions not to act, read as requests for information. Asking what a
        #   word IS needs an open-class lexicon; asking what it IS NOT needs two closed ones.
        if negated and not (w in SUBJECT_PRONOUNS or _is_determiner(w)):
            return None                    # "do not touch …" — an imperative, not a question
        # ⇒⇒ **A VERB WHERE THE SUBJECT SHOULD BE MEANS THERE IS NO SUBJECT** — `do not START
        #   any changes` is a negative imperative, not a question about `start`. Without this
        #   the auxiliary rule read the operator's own *"don't start any changes"* as a
        #   QUESTION, which is the reading that makes the whole `framed` arm meaningless.
        #   ⇒ THE LAB'S OWN ENGLISH COUNTS, not only the manifest's spelling: `start` names no
        #     operation and is plainly a verb, and it is the operator's actual wording in
        #     *"don't start any changes"*. Same vocabulary the scope test reads.
        if not _is_function_word(w) and (changes_the_world(w) is not None
                                         or _lab_predicate_in([w])):
            return None
        return w
    return None


def _addressed_to_us(words: Sequence[str]) -> bool:
    return any(w in ADDRESSEE for w in words)


def _any_manifest_verb(words: Sequence[str], board: Optional[Board] = None) -> bool:
    from .linguistics import manifest_verbs
    return bool(set(words) & manifest_verbs(board))


def _acting_verb_in(words: Sequence[str], board: Optional[Board] = None) -> bool:
    """Does any word name an operation that CHANGES the world? Used by the two order-shapes."""
    return any(changes_the_world(w, board) for w in words)


# ── the sentence ─────────────────────────────────────────────────────────────────────
ORDER, QUESTION, NEITHER = "order", "question", "neither"


def clauses(request: str) -> List[str]:
    """The request's clauses — PASS 2's splitter, not a second one.

    A private splitter here would be the twin-owner defect again, and `clauses_of` already
    carries the member-list rule (*"n1, n2 and n3"* is one clause, not three) that took a
    recorded bug to get right.
    """
    from .pass2 import clauses_of
    return [c for c in clauses_of(request) if c and c.strip()]


def governs(clause: str, board: Optional[Board] = None) -> bool:
    """Does this wh-question take the REST OF THE SENTENCE as its complement?

    ⇒⇒ **THE CLAUSE SPLIT CUTS A QUESTION IN HALF, AND ORDER-WINS THEN EATS IT.** *"how do i
      create a vm named beta and then launch it?"* splits into a question and an imperative, and
      the imperative half decided the sentence — 7/14 on both question arms, every miss a FALSE
      SERVE on a sentence that never asked for anything.

    ⇒ **THE DISCRIMINATOR IS WHAT THE WH-CLAUSE'S OWN PREDICATE IS.**

          how do i CREATE a vm …          asks HOW TO ACT — the act is inside the question,
                                          and everything after it continues the act
          how many vms ARE there, and     a COMPLETE question over a copula; what follows is
          stop the stopped ones           a second speech act and a real order

      An acting verb inside the wh-clause is the signal, and it is the same `actors` lookup the
      rest of this file uses. The `asked` frames are exactly this shape — *how do i {goal}*,
      *what's the way to {goal}* — because a goal IS an act.

    ⚠ AND IT IS SCOPE, NOT A VERDICT: this says the following clauses BELONG to the question,
      never what to do about it.
    """
    words = _after_openers(words_of(clause))
    if not words or words[0] not in WH_WORDS or _subordinate_wh(words, clause):
        return False
    return _acting_verb_in(words, board) or _lab_predicate_in(words, board)


def _lab_predicate_in(words: Sequence[str], board: Optional[Board] = None) -> bool:
    """Does this clause hold a word the lab's own English uses for DOING something?

    ⇒⇒ **RUNG 13 IS RUNG 4 WITH `take` FOR `create`, AND THAT ONE WORD WAS THE LAST MISS.**
      `take a snapshot` and `put them on a network` are how the operator says
      `snapshot_create` and `add_vm_to_network`; the manifest's spelling is not the operator's,
      and a scope test that only knows manifest spellings misses every rung phrased in English.

    ⇒ **`scan._operation_words` IS THAT VOCABULARY AND IS ALREADY LOAD-BEARING** — it is what
      pass 1 reads a request's verbs with. Reused rather than copied, so the two cannot drift.
    ⇒ ⚠ **AND ITS NOUNS ARE SUBTRACTED, because it holds `vms`, `label`, `networks` too.** The
      manifest's own index says which of its entries are things rather than doings, so the
      subtraction is a lookup and not a hand-kept exception list. Without it *"how many VMS are
      there"* would look like a question about an act and swallow the clause after it.
    """
    from .scan import _index, _operation_words
    board = board or Board()
    doings = _operation_words(board) - set(_index(board))
    return any(w in doings and w not in COPULA for w in words)


def read(request: str, board: Optional[Board] = None,
         world=None) -> List[Tuple[str, Optional[str]]]:
    """Every clause of the request paired with its speech act — WITH THE QUESTION'S SCOPE.

    A governing wh-clause pulls everything after it into the question, because that is what
    subordination does. Without it the second half of *"how do i create a vm and launch it?"*
    is read as an order nobody gave.
    """
    out: List[Tuple[str, Optional[str]]] = []
    governed = False
    for c in clauses(request):
        if governed:
            out.append((c, DIRECTIVE_INFORM))
            continue
        act = act_of(c, board, world)
        out.append((c, act))
        if act == DIRECTIVE_INFORM and governs(c, board):
            governed = True
    return out


def verdict(request: str, board: Optional[Board] = None, world=None) -> str:
    """ORDER, QUESTION or NEITHER for the whole request — the OPERATIVE clause decides.

    ⇒⇒ **AN ORDER ANYWHERE MAKES IT AN ORDER**, and the asymmetry is why: a sentence carrying
      one clause that asks the lab to change is a sentence that changes the lab, and reading it
      as a question would be a false serve wearing a question's clothes. A false avoid costs a
      question ([[gorgon-vague-request-ladder]]).

    ⇒ **AND THIS ROUTES NOTHING TODAY.** It is computed and reported; what the pipeline does
      with it is the operator's call, deliberately not taken here.
    """
    acts = [a for _, a in read(request, board, world)]
    if DIRECTIVE_ACT in acts:
        return ORDER
    if DIRECTIVE_INFORM in acts:
        return QUESTION
    return NEITHER
