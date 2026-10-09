"""Chooses what to practise next and updates progress.

Learning design:
  1. worked  - first time on a level: watch a fully worked example.
  2. guided  - solve two problems step by step with support (faded guidance).
  3. solo    - answer on your own. 4 of the last 5 correct unlocks the next level.
               Two misses in a row sends you back to one guided problem.
  Pupil choice: at any time the pupil can pick "Vis meg" (worked, one problem),
  "Hjelp meg" (guided) or "Jeg prøver selv" (solo). Guided and solo stick as the
  skill's `pref` until changed, a level is passed, or two solo misses in a row
  force one guided problem (`force`). Chosen solo counts toward mastery as usual.
  4. review  - mastered skills come back after 1, 3, 7, 14 and 30 days
               (spaced repetition), and are mixed into other practice
               (interleaving) about one time in four.

Progress lives in the browser and is sent with every request, so the
server stays stateless. Everything here is plain dict/list/int so it
survives the JSON round trip.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from .curriculum import SKILLS

INTERVALS = [0, 1, 3, 7, 14, 30]
MASTERY_WINDOW, MASTERY_NEEDED, GUIDED_NEEDED = 5, 4, 2
INTERLEAVE = 0.25
CHOOSABLE = ("worked", "guided", "solo")


def blank() -> dict:
    return {"lvl": 1, "worked": [], "guided": 0, "hist": [], "mastered": False, "box": 0, "due": None,
            "pref": None, "force": 0}


def clean(progress) -> dict:
    """Accept whatever the browser sends; keep only what we understand."""
    out = {"skills": {}, "solved": 0}
    if not isinstance(progress, dict):
        return out
    out["solved"] = int(progress.get("solved", 0) or 0)
    for sid, st in (progress.get("skills") or {}).items():
        if sid not in SKILLS or not isinstance(st, dict):
            continue
        s = blank()
        s["lvl"] = max(1, min(int(st.get("lvl", 1)), len(SKILLS[sid].levels)))
        s["worked"] = [int(x) for x in st.get("worked", []) if isinstance(x, int)]
        s["guided"] = int(st.get("guided", 0))
        s["hist"] = [bool(x) for x in st.get("hist", [])][-MASTERY_WINDOW:]
        s["mastered"] = bool(st.get("mastered", False))
        s["box"] = max(0, min(int(st.get("box", 0)), len(INTERVALS) - 1))
        s["due"] = st.get("due") if isinstance(st.get("due"), str) else None
        s["pref"] = st.get("pref") if st.get("pref") in ("guided", "solo") else None
        s["force"] = max(0, min(int(st.get("force", 0) or 0), 2))
        out["skills"][sid] = s
    return out


def due_reviews(progress: dict, today: date, exclude: str | None = None) -> list[str]:
    iso = today.isoformat()
    return [sid for sid, st in progress["skills"].items()
            if st["mastered"] and sid != exclude and (st["due"] or "") <= iso]


def set_pref(progress: dict, skill_id: str, want: str) -> None:
    """Record the pupil's own choice.

    guided/solo stick. worked is a one-off, followed by one guided problem,
    the same order as the default path.
    """
    st = progress["skills"].setdefault(skill_id, blank())
    st["force"] = 1 if want == "worked" else 0
    if want in ("guided", "solo"):
        st["pref"] = want


def mode_for(st: dict) -> str:
    if st["force"] > 0 and not st["mastered"]:
        return "guided"
    if st["pref"] == "guided":
        return "guided"
    if st["mastered"]:
        return "review"
    if st["pref"] == "solo":
        return "solo"
    if st["lvl"] not in st["worked"]:
        return "worked"
    if st["guided"] < GUIDED_NEEDED:
        return "guided"
    return "solo"


def choose(progress: dict, skill_id: str | None, today: date, rng: random.Random, want: str | None = None):
    """Returns (skill_id, level, mode) or None if there is nothing to review.

    want: a mode the pupil picked for this skill ("worked", "guided", "solo").
    """
    skills = progress["skills"]
    if skill_id is None:
        due = due_reviews(progress, today)
        pool = due or [sid for sid, st in skills.items() if st["mastered"] or st["hist"]]
        if not pool:
            return None
        sid = rng.choice(pool)
        st = skills[sid]
        if st["mastered"]:
            return sid, rng.randint(1, len(SKILLS[sid].levels)), "review"
        return sid, st["lvl"], "solo"

    st = skills.setdefault(skill_id, blank())
    if want in CHOOSABLE:
        set_pref(progress, skill_id, want)
    mode = mode_for(st)
    if want == "worked":
        mode = "worked"
    if st["mastered"] and mode != "review":
        return skill_id, rng.randint(1, len(SKILLS[skill_id].levels)), mode
    if mode == "review":
        return skill_id, rng.randint(1, len(SKILLS[skill_id].levels)), "review"
    if mode == "solo" and want is None and rng.random() < INTERLEAVE:
        due = due_reviews(progress, today, exclude=skill_id)
        if due:
            other = rng.choice(due)
            return other, rng.randint(1, len(SKILLS[other].levels)), "review"
    return skill_id, st["lvl"], mode


def record(progress: dict, skill_id: str, level: int, mode: str, correct: bool, today: date) -> list[str]:
    """Update progress in place. Returns events for the browser to celebrate."""
    st = progress["skills"].setdefault(skill_id, blank())
    events = []
    if correct and mode != "worked":
        progress["solved"] += 1

    if mode == "review":
        st["box"] = min(st["box"] + 1, len(INTERVALS) - 1) if correct else 1
        st["due"] = (today + timedelta(days=INTERVALS[st["box"]])).isoformat()
        return events

    if level != st["lvl"]:
        return events

    if mode == "worked":
        if level not in st["worked"]:
            st["worked"].append(level)
    elif mode == "guided":
        st["force"] = max(0, st["force"] - 1)
        if correct:
            st["guided"] += 1
    elif mode == "solo":
        st["hist"] = (st["hist"] + [correct])[-MASTERY_WINDOW:]
        if sum(st["hist"]) >= MASTERY_NEEDED:
            if st["lvl"] < len(SKILLS[skill_id].levels):
                st["lvl"] += 1
                st["hist"], st["guided"] = [], 0
                st["pref"], st["force"] = None, 0
                events.append("level_up")
            else:
                st["mastered"], st["box"] = True, 1
                st["pref"], st["force"] = None, 0
                st["due"] = (today + timedelta(days=INTERVALS[1])).isoformat()
                events.append("mastered")
        elif st["hist"][-2:] == [False, False]:
            st["force"] = 1
            st["guided"] = max(st["guided"], GUIDED_NEEDED - 1)
            st["hist"] = st["hist"][:-1]
            events.append("step_back")
    return events
