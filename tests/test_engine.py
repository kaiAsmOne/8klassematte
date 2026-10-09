"""Run: python -m pytest -q   (or: python tests/test_engine.py)"""
import json
import random
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import scheduler
from engine.answers import check
from engine.core import dec_
from engine.curriculum import SKILLS


def as_text(spec):
    k, e = spec["kind"], spec["expect"]
    if k == "int":
        return str(e)
    if k == "num":
        return dec_(Fraction(e)).replace("\u00a0", "")
    if k in ("frac", "frac_simplest"):
        return f"{e[0]}/{e[1]}" if e[1] != 1 else str(e[0])
    if k == "factors":
        out, n, p = [], e, 2
        while n > 1:
            while n % p == 0:
                out.append(str(p))
                n //= p
            p += 1
        return "·".join(out)
    if k == "std":
        return f"{dec_(Fraction(e[0]))}·10^{e[1]}"
    if k == "sign":
        return e
    if k == "expr_n":
        a = e[1] - e[0]
        if e[2] - e[1] == a:
            return f"{a}n+{e[0] - a}"
        return f"n^2+{e[0] - 1}"
    raise AssertionError(k)


def test_all_generators():
    for sid, skill in SKILLS.items():
        for level in range(1, len(skill.levels) + 1):
            for seed in range(300):
                p = skill.gen(level, random.Random(seed)).to_dict()
                json.dumps(p)
                specs = [s["ask"] for s in p["steps"] if s["ask"]] + [p["final"]]
                for spec in specs:
                    r = check(spec, as_text(spec))
                    assert r["ok"], (sid, level, seed, spec, as_text(spec), r)
                if p["work"]:
                    chain = " = ".join(p["work"])
                    r = check(p["final"], chain)
                    assert r["ok"], (sid, level, seed, chain, r)


def test_answer_parsing():
    assert check({"kind": "frac", "expect": [3, 4], "traps": []}, "6/8")["ok"]
    assert not check({"kind": "frac_simplest", "expect": [3, 4], "traps": []}, "6/8")["ok"]
    assert check({"kind": "frac", "expect": [3, 2], "traps": []}, "1 1/2")["ok"]
    assert check({"kind": "factors", "expect": 60, "traps": []}, "2^2 · 3 · 5")["ok"]
    assert "ikke et primtall" in check({"kind": "factors", "expect": 60, "traps": []}, "4·3·5")["msg"]
    assert check({"kind": "std", "expect": ["4.5", 6], "traps": []}, "4,5*10^6")["ok"]
    assert not check({"kind": "std", "expect": ["4.5", 6], "traps": []}, "45·10^5")["ok"]
    assert check({"kind": "std", "expect": ["3.2", -4], "traps": []}, "3,2·10^−4")["ok"]
    assert check({"kind": "expr_n", "expect": [4, 7, 10, 13, 16, 19], "traps": []}, "3n + 1")["ok"]
    assert check({"kind": "expr_n", "expect": [4, 7, 10, 13, 16, 19], "traps": []}, "1+3·n")["ok"]
    assert check({"kind": "int", "expect": -81, "traps": []}, "−81")["ok"]
    assert check({"kind": "num", "expect": "4.5", "traps": []}, "4,5")["ok"]
    assert check({"kind": "expr_n", "expect": [1], "traps": []}, "__import__('os')")["invalid"]
    trap = {"kind": "frac", "expect": [5, 6], "traps": [{"v": [2, 5], "msg": "nevner"}]}
    assert check(trap, "2/5")["msg"] == "nevner"


def test_chains():
    spec = {"kind": "int", "expect": 123, "traps": [], "fmt": ""}
    assert check(spec, "16 + 23 + 84 = (16 + 84) + 23 = 123")["ok"]
    assert check(spec, "16 + 23 + 84 = (84 + 16) + 23 = 100 + 23 = 123")["ok"]
    r = check(spec, "16 + 23 + 84 = (16 + 83) + 23 = 123")
    assert not r["ok"] and "Likhetstegnet" in r["msg"]
    r = check(spec, "16 + 23 + 84 = 100 + 23 = 124")
    assert not r["ok"] and "ikke 124" in r["msg"]
    assert check(spec, "16 + 23 + 84 = 100 + 23")["invalid"]
    assert check({"kind": "factors", "expect": 60, "traps": []}, "60 = 2·30 = 2·2·15 = 2^2·3·5")["ok"]
    assert check({"kind": "frac_simplest", "expect": [1, 2], "traps": []}, "3/6 = (3:3)/(6:3) = 1/2")["ok"]
    assert check({"kind": "std", "expect": ["4.5", 6], "traps": []}, "4 500 000 = 4,5·10^6")["ok"]
    assert check({"kind": "int", "expect": 12, "traps": []}, "√144 = 12")["ok"]


def test_examples():
    from engine.examples import example_for
    for sid, skill in SKILLS.items():
        for level in range(1, len(skill.levels) + 1):
            ex = example_for(skill, level, "", random.Random(level))
            assert ex and ex["typed"], (sid, level)


def test_mastery_flow():
    prog = scheduler.clean({})
    today, rng = date(2026, 9, 29), random.Random(1)
    seen = []
    for _ in range(40):
        sid, lvl, mode = scheduler.choose(prog, "sqrt", today, rng)
        seen.append(mode)
        scheduler.record(prog, sid, lvl, mode, True, today)
    assert prog["skills"]["sqrt"]["mastered"]
    assert seen[:4] == ["worked", "guided", "guided", "solo"]


def test_pupil_choice():
    today, rng = date(2026, 9, 29), random.Random(2)
    prog = scheduler.clean({})
    sid, lvl, mode = scheduler.choose(prog, "regroup", today, rng, want="solo")
    assert mode == "solo" and prog["skills"]["regroup"]["pref"] == "solo"
    for ok in (True, True, True, True):
        scheduler.record(prog, sid, lvl, "solo", ok, today)
    st = prog["skills"]["regroup"]
    assert st["lvl"] == 2 and st["pref"] is None
    assert scheduler.choose(prog, "regroup", today, rng)[2] == "worked"

    scheduler.choose(prog, "regroup", today, rng, want="solo")
    scheduler.record(prog, "regroup", 2, "solo", False, today)
    ev = scheduler.record(prog, "regroup", 2, "solo", False, today)
    assert ev == ["step_back"]
    assert scheduler.choose(prog, "regroup", today, rng)[2] == "guided"
    scheduler.record(prog, "regroup", 2, "guided", True, today)
    assert scheduler.choose(prog, "regroup", today, rng)[2] == "solo"

    scheduler.choose(prog, "regroup", today, rng, want="guided")
    for _ in range(3):
        assert scheduler.choose(prog, "regroup", today, rng)[2] == "guided"
        scheduler.record(prog, "regroup", 2, "guided", True, today)

    assert scheduler.choose(prog, "regroup", today, rng, want="worked")[2] == "worked"
    scheduler.record(prog, "regroup", 2, "worked", True, today)
    assert scheduler.choose(prog, "regroup", today, rng)[2] == "guided"


if __name__ == "__main__":
    test_all_generators()
    test_answer_parsing()
    test_chains()
    test_examples()
    test_mastery_flow()
    test_pupil_choice()
    print("ok")
