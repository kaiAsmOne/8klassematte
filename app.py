"""Mattelab 8 - Flask app. Run: python app.py  (http://127.0.0.1:5000)"""
from __future__ import annotations

import os
import random
from datetime import date

from flask import Flask, abort, jsonify, render_template, request
from itsdangerous import BadSignature, URLSafeSerializer

from engine import scheduler
from engine.answers import check
from engine.curriculum import SKILLS, public_curriculum
from engine.examples import example_for

app = Flask(__name__)
signer = URLSafeSerializer(os.environ.get("MATTELAB_SECRET", "dev-only-change-me"), salt="problem")


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


def _token(data) -> dict:
    try:
        return signer.loads(data.get("token", ""))
    except BadSignature:
        abort(400)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/curriculum")
def curriculum():
    return jsonify(public_curriculum())


@app.post("/api/next")
def next_problem():
    data = _body()
    progress = scheduler.clean(data.get("progress"))
    skill_id = data.get("skill")
    if skill_id is not None and skill_id not in SKILLS:
        abort(404)
    want = data.get("want") if data.get("want") in scheduler.CHOOSABLE else None
    rng = random.Random()
    pick = scheduler.choose(progress, skill_id, date.today(), rng, want)
    if pick is None:
        return jsonify({"empty": True, "progress": progress})
    sid, level, mode = pick
    skill = SKILLS[sid]
    problem = skill.gen(level, rng).to_dict()
    problem["example"] = example_for(skill, level, problem["expr"], rng)
    token = signer.dumps({
        "skill": sid, "level": level, "mode": mode,
        "asks": [s["ask"] for s in problem["steps"]],
        "final": problem["final"],
    })
    return jsonify({
        "token": token, "skill": sid, "skill_title": skill.title, "topic": skill.topic,
        "level": level, "level_name": skill.levels[level - 1], "levels": len(skill.levels),
        "mode": mode, "requested": skill_id, "problem": problem,
        "pref": progress["skills"].get(sid, {}).get("pref"), "progress": progress,
    })


@app.post("/api/switch")
def switch_mode():
    """Pupil asks for more help on the problem in front of them: same problem, new mode.

    The problem does not count toward mastery (the pupil saw help), so a switched
    solo attempt is never recorded as a miss either.
    """
    data = _body()
    tok = _token(data)
    want = data.get("want")
    if want not in ("worked", "guided"):
        abort(400)
    progress = scheduler.clean(data.get("progress"))
    scheduler.set_pref(progress, tok["skill"], want)
    tok["mode"] = want
    tok["switched"] = True
    return jsonify({"token": signer.dumps(tok), "mode": want, "progress": progress,
                    "pref": progress["skills"][tok["skill"]]["pref"]})


@app.post("/api/check")
def check_answer():
    data = _body()
    tok = _token(data)
    step = data.get("step")
    spec = tok["final"] if step == "final" else None
    if spec is None and isinstance(step, int) and 0 <= step < len(tok["asks"]):
        spec = tok["asks"][step]
    if spec is None:
        abort(400)
    return jsonify(check(spec, str(data.get("answer", ""))[:80]))


@app.post("/api/record")
def record():
    data = _body()
    tok = _token(data)
    progress = scheduler.clean(data.get("progress"))
    if tok.get("switched"):
        return jsonify({"progress": progress, "events": []})
    events = scheduler.record(progress, tok["skill"], tok["level"], tok["mode"],
                              bool(data.get("correct")), date.today())
    return jsonify({"progress": progress, "events": events})


if __name__ == "__main__":
    app.run(debug=True)
