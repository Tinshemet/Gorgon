#!/usr/bin/env bash
# start_marathon.sh — launch the Serpent marathon (freeze -> read), detached, resumable, with a HARD
# THERMAL BACKSTOP. The in-code cool_down() is the soft adaptive throttle (CPU>=88 / GPU>=83); THIS
# is the crit backstop that KILLS the run if the CPU package hits 96C or the GPU hits 90C — because
# the 09-02 halt was the CPU reaching 100C. Detached with setsid+nohup+disown so it survives the
# launching shell (a plain background job dies with its process group — learned the hard way).
#
# Usage:  bash tests/bench/read_eval/marathon/start_marathon.sh <N_TURNS> [seed]
#         (from the repo's files/ dir; N defaults to 2000)
# Resume: just run it again — freeze and read both skip ids already done in frozen.jsonl/results.jsonl.
# Watch:  tail -f <marathon dir>/marathon.log   (and watchdog.log)
# Stop:   kill -TERM -$(cat <marathon dir>/marathon.pgid)
set -u

MDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="$(cd "$MDIR/../../../.." && pwd)"          # repo files/ dir (PYTHONPATH root)
N="${1:-2000}"; SEED="${2:-20260829}"
CPU_CRIT=96; GPU_CRIT=90

cpu_pkg() { for z in /sys/class/thermal/thermal_zone*; do
    [ "$(cat "$z/type" 2>/dev/null)" = x86_pkg_temp ] && { echo $(( $(cat "$z/temp" 2>/dev/null)/1000 )); return; }
  done; echo 0; }
gpu_c()  { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc 0-9; }

prof="$(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo unknown)"
[ "$prof" = balanced ] || echo "WARN: platform_profile is '$prof', not 'balanced' (root-only to change) — fans may run hotter." >&2
echo "marathon: N=$N seed=$SEED  files=$FILES  cpu=$(cpu_pkg)C gpu=$(gpu_c)C profile=$prof"

# The work: freeze the ruler, then read it. Both are resumable. Its own process group so the
# watchdog can kill the whole tree with one signal.
run_work() {
  cd "$FILES" || exit 1
  export PYTHONPATH=.
  echo "=== FREEZE $(date -Is) ==="
  python3 -m tests.bench.read_eval.marathon.marathon_freeze "$N" "$SEED" || exit 1
  echo "=== READ $(date -Is) ==="
  python3 -m tests.bench.read_eval.marathon.marathon_read
  echo "=== DONE $(date -Is) ==="
}

# Detach the worker in its OWN session/process group; record the pgid for the watchdog + manual stop.
setsid nohup bash -c "$(declare -f run_work); run_work" >"$MDIR/marathon.log" 2>&1 &
WORK_PID=$!
disown
# setsid makes the worker a session/group leader (pgid==pid, verified) — but read the REAL pgid
#   rather than assume it, since this is the group the thermal backstop must kill on crit.
WORK_PGID="$(ps -o pgid= -p "$WORK_PID" 2>/dev/null | tr -d ' ')"; WORK_PGID="${WORK_PGID:-$WORK_PID}"
echo "$WORK_PGID" > "$MDIR/marathon.pgid"

# The HARD BACKSTOP watchdog: poll temps; kill the whole run group on crit; exit when the run ends.
watchdog() {
  while kill -0 "$WORK_PID" 2>/dev/null; do
    c=$(cpu_pkg); g=$(gpu_c); g=${g:-0}
    if [ "$c" -ge "$CPU_CRIT" ] || [ "$g" -ge "$GPU_CRIT" ]; then
      echo "$(date -Is) BACKSTOP TRIPPED cpu=${c}C gpu=${g}C -> killing run group $WORK_PGID"
      kill -TERM -"$WORK_PGID" 2>/dev/null; sleep 5; kill -9 -"$WORK_PGID" 2>/dev/null
      exit 1
    fi
    sleep 5
  done
  echo "$(date -Is) run ended; watchdog exiting (last cpu=$(cpu_pkg)C gpu=$(gpu_c)C)"
}
setsid nohup bash -c "WORK_PID=$WORK_PID WORK_PGID=$WORK_PGID CPU_CRIT=$CPU_CRIT GPU_CRIT=$GPU_CRIT
  $(declare -f cpu_pkg gpu_c watchdog); watchdog" >"$MDIR/watchdog.log" 2>&1 &
disown

echo "launched: run pgid $WORK_PGID (log: $MDIR/marathon.log), watchdog armed (log: $MDIR/watchdog.log)"
echo "stop with:  kill -TERM -$WORK_PGID"
