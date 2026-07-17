#!/usr/bin/env python3
"""runner.py — walk-away sequencer over Claude Code BUILT-INS.

All cognition is built-in Claude Code functionality invoked headlessly
(planning, implementation, /code-review --fix, /simplify). This script only:
sequences fresh sessions, reads GIT STATE, runs the manifest's checks, and
stops. It never parses model prose for control flow.

Pipeline:
  plan      one session reads the design doc, decides its own task breakdown,
            writes specs/ + tasks.json (the only structural demand we place),
            commits.
  per task  fresh implement session -> /code-review <effort> --fix
            (mechanical churn rule: pass leaves tree dirty = findings existed;
            runner commits them and reviews again; a 2nd dirty pass =
            churning -> revert task, re-implement fresh at the escalate
            model; churn again -> HALT) -> /simplify -> runner re-runs the
            task's checks itself (red = revert the simplify commit, note it,
            continue) -> next task.
  closure   run every task's checks, then one whole-diff report-only review.

Stop semantics: any session failure, timeout, or post-escalation churn halts
the run (exit 1) with state on the ledger; re-running skips completed tasks
(derived from the ledger) and starts each task from a clean tree.

Usage:
  python3 runner.py --repo ~/repos/eaitl-nocode --plan design-draft.md --yes
  python3 runner.py --repo ... --skip-plan --yes        # manifest already exists
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

IMPLEMENT_PROMPT = (
    "Implement {spec} exactly. It is self-contained; do not re-decide anything "
    "it pins. Run its checks ({checks}), fix until green, then commit ALL "
    "changes (git add -A && git commit). Work not committed does not exist."
)
PLAN_PROMPT = (
    "Read {plan}. Plan how to build it: break the work into however many "
    "ordered, dependency-respecting tasks you judge right. "
    "First, conventions: if a root CLAUDE.md already exists, treat its rules as "
    "binding and do not overwrite it. Otherwise decide the project-wide "
    "engineering conventions this build should hold to (language/runtime, "
    "dependency policy, type-checking, test framework and layout, style) — "
    "derive them from the design doc plus sound engineering defaults — and "
    "write them to a root CLAUDE.md as concrete, quotable rules. Either way, "
    "this file is loaded into every later session and is the surface the review "
    "pass enforces against, so a convention that lives only in a task spec will "
    "NOT be enforced — the enforceable rules must be in CLAUDE.md. "
    "For each task write "
    "a self-contained spec under specs/ (a fresh session must be able to "
    "implement from the spec alone: exact module paths, signatures, consumed "
    "interfaces of prior tasks re-stated, error model, a worked example with "
    "exact expected values). Then write tasks.json: an ordered JSON array of "
    '{{"id": "<kebab-id>", "spec": "specs/<file>.md", "checks": ["<shell '
    'command>", ...]}} — checks are commands with exit codes, runnable from '
    "the repo root. Ask no questions; make reasonable calls and record them "
    "in the specs. Commit everything when done."
)


def sh(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def head(repo):
    return sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def dirty(repo):
    return bool(sh(["git", "status", "--porcelain"], repo).stdout.strip())


def commit_all(repo, msg):
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-q", "-m", msg], repo)


def reset_clean(repo, ref="HEAD"):
    """The one spelling of 'discard everything back to ref'."""
    sh(["git", "reset", "--hard", ref, "-q"], repo)
    sh(["git", "clean", "-fdq"], repo)


class Halt(Exception):
    pass


class Runner:
    def __init__(self, args):
        self.repo = os.path.abspath(os.path.expanduser(args.repo))
        self.args = args
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.rundir = os.path.join(self.repo, ".runner", ts)
        os.makedirs(self.rundir, exist_ok=True)
        self.ledger_path = os.path.join(self.repo, ".runner", "ledger.jsonl")

    def ledger(self, record):
        record["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
            fh.flush()
            os.fsync(fh.fileno())  # resume-correctness rides on the last record

    def done_tasks(self):
        done = set()
        if os.path.exists(self.ledger_path):
            for line in open(self.ledger_path, encoding="utf-8"):
                r = json.loads(line)
                if r.get("stage") == "task-done":
                    done.add(r["task"])
        return done

    def claude(self, label, prompt, model, effort):
        """One fresh headless session. Only exit code and git state are used
        for control flow; the full JSON result (incl. usage) is archived.
        Effort travels as the launcher-verified --effort flag; auto-memory is
        off so 'fresh session' means fresh; the session runs in its own
        process group so a timeout kills its subagents too."""
        out = os.path.join(self.rundir, f"{label}.json")
        env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
        argv = ["claude", "-p", prompt, "--output-format", "json",
                "--model", model, "--effort", effort]
        print(f"    session {label} ({model}@{effort})", flush=True)
        proc = subprocess.Popen(argv, cwd=self.repo, text=True, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=self.args.timeout_s)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), 9)
            proc.wait()
            self.ledger({"stage": "session-timeout", "label": label})
            raise Halt(f"session {label} timed out ({self.args.timeout_s}s)")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(stdout or "")
            if stderr:
                fh.write("\n--- stderr ---\n" + stderr)
        if proc.returncode != 0:
            self.ledger({"stage": "session-failed", "label": label,
                         "exit": proc.returncode})
            raise Halt(f"session {label} exited {proc.returncode} (see {out})")

    def run_checks(self, checks):
        for cmd in checks:
            r = subprocess.run(cmd, shell=True, cwd=self.repo,
                               capture_output=True, text=True, timeout=600,
                               stdin=subprocess.DEVNULL)
            if r.returncode != 0:
                return cmd, (r.stdout + r.stderr)[-800:]
        return None, None

    def commit_dirty(self, msg):
        """Commit whatever a session left uncommitted; True if anything was."""
        if dirty(self.repo):
            commit_all(self.repo, msg)
            return True
        return False

    def review_fix_cycle(self, task, tier_label, review_range):
        """/code-review --fix passes until one leaves the tree clean.
        True = still churning after the pass budget (the escalation signal)."""
        for n in range(1, self.args.max_review_passes + 1):
            self.claude(f"{task['id']}-review-{tier_label}-{n}",
                        f"/code-review {self.args.review_effort} --fix {review_range}",
                        self.args.review_model, self.args.review_effort)
            if not dirty(self.repo):
                return False
            commit_all(self.repo, f"review-fix pass {n} ({task['id']})")
        return True

    def build_task(self, task):
        pre = head(self.repo)
        reset_clean(self.repo)
        rng = f"{pre}...HEAD"
        impl_prompt = IMPLEMENT_PROMPT.format(spec=task["spec"],
                                              checks="; ".join(task["checks"]))

        # One attempt loop over escalation tiers — the guards exist once, so
        # the tiers cannot drift apart.
        tiers = [("t1", self.args.implement_model, self.args.implement_effort),
                 ("t2", self.args.escalate_model, self.args.escalate_effort)]
        escalated = False
        for i, (label, model, effort) in enumerate(tiers):
            if i:
                escalated = True
                self.ledger({"stage": "escalate", "task": task["id"],
                             "reason": "review still applying fixes after "
                                       f"{self.args.max_review_passes} passes"})
                reset_clean(self.repo, pre)
            self.claude(f"{task['id']}-implement-{label}", impl_prompt,
                        model, effort)
            committed = self.commit_dirty(
                f"implement ({task['id']}) [runner-committed leftovers]")
            if head(self.repo) == pre and not committed:
                raise Halt(f"{task['id']}: implement session produced no commit")
            if not self.review_fix_cycle(task, label, rng):
                break
        else:
            raise Halt(f"{task['id']}: still churning after escalation — "
                       "operator judgment needed")

        # Gate before spending the simplify session (closure's own fail-fast
        # pattern): a red tree here is a contract breach, not simplify's job.
        failed, tail = self.run_checks(task["checks"])
        if failed:
            raise Halt(f"{task['id']}: checks red before simplify: {failed}\n{tail}")

        pre_simplify = head(self.repo)
        self.claude(f"{task['id']}-simplify", f"/simplify {rng}",
                    self.args.review_model, self.args.review_effort)
        self.commit_dirty(f"simplify ({task['id']})")
        failed, tail = self.run_checks(task["checks"])
        simplify_reverted = False
        if failed:
            reset_clean(self.repo, pre_simplify)
            simplify_reverted = True
            failed, tail = self.run_checks(task["checks"])
        if failed:
            raise Halt(f"{task['id']}: checks red after build: {failed}\n{tail}")

        self.ledger({"stage": "task-done", "task": task["id"],
                     "escalated": escalated,
                     "simplify_reverted": simplify_reverted,
                     "sha": head(self.repo)})
        print(f"  == {task['id']} done (escalated={escalated})", flush=True)

    def run(self):
        manifest = os.path.join(self.repo, "tasks.json")
        if not self.args.skip_plan and not os.path.exists(manifest):
            base = head(self.repo)
            self.claude("plan", PLAN_PROMPT.format(plan=self.args.plan),
                        self.args.escalate_model, self.args.escalate_effort)
            self.commit_dirty("plan: specs + task manifest")
            self.ledger({"stage": "planned", "base": base, "sha": head(self.repo)})
        tasks = json.load(open(manifest, encoding="utf-8"))
        for t in tasks:
            if not (t.get("id") and t.get("spec") and t.get("checks")):
                raise Halt(f"manifest entry malformed: {t}")
            if not os.path.exists(os.path.join(self.repo, t["spec"])):
                raise Halt(f"manifest spec missing: {t['spec']}")

        done = self.done_tasks()
        chain_base = head(self.repo)
        for t in tasks:
            if t["id"] in done:
                print(f"  == skip (done): {t['id']}", flush=True)
                continue
            print(f"=== task: {t['id']}", flush=True)
            self.build_task(t)

        seen = set()
        for t in tasks:
            fresh = [c for c in t["checks"] if c not in seen]
            seen.update(fresh)
            failed, tail = self.run_checks(fresh)
            if failed:
                raise Halt(f"closure: {t['id']} checks red: {failed}\n{tail}")
        self.claude("closure-review",
                    f"/code-review {self.args.review_effort} {chain_base}...HEAD",
                    self.args.review_model, self.args.review_effort)
        self.ledger({"stage": "closure", "sha": head(self.repo)})
        print("RUN COMPLETE — all tasks built, checks green, closure review "
              f"archived under {self.rundir}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--plan", default="design-draft.md")
    ap.add_argument("--skip-plan", action="store_true")
    ap.add_argument("--implement-model", default="claude-sonnet-5")
    ap.add_argument("--implement-effort", default="xhigh")
    ap.add_argument("--review-model", default="claude-opus-4-8")
    ap.add_argument("--review-effort", default="xhigh")
    ap.add_argument("--escalate-model", default="claude-opus-4-8")
    ap.add_argument("--escalate-effort", default="xhigh")
    ap.add_argument("--max-review-passes", type=int, default=2)
    ap.add_argument("--timeout-s", type=int, default=3600)
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    if not args.yes:
        print("This SPENDS QUOTA: one planning session + ~3-5 sessions per "
              "task it plans. Re-run with --yes.", file=sys.stderr)
        return 2
    try:
        Runner(args).run()
        return 0
    except Halt as exc:
        print(f"HALT: {exc}", file=sys.stderr)
        print("State is on the ledger; re-running skips completed tasks.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
