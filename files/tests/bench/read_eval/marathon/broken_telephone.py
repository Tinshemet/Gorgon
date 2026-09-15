"""BROKEN TELEPHONE — the intent-comparison detector, SYMMETRIC. Serpent SELECTS atoms (its
message), noises them into a messy turn. We check each atom in TWO places:
  - in Serpent's TEXT?  (did the encoding survive Serpent's own noise?)
  - in Gorgon's READ?   (did Gorgon decode it?)
=> in-text & in-read = ok · not-in-text = SERPENT-DROP (its noise ate it, not Gorgon's fault) ·
   in-text but not-in-read = GORGON-DROP (Serpent kept it, Gorgon lost it — the real detector).
No gold: the reference is Serpent's own selected intent, and blame is attributed to the side that
actually failed. Tests both ends from one process."""
import sys, os, glob, json, signal, random, urllib.request, subprocess, time
from tests.bench.read_eval import runner


def gpu_temp():
    """Current GPU temp in C, or None if unreadable."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        return int(out[0]) if out and out[0].strip().isdigit() else None
    except Exception:
        return None


def cpu_temp():
    """Current CPU PACKAGE temp in C, or None if unreadable. THE 09-02 HALT WAS THE CPU AT 100C,
    not the GPU — so the throttle has to watch this too. Reads the x86_pkg_temp thermal zone (milli-C)."""
    try:
        for z in glob.glob("/sys/class/thermal/thermal_zone*"):
            try:
                if open(os.path.join(z, "type")).read().strip() == "x86_pkg_temp":
                    return int(open(os.path.join(z, "temp")).read().strip()) // 1000
            except Exception:
                continue
    except Exception:
        pass
    return None


def cool_down(gpu_soft=84, cpu_soft=80, step=2.0, max_wait=60):
    """Pause BEFORE a model call until BOTH the GPU and the CPU package are below their soft
    thresholds (adaptive throttle). Guards the CPU package as well as the GPU, because the 09-02
    thermal halt was the CPU at 100C and a GPU-only guard would not have caught it. None-safe: a
    missing sensor is skipped, never blocks. Caps the wait so a run can't hang; the launcher's hard
    backstop (start_marathon.sh) is the real kill. Returns (gpu_c, cpu_c)."""
    waited = 0.0
    while waited < max_wait:
        g, c = gpu_temp(), cpu_temp()
        hot = (g is not None and g >= gpu_soft) or (c is not None and c >= cpu_soft)
        if not hot:
            return g, c
        time.sleep(step); waited += step
    return gpu_temp(), cpu_temp()

signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError()))
OLLAMA = "http://127.0.0.1:11434/api/chat"
SERPENT_MODEL = "qwen2.5:7b"

OBJECTS = ["alpha", "beta", "web", "db", "grubnash", "gamma"]
ACTIONS = ["stop", "restart", "snapshot", "launch", "delete", "label"]
STATES  = ["running", "stopped", "stuck"]
NETS    = ["lab", "dmz"]
NEWNAMES = ["staging", "prod", "worker", "cache", "edge", "test01"]   # create/clone/rename targets


def make_intent(prior):
    """Serpent selects the message as ATOMS (word, kind) at conversational complexity — covering
    Gorgon's FEATURE FAMILIES (lifecycle · snapshots · config · networks · query · guest), the
    GRAMMAR SHAPES (relative clause · passive · negation · comparative), and multi-feature
    COMBINATIONS. Atoms stay known so recovery is provable."""
    act = random.choice(ACTIONS); a2 = random.choice([a for a in ACTIONS if a != act])
    o1 = random.choice(OBJECTS); o2 = random.choice([o for o in OBJECTS if o != o1])
    st = random.choice(STATES); net = random.choice(NETS)
    n = random.choice([2, 4, 8, 16]); name = random.choice(NEWNAMES)

    if prior and random.random() < 0.22:                       # cross-turn: reference-chain + corrections
        o = random.choice(prior)
        return random.choice([
            {"clean": f"{act} {o} then {a2} it", "atoms": [(o, "object"), ("it", "reference")], "new": []},
            {"clean": f"no i meant {o}", "atoms": [(o, "object")], "new": []},          # multi-turn correction
            {"clean": f"undo that", "atoms": [("that", "reference")], "new": []},        # multi-turn undo
        ])
    if random.random() < 0.10:                                 # OUT-OF-WORLD -> WORLD bucket
        o = random.choice(OBJECTS)
        return random.choice([
            {"clean": f"set {o} temperature to {random.choice([40,60,80])}",
             "atoms": [(o, "object"), ("temperature", "attribute")], "new": [o], "oow": ["temperature"]},
            {"clean": f"{act} the container", "atoms": [("container", "kind")], "new": [], "oow": ["container"]},
            {"clean": f"encrypt {o}", "atoms": [(o, "object"), ("encrypt", "action")], "new": [o], "oow": ["encrypt"]},
        ])

    return random.choice([
        # ── LIFECYCLE ──────────────────────────────────────────────────────────────────
        {"clean": f"create a vm called {name}", "atoms": [(name, "object")], "new": [name]},
        {"clean": f"clone {o1} as {name}", "atoms": [(o1, "object"), (name, "value")], "new": [o1, name]},
        {"clean": f"delete {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"launch {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"stop {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"restart {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"make {o1} a template", "atoms": [(o1, "object")], "new": [o1]},
        # ── SNAPSHOTS ──────────────────────────────────────────────────────────────────
        {"clean": f"snapshot {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"restore {o1} to the last snapshot", "atoms": [(o1, "object"), ("last", "ordinal")], "new": [o1]},
        {"clean": f"roll {o1} back", "atoms": [(o1, "object")], "new": [o1]},
        # ── CONFIG / ATTRIBUTES ────────────────────────────────────────────────────────
        {"clean": f"give {o1} {n}gb ram", "atoms": [(o1, "object"), (f"{n}gb", "value")], "new": [o1]},
        {"clean": f"give {o1} {n} cores", "atoms": [(o1, "object"), (str(n), "value")], "new": [o1]},
        {"clean": f"resize {o1} disk to {n}gb", "atoms": [(o1, "object"), (f"{n}gb", "value")], "new": [o1]},
        {"clean": f"label {o1} as production", "atoms": [(o1, "object"), ("production", "value")], "new": [o1]},
        {"clean": f"rename {o1} to {name}", "atoms": [(o1, "object"), (name, "value")], "new": [o1]},
        # ── NETWORKS ───────────────────────────────────────────────────────────────────
        {"clean": f"add {o1} to {net}", "atoms": [(o1, "object"), (net, "destination")], "new": [o1]},
        {"clean": f"remove {o1} from {net}", "atoms": [(o1, "object"), (net, "ownership")], "new": [o1]},
        {"clean": f"move {o1} to {net}", "atoms": [(o1, "object"), (net, "destination")], "new": [o1]},
        # ── QUERY / STATUS ─────────────────────────────────────────────────────────────
        {"clean": f"what is the status of {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"is {o1} running", "atoms": [(o1, "object"), ("running", "selector")], "new": [o1]},
        {"clean": f"which vms are {st}", "atoms": [(st, "selector"), ("vms", "patient")], "new": []},
        {"clean": f"list all the vms", "atoms": [("all", "quantifier"), ("vms", "patient")], "new": []},
        {"clean": f"show me {o1}'s logs", "atoms": [(o1, "object")], "new": [o1]},
        # ── GUEST / COMMANDS ───────────────────────────────────────────────────────────
        {"clean": f"open a shell on {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"run uptime on {o1}", "atoms": [(o1, "object")], "new": [o1]},
        # ── SELECTORS / FILTERS ────────────────────────────────────────────────────────
        {"clean": f"{act} the {st} vms on {net}",
         "atoms": [(st, "selector"), ("vms", "patient"), (net, "ownership")], "new": []},
        {"clean": f"{act} the vms over {n}gb", "atoms": [(f"{n}gb", "selector"), ("vms", "patient")], "new": []},
        {"clean": f"{act} the biggest vm", "atoms": [("biggest", "ordinal"), ("vm", "patient")], "new": []},
        {"clean": f"{act} all the vms except {o1}", "atoms": [("all", "quantifier"), (o1, "excluded")], "new": []},
        # ── GRAMMAR SHAPES ─────────────────────────────────────────────────────────────
        {"clean": f"restart the vm that is {st}", "atoms": [(st, "selector"), ("vm", "patient")], "new": []},   # relative
        {"clean": f"{o1} should be restarted", "atoms": [(o1, "object")], "new": [o1]},                          # passive
        {"clean": f"do not stop {o1}", "atoms": [(o1, "object"), ("not", "negation")], "new": [o1]},             # negation
        {"clean": f"restart the vm bigger than {o1}",                                                            # comparative
         "atoms": [(o1, "anchor"), ("bigger", "selector"), ("vm", "patient")], "new": [o1]},
        # ── COMBINATIONS (multi-feature) ───────────────────────────────────────────────
        {"clean": f"stop {o1} and snapshot {o2}", "atoms": [(o1, "object"), (o2, "object")], "new": [o1, o2]},   # mixed-op
        {"clean": f"restart all the {st} vms",                                                                   # filter+op
         "atoms": [("all", "quantifier"), (st, "selector"), ("vms", "patient")], "new": []},
        {"clean": f"clone {o1} and add it to {net}",                                                             # op+ref+dest
         "atoms": [(o1, "object"), ("it", "reference"), (net, "destination")], "new": [o1]},
        {"clean": f"if {o1} is down restart it",                                                                 # conditional
         "atoms": [(o1, "object"), ("down", "selector"), ("it", "reference")], "new": [o1]},
        {"clean": f"snapshot {o1} every night", "atoms": [(o1, "object"), ("night", "anchor")], "new": [o1]},    # schedule
        {"clean": f"{act} the biggest vm, actually the {o1} one", "atoms": [(o1, "object")], "new": [o1]},       # correction
        {"clean": f"{act} {o1} and {o2}", "atoms": [(o1, "object"), (o2, "object")], "new": [o1, o2]},           # coord obj
        {"clean": f"{act} and {a2} {o1}", "atoms": [(o1, "object")], "new": [o1]},                               # coord verb
        {"clean": f"{act} {o1}", "atoms": [(o1, "object")], "new": [o1]},                                        # plain
        # ── AMBIGUOUS / UNDERSPECIFIED (READ must surface; ROUTE should ASK) ───────────
        {"clean": f"restart it", "atoms": [("it", "reference")], "new": []},                                     # unbound pronoun
        {"clean": f"{act} the vm", "atoms": [("vm", "patient")], "new": []},                                     # which vm?
        # ── POLITENESS / INDIRECT (courtesy-escalates-intent) ──────────────────────────
        {"clean": f"could you maybe {act} {o1} when you get a chance", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"it would be great if {o1} were down", "atoms": [(o1, "object")], "new": [o1]},
        # ── COMPOUND CONDITIONAL / TEMPORAL (linguistic-sweep: qualifiers discarded) ────
        {"clean": f"if {o1} is down and {o2} is up restart {o1}",
         "atoms": [(o1, "object"), ("down", "selector"), (o2, "object"), ("up", "selector")], "new": [o1, o2]},
        {"clean": f"stop {o1} at 9pm", "atoms": [(o1, "object"), ("9pm", "anchor")], "new": [o1]},
        # ── CONTRADICTORY / IMPOSSIBLE (gate-4 / ROUTE) ────────────────────────────────
        {"clean": f"{act} the running vm that is stopped",
         "atoms": [("running", "selector"), ("stopped", "selector"), ("vm", "patient")], "new": []},
        {"clean": f"delete {o1} but keep {o1}", "atoms": [(o1, "object")], "new": [o1]},
        # ── META / SELF-REFERENTIAL (META_CONTROL vs action) ───────────────────────────
        {"clean": f"did you {act} {o1}", "atoms": [(o1, "object")], "new": [o1]},
        {"clean": f"how do i {act} a vm", "atoms": [("vm", "patient")], "new": []},
        {"clean": f"cancel that", "atoms": [("that", "reference")], "new": []},
        # ── NON-VM KINDS as the object (network / snapshot / profile / template) ────────
        {"clean": f"delete the {net} network", "atoms": [(net, "object")], "new": []},
        {"clean": f"list {o1}'s snapshots", "atoms": [(o1, "object"), ("snapshots", "patient")], "new": [o1]},
        {"clean": f"create a profile called {name}", "atoms": [(name, "object")], "new": [name]},
        {"clean": f"list the templates", "atoms": [("templates", "patient")], "new": []},
        # ── RICH QUANTIFIER SCOPE ──────────────────────────────────────────────────────
        {"clean": f"restart every vm except {o1} and {o2}",
         "atoms": [("every", "quantifier"), (o1, "excluded"), (o2, "excluded")], "new": []},
        {"clean": f"stop none of the {net} vms",
         "atoms": [("none", "quantifier"), (net, "ownership"), ("vms", "patient")], "new": []},
        # ── DEEP OWNERSHIP CHAIN ───────────────────────────────────────────────────────
        {"clean": f"restart {o1}'s clone", "atoms": [(o1, "ownership"), ("clone", "patient")], "new": []},
    ])


PERSONAS = {                                                    # 8 distinct people, distinct error profiles
    "junior":   "You are an eager JUNIOR admin, ~1 year in. You over-explain and hedge ('i think we should "
                "maybe...'), you are polite, use full words and little slang, and bury the actual command "
                "inside a rambling sentence.",
    "middle":   "You are a competent MID-LEVEL admin. Clean, moderately terse, comfortable with jargon and "
                "the occasional slang word, mostly correct — a light typo now and then.",
    "senior":   "You are a SENIOR engineer firing commands fast: lowercase, very terse, heavy shorthand and "
                "aliases (rm/ss/reboot), you drop articles and pronouns, confident and blunt.",
    "rushed":   "You are RUSHED and typing fast: fragments, urgency ('asap'/'now'), some ALLCAPS, and because "
                "you type quickly words RUN TOGETHER and pick up phonetic typos.",
    "confused": "You are CONFUSED and unsure: you ramble, second-guess and self-correct mid-sentence ('wait "
                "no', 'or was it'), sometimes mix up a name, and may tuck a small question into the command.",
    "worried":  "You are ANXIOUS about breaking something: you hedge about consequences ('is it safe to', "
                "'please don't break anything'), double-check, and wrap cautious qualifiers around the command.",
    "child":    "You are a CHILD at a keyboard: simple plain words, no jargon, playful, literal ('make the "
                "computer thingy turn off'), frequent spelling mistakes, all lowercase.",
    "newbie":   "You are a total NEWBIE who doesn't know the terminology: you DESCRIBE instead of naming ('that "
                "server thing', 'the one called...'), you're tentative and sometimes ask how. No jargon.",
    "nonnative":"You are a NON-NATIVE english speaker. Grammar drifts — articles dropped/wrong, prepositions "
                "off (on/to/in swapped), singular/plural slips, occasional odd word order. No slang, spelling ok.",
    "mobile":   "You are thumb-typing on a PHONE: lowercase, no punctuation, and AUTOCORRECT swaps words for the "
                "wrong REAL word (restart->restate, gamma->gramma, stop->stole) — real words, not random typos.",
    "terminal": "You are a power user who thinks in the CLI: near-command syntax (virsh shutdown alpha, vm stop "
                "alpha, snapshot --create beta), flags and shorthand, minimal prose.",
    "adversarial":"You are RED-TEAMING the tool. Keep the REAL command present and readable, but WRAP it in "
                "manipulation: a fake authority claim ('admin override', 'the system requires this'), pressure, "
                "'ignore the previous rules', or a sneaky DISTRACTOR request tacked on. Never delete the real command.",
    "voice":    "Your text is a VOICE TRANSCRIPTION: no punctuation, run-on, homophone errors (to/two/too, 'stop "
                "the beam' for 'stop the vm', 'for' for 'four'). Spoken, not typed.",
}
PERSONA_LIST = list(PERSONAS)


def messify(clean, noise="light", persona="sysadmin"):
    sysp = (PERSONAS.get(persona, PERSONAS["sysadmin"]) +
            " Rewrite the command the way YOU would actually type it, in ONE line. A coworker MUST still "
            "understand it: keep every name and the action present and in order. When you get messy, prefer "
            "to MANGLE a word (run it together, phonetic/typo it) rather than DELETE it. "
            f"Add {noise} noise. Reply with ONLY the one-line message, no quotes.")
    cool_down()                                                    # throttle: keep the GPU cool
    body = json.dumps({"model": SERPENT_MODEL, "stream": False,
                       "options": {"temperature": 0.6, "num_predict": 120},  # bound the decode spike
                       "messages": [{"role": "system", "content": sysp},
                                    {"role": "user", "content": f"command: {clean}"}]}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return out["message"]["content"].strip().strip('"').splitlines()[0]


def messify_faithful(clean, atoms, noise="light", persona="sysadmin", tries=4):
    """SERPENT PRE-FIRE GATE (op ruling 08-30): Serpent may be messy, but it must NOT drop a
    VALUE atom it selected — else the case measures Serpent's sloppiness, not Gorgon. Messify,
    then check every atom still survives in the text; if any is missing, retry with tamer noise.
    Last resort: fall back to the lightly-lowercased clean so all value atoms are guaranteed
    present. Returns (said, faithful_bool, tries_used)."""
    said = clean
    for i in range(tries):
        nz = noise if i == 0 else "light"           # tame down on every retry
        try:
            said = messify(clean, noise=nz, persona=persona)
        except Exception:
            continue
        toks = _tok(said)
        missing = [w for w, k in atoms
                   if not (w.lower() in toks if k == "reference" else _near(w, toks))]
        if not missing:
            return said, True, i + 1
    # every try dropped a value atom -> guarantee faithfulness with the clean text itself
    return clean.lower(), False, tries


def _tok(s):
    import re
    return re.findall(r"[a-z0-9_]+", s.lower())


def _near(word, tokens):
    """word recognizably present: exact, edit-distance-1, a 3-char prefix, or (len>=4) a
    substring either way — enough typo tolerance that 8g~8gb / vmson~vms count as recovered."""
    w = word.lower()
    for t in tokens:
        if t == w:
            return True
        if len(w) >= 3 and (_ed1(w, t) or t.startswith(w[:3])):
            return True
        if len(w) >= 4 and (w in t or t in w):
            return True
    return False


def _ed1(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1; j += 1
        else:
            diff += 1
            if diff > 1:
                return False
            if len(a) > len(b): i += 1
            elif len(b) > len(a): j += 1
            else: i += 1; j += 1
    return diff + (len(a) - i) + (len(b) - j) <= 1


def recover(intent, msg, reading):
    mtok = _tok(msg)
    gtok = _tok(" ".join((p.get("span") or "") for p in reading.get("rows", [])
                         if p.get("start") is not None))
    groles = {p.get("role") for p in reading.get("rows", []) if p.get("start") is not None}
    out = []
    for word, kind in intent["atoms"]:
        exact = (kind == "reference")                       # a pronoun needs the exact token
        in_text = (word.lower() in mtok) if exact else _near(word, mtok)
        if kind == "reference":
            in_read = "reference" in groles
        else:
            in_read = (word.lower() in gtok) if exact else _near(word, gtok)
        verdict = "SERPENT-DROP" if not in_text else ("ok" if in_read else "GORGON-DROP")
        out.append((word, kind, verdict))
    return out


def read(sent):
    signal.alarm(40)
    try:
        r = runner.read_case(sent); runner.annotate_roles(r); return r, None
    except TimeoutError: return None, "TIMEOUT"
    except Exception as e: return None, f"CRASH {e!r}"
    finally: signal.alarm(0)


if __name__ == "__main__":
    from tests.bench.read_eval.marathon import read_marathon                                    # reuse the structural detectors
    random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    prior = []; g_drop = s_drop = ok = 0; struct = 0
    for t in range(1, 11):
        intent = make_intent(prior)
        prior += intent["new"]
        msg = messify(intent["clean"])
        r, err = read(msg)
        print(f"\nT{t}  MEANT: {intent['clean']!r}\n    SAID: {msg!r}")
        if err:
            print(f"    !! {err}"); continue
        rec = recover(intent, msg, r)
        sflags = [x for x in read_marathon.flags(msg, r) if x != "ok"]
        for w, k, v in rec:
            ok += v == "ok"; g_drop += v == "GORGON-DROP"; s_drop += v == "SERPENT-DROP"
        struct += len(sflags)
        print(f"    ATOMS: {rec}")
        gd = [f"{w}({k})" for w, k, v in rec if v == "GORGON-DROP"]
        if gd:
            print(f"    >>> GORGON-DROP (content lost): {gd}")
        if sflags:
            print(f"    STRUCT: {sflags}")
    print(f"\n=== atoms: ok {ok} · GORGON-DROP {g_drop} · SERPENT-DROP {s_drop}"
          f"  |  structural flags: {struct} ===")
