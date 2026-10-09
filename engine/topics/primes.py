"""Primtall og primtallsfaktorisering med faktortre."""
from __future__ import annotations

import random

from ..core import Problem, Skill, Step, ask, power_form, prime_factors

POOLS = {1: [2, 3, 5, 7], 2: [2, 3, 5, 7, 11], 3: [2, 3, 5, 7, 11, 13]}
COUNT = {1: (3, 3), 2: (3, 4), 3: (4, 5)}
BOUNDS = {1: (12, 100), 2: (60, 300), 3: (150, 1500)}


def _reason(q: int, p: int) -> str:
    if p == 2:
        return f"Er {q} et partall? Da kan det deles på 2."
    if p == 3:
        s = sum(int(c) for c in str(q))
        return f"Tverrsummen av {q} er {s}. Går 3 opp i den, går 3 opp i {q}."
    if p == 5:
        return f"{q} slutter på 0 eller 5, så 5 går opp."
    return f"Verken 2, 3 eller 5 går opp i {q}. Prøv neste primtall: {p}."


def _tree(n: int, splits: list[tuple[int, int]], upto: int) -> dict:
    """Chain-shaped factor tree after `upto` splits."""
    root = {"v": n}
    node = root
    for p, q in splits[:upto]:
        node["c"] = [{"v": p, "prime": True}, {"v": q}]
        node = node["c"][1]
    if not splits[:upto] or upto == len(splits):
        node["prime"] = len(prime_factors(node["v"])) == 1
    return {"type": "tree", "root": root}


def gen_factor(level: int, rng: random.Random) -> Problem:
    lo, hi = BOUNDS[level]
    while True:
        k = rng.randint(*COUNT[level])
        fs = sorted(rng.choice(POOLS[level]) for _ in range(k))
        n = 1
        for f in fs:
            n *= f
        if lo <= n <= hi and len(set(fs)) >= 2:
            break

    splits, q = [], n
    for p in fs[:-1]:
        splits.append((p, q // p))
        q //= p

    steps, done = [], []
    q = n
    for i, (p, r) in enumerate(splits):
        done.append(p)
        steps.append(Step(
            say=_reason(q, p),
            math=f"{n} = " + " · ".join(str(x) for x in done) + f" · {r}",
            show=_tree(n, splits, i + 1),
            ask=ask(f"{q} : {p} = ?", "int", r,
                    [(q - p, "Det er minus. Vi skal dele.")] if q - p != r else None),
        ))
        q = r
    steps.append(Step(
        say=f"{q} er et primtall og kan ikke deles mer. Samle like faktorer som potenser.",
        math=f"{n} = {power_form(fs)}",
        show=_tree(n, splits, len(splits)),
    ))
    return Problem(
        task="Skriv tallet som et produkt av primtall.",
        expr=f"{n} = ?",
        steps=steps,
        final=ask("Primtallsfaktorer", "factors", n),
        work=[str(n)] + [" · ".join(map(str, fs[:i + 1])) + f" · {r}" for i, (_, r) in enumerate(splits)]
             + ([power_form(fs)] if len(set(fs)) < len(fs) else []),
        start={"type": "tree", "root": {"v": n}},
    )


SKILLS = [
    Skill("factor", "primtall", "Primtallsfaktorisering",
          "Del opp tall i primtall med et faktortre.",
          ["Opptil 100", "Opptil 300", "Opptil 1500"], gen_factor,
          ["primtall", "faktortre"]),
]
