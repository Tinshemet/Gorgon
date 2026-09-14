"""SERPENT — the marathon persona generator. A busy on-call sysadmin who carries out a real
task as a messy multi-turn conversation. Runs on an INDEPENDENT model (qwen2.5:7b, != READ's
llama3.1:8b) to avoid shared blind spots. Outputs the USER turns only — the marathon input.
See marathon_spec.md. Persona = Serpent (Gorgon/Medusa theme)."""
import json, sys, urllib.request

OLLAMA = "http://127.0.0.1:11434/api/chat"
SERPENT_MODEL = "qwen2.5:7b"

SYSTEM = """You are SERPENT, a busy on-call sysadmin running a small VM lab through a command
assistant — you TYPE, it ACTS (creates/stops/restarts/snapshots/deletes VMs, makes networks,
sets ram/cores/ip, labels, schedules, answers status questions).

Given a TASK, produce the sequence of messages YOU send the assistant to get it done — a REAL,
messy conversation the way a rushed admin actually types:
- lowercase, terse; shorthand (`db`, `the lab ones`, `2 cores`); slang (`nuke it`, `spin up`,
  `gimme`, `it's toast`, `kill it`)
- BACK-REFERENCES across turns — `that one`, `do it again`, `same as before`, `the first one`,
  `snapshot that`, `the ones from earlier`
- mid-stream CORRECTIONS — `actually no—`, `wait, make it the db instead`, `scratch that`
- the odd typo
- you have a GOAL; push turn by turn until it's done, then stop.

Rules: output ONLY your own messages, one per line, each starting with `U: `. NEVER write the
assistant's replies. NEVER explain or add commentary. 8 to 15 messages. Talk like a person, not a
form — and NEVER copy these examples verbatim, use your own words."""

# The 12 happy-path scenarios (marathon_spec §A), phrased as GOALS (not sentences), cross-turn noted.
SCENARIOS = {
 1: "Stand up a fresh environment: make a new network, spin up a few vms on it, name them, and give them some ram/cores. Refer back to the ones you just made as you go.",
 2: "Morning triage: ask what's not running, restart the dead ones, and if one still won't come up after that, flag it. Use 'that one'/'the same' across turns.",
 3: "Memory hunt: something's eating ram. Find the vms over a threshold, then stop the worst offender. Refer back to what you found.",
 4: "Pre-change backup: snapshot everything before a risky change, then clear out the snapshots older than a while to save space.",
 5: "Set up a nightly routine: have the db vm snapshot every night and the test vms stop at 9pm, then check it's set.",
 6: "Restart everything except alpha, then ask what changed. Then act on one of the changed ones.",
 7: "Tag the prod machines 'prod' and move them onto a locked-down network you create. Refer back to 'the prod ones'.",
 8: "Two machines are acting up — the one at an ip you give, and the one with a serial you give. Stop both, then snapshot them.",
 9: "Change your mind mid-task: restart the biggest vm... no wait, do the db one instead... then snapshot that.",
 10: "Teach the assistant a shorthand: tell it that when you say 'nightly' you mean snapshot all the vms and restart the lab ones — then use 'nightly'.",
 11: "Owner cleanup: delete alpha's old snapshots, and the lab vms' stale logs. Refer to them possessively.",
 12: "Escalating conditional: if the grubnash isn't up, restart it and the oldest vm; if that doesn't help, snapshot beta but not alpha and tell you which are still down.",
}


def serpent_turns(scenario_text, model=SERPENT_MODEL, temperature=0.9):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"TASK: {scenario_text}\n\nWrite your conversation now."}]
    body = json.dumps({"model": model, "messages": msgs, "stream": False,
                       "options": {"temperature": temperature}}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=180).read())
    text = out.get("message", {}).get("content", "")
    turns = [l.split(":", 1)[1].strip() for l in text.splitlines()
             if l.strip().lower().startswith("u:")]
    return turns, text


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"=== SCENARIO {n}: {SCENARIOS[n]}\n")
    turns, raw = serpent_turns(SCENARIOS[n])
    if not turns:
        print("NO 'U:' TURNS PARSED — raw output:\n", raw[:800]); sys.exit(1)
    for i, t in enumerate(turns, 1):
        print(f"  {i:2}. {t}")
    print(f"\n[{len(turns)} user turns]")
