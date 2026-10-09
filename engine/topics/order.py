"""Regnerekkefølge: parenteser, potenser, ganging/deling, pluss/minus."""
from __future__ import annotations

import random

from ..core import MINUS, Problem, Skill, Step, ask, n_, p_

OPS = {"+": lambda a, b: a + b, MINUS: lambda a, b: a - b,
       "·": lambda a, b: a * b, ":": lambda a, b: a // b, "^": lambda a, b: a ** b}
LEVELS = [("^",), ("·", ":"), ("+", MINUS)]
RUNG = {"^": 1, "·": 2, ":": 2, "+": 3, MINUS: 3}


class Bad(Exception):
    pass


def _apply(op, a, b):
    if op == ":" and (b == 0 or a % b):
        raise Bad
    if op == "^" and (b < 1 or b > 4 or abs(a) > 12):
        raise Bad
    return OPS[op](a, b)


def _unwrap(t):
    """Remove parentheses around a single number."""
    i = 0
    while i < len(t) - 2:
        if t[i] == "(" and isinstance(t[i + 1], int) and t[i + 2] == ")":
            t = t[:i] + [t[i + 1]] + t[i + 3:]
            i = 0
        else:
            i += 1
    return t


def _next(t):
    """Index of the operator to evaluate next, and whether it is inside parentheses."""
    if ")" in t:
        close = t.index(")")
        lo = max(i for i in range(close) if t[i] == "(") + 1
        hi, inside = close, True
    else:
        lo, hi, inside = 0, len(t), False
    for group in LEVELS:
        for i in range(lo, hi):
            if t[i] in group:
                return i, inside, [t[k] for k in range(lo, hi) if k != i and t[k] in group]
    raise Bad


def show(t, hl=None) -> str:
    out = []
    for k, x in enumerate(t):
        s = p_(x) if isinstance(x, int) and k > 0 and t[k - 1] not in ("(",) else (n_(x) if isinstance(x, int) else x)
        if hl and k == hl[0]:
            s = "[[" + s
        if hl and k == hl[1]:
            s = s + "]]"
        out.append(s)
    txt = " ".join(out)
    return txt.replace("( ", "(").replace(" )", ")").replace(" ^ ", "^")


def reduce(tokens):
    """Yield (before, (lo, hi), op, a, b, value, rule, after) for each step."""
    t = _unwrap(list(tokens))
    steps = []
    while len(t) > 1:
        i, inside, same = _next(t)
        op, a, b = t[i], t[i - 1], t[i + 1]
        v = _apply(op, a, b)
        if inside:
            rule = "Regn ut parentesen først."
        elif op == "^":
            rule = "Potenser regnes ut før ganging, deling, pluss og minus."
        elif op in ("·", ":"):
            rule = "Ganging og deling kommer før pluss og minus."
        else:
            rule = "Nå er bare pluss og minus igjen."
        if same and not inside and op != "^":
            rule += " Like regnearter tas fra venstre mot høyre."
        after = _unwrap(t[:i - 1] + [v] + t[i + 2:])
        steps.append((t, (i - 1, i + 1), op, a, b, v, rule, after))
        t = after
    return steps, t[0]


def naive(tokens):
    """Typical mistake: straight left to right, ignoring precedence (parentheses still first)."""
    t = _unwrap(list(tokens))
    while ")" in t:
        close = t.index(")")
        op_ = max(i for i in range(close) if t[i] == "(")
        inner = t[op_ + 1:close]
        v = inner[0]
        for k in range(1, len(inner), 2):
            v = _apply(inner[k], v, inner[k + 1])
        t = _unwrap(t[:op_] + [v] + t[close + 1:])
    v = t[0]
    for k in range(1, len(t), 2):
        v = _apply(t[k], v, t[k + 1])
    return v


def _random_tokens(level, rng):
    n_nums = {1: 3, 2: 4, 3: 4}[level]
    nums = [rng.randint(2, 12) for _ in range(n_nums)]
    ops = [rng.choice(["+", MINUS, "·", ":"]) for _ in range(n_nums - 1)]
    if level == 3:
        k = rng.randrange(n_nums - 1)
        ops[k] = "^"
        nums[k] = rng.randint(2, 5)
        nums[k + 1] = rng.randint(2, 3)
    t = []
    for k, x in enumerate(nums):
        t.append(x)
        if k < len(ops):
            t.append(ops[k])
    if level >= 2 and rng.random() < 0.85:
        starts = [k for k in range(0, len(t) - 2, 2) if t[k + 1] in ("+", MINUS)]
        if starts:
            s = rng.choice(starts)
            t = t[:s] + ["("] + t[s:s + 3] + [")"] + t[s + 3:]
    return t


def gen_order(level: int, rng: random.Random) -> Problem:
    for _ in range(5000):
        t = _random_tokens(level, rng)
        try:
            steps, val = reduce(t)
            wrong = naive(t)
        except Bad:
            continue
        values = [s[5] for s in steps]
        if level < 3 and min(values) < 0:
            continue
        if max(abs(v) for v in values) > 300:
            continue
        ops = [x for x in t if x in OPS]
        if not any(o in ("·", ":", "^") for o in ops) or not any(o in ("+", MINUS) for o in ops):
            continue
        if wrong == val:
            continue
        break
    else:
        raise RuntimeError("fant ingen oppgave")

    out = []
    for k, (before, (lo, hi), op, a, b, v, rule, after) in enumerate(steps):
        lo_, hi_ = lo, hi
        if lo > 0 and before[lo - 1] == "(" and hi + 1 < len(before) and before[hi + 1] == ")":
            lo_, hi_ = lo - 1, hi + 1
        prefix = "" if k == 0 else "= "
        sym = "^" if op == "^" else f" {op} "
        out.append(Step(
            say=rule,
            math=prefix + show(before, (lo_, hi_)),
            show={"type": "ladder", "active": 0 if "parentesen" in rule else RUNG[op]},
            ask=ask(f"{p_(a)}{sym}{p_(b)} = ?", "int", v),
        ))
    out.append(Step(say="Ferdig!", math=f"= {n_(val)}", show={"type": "ladder", "active": None}))
    return Problem(
        task="Regn ut. Følg regnerekkefølgen.",
        expr=show(t),
        steps=out,
        final=ask("Svar", "int", val,
                  [(wrong, "Du regnet fra venstre mot høyre. Ganging og deling skal gjøres før pluss og minus.")]),
        start={"type": "ladder", "active": None},
        work=[show(t)] + [show(s[7]) for s in steps],
    )


SKILLS = [
    Skill("order", "rekkefolge", "Regnerekkefølge",
          "Hva regner vi først? Følg stigen.",
          ["Fire regnearter", "Med parenteser", "Med potenser"], gen_order,
          ["parentes", "prioritet"]),
]
