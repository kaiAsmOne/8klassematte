"""Regnestrategier: kommutativ, assosiativ og distributiv lov i hoderegning."""
from __future__ import annotations

import random

from ..core import Problem, Skill, Step, ask, n_

# ------------------------------------------------------------- regroup

def _cards(groups, op, sums=None):
    sums = sums or [None] * len(groups)
    return {"type": "cards", "op": op,
            "groups": [{"items": g, "sum": s} for g, s in zip(groups, sums)]}


def gen_regroup(level: int, rng: random.Random) -> Problem:
    if level == 1:
        target = rng.choice([50, 100, 100, 200])
        a = rng.choice([x for x in range(11, target - 10) if x % 10])
        b = target - a
        c = rng.choice([x for x in range(12, 99) if x % 10])
        op, sym = "+", "+"
        nums, pair, rest = [a, c, b], (a, b), [c]
    elif level == 2:
        a, b = rng.choice([(25, 4), (4, 25), (5, 2), (2, 5), (50, 2), (20, 5), (125, 8)])
        c = rng.choice([x for x in range(3, 20) if x != 10])
        op, sym = "·", "·"
        nums, pair, rest = [a, c, b], (a, b), [c]
    else:
        a, b = rng.choice([(25, 4), (5, 2), (50, 2), (20, 5)])
        c, d = rng.randint(2, 9), rng.randint(2, 9)
        op, sym = "·", "·"
        nums, pair, rest = [a, c, b, d], (a, b), [c, d]

    calc = (lambda x, y: x + y) if op == "+" else (lambda x, y: x * y)
    law = "Addisjon" if op == "+" else "Multiplikasjon"
    first = calc(*pair)
    expr = f" {sym} ".join(n_(x) for x in nums)
    steps = [Step(
        say=f"{law} kan byttes om og grupperes som du vil. Se etter to tall som gir et rundt tall sammen.",
        math=f"{expr} = ({n_(pair[0])} {sym} {n_(pair[1])}) {sym} " + f" {sym} ".join(n_(x) for x in rest),
        show=_cards([list(pair)] + [[x] for x in rest], op),
        ask=ask(f"{n_(pair[0])} {sym} {n_(pair[1])} = ?", "int", first),
    )]
    if len(rest) == 1:
        total = calc(first, rest[0])
        steps.append(Step(
            say="Det runde tallet gjør resten til enkel hoderegning.",
            math=f"= {n_(first)} {sym} {n_(rest[0])} = {n_(total)}",
            show=_cards([list(pair), rest], op, [first, None]),
            ask=ask(f"{n_(first)} {sym} {n_(rest[0])} = ?", "int", total),
        ))
    else:
        r = calc(*rest)
        total = first * r
        steps.append(Step(
            say="Gang sammen de to andre tallene for seg.",
            math=f"= {n_(first)} {sym} ({n_(rest[0])} {sym} {n_(rest[1])})",
            show=_cards([list(pair), rest], op, [first, None]),
            ask=ask(f"{rest[0]} {sym} {rest[1]} = ?", "int", r),
        ))
        steps.append(Step(
            say="Gang med det runde tallet til slutt.",
            math=f"= {n_(first)} {sym} {n_(r)} = {n_(total)}",
            show=_cards([list(pair), rest], op, [first, r]),
            ask=ask(f"{n_(first)} {sym} {n_(r)} = ?", "int", total),
        ))
    plain = f" {sym} ".join(str(x) for x in nums)
    if len(rest) == 1:
        work = [plain, f"({pair[0]} {sym} {pair[1]}) {sym} {rest[0]}", str(total)]
    else:
        work = [plain, f"({pair[0]} {sym} {pair[1]}) {sym} ({rest[0]} {sym} {rest[1]})",
                f"{first} {sym} {r}", str(total)]
    naive = None
    if op == "·" and len(nums) == 3:
        naive = nums[0] * nums[1]
    traps = [(naive, "Det er bare de to første tallene. Ta med alle faktorene.")] if naive else []
    return Problem(
        task="Regn ut i hodet. Finn en lur rekkefølge.",
        expr=expr,
        steps=steps,
        final=ask("Svar", "int", total, traps),
        start=_cards([[x] for x in nums], op),
        work=work,
    )


# ------------------------------------------------------------- distribute

def _area(rows, cols, cells, cut=None, cutval=None):
    return {"type": "area", "rows": rows, "cols": cols, "cells": cells, "cut": cut, "cutval": cutval}


def gen_distrib(level: int, rng: random.Random) -> Problem:
    if level == 1:
        a = rng.randint(3, 9)
        b = rng.choice([x for x in range(21, 99) if x % 10])
        tens, ones = b - b % 10, b % 10
        p1, p2, total = a * tens, a * ones, a * b
        steps = [
            Step(say=f"Del opp {b} i tiere og enere. Rektangelet viser {a} · {b} som to deler.",
                 math=f"{a} · {b} = {a} · ({tens} + {ones})",
                 show=_area([a], [tens, ones], [[None, None]])),
            Step(say="Regn ut den store delen først.",
                 math=f"= {a} · {tens} + {a} · {ones}",
                 show=_area([a], [tens, ones], [[p1, None]]),
                 ask=ask(f"{a} · {tens} = ?", "int", p1,
                         [(a * (tens // 10), f"Husk at det er {tens}, ikke {tens // 10}. Legg til en null.")])),
            Step(say="Så den lille delen.",
                 math=f"= {n_(p1)} + {p2}",
                 show=_area([a], [tens, ones], [[p1, p2]]),
                 ask=ask(f"{a} · {ones} = ?", "int", p2)),
            Step(say="Legg sammen delene. Hele rektangelet er svaret.",
                 math=f"= {n_(total)}",
                 show=_area([a], [tens, ones], [[p1, p2]]),
                 ask=ask(f"{n_(p1)} + {p2} = ?", "int", total)),
        ]
        start = _area([a], [b], [[None]])
        traps = [(a * tens + ones, f"Du glemte å gange {ones} med {a}. Begge delene skal ganges.")]
        work = [f"{a} · {b}", f"{a} · {tens} + {a} · {ones}", f"{p1} + {p2}", str(total)]
    elif level == 2:
        rnd = rng.choice([20, 30, 40, 50, 60, 100, 100, 200])
        k = rng.randint(1, 3)
        a = rng.randint(3, 9)
        b = rnd - k
        big, small, total = a * rnd, a * k, a * b
        steps = [
            Step(say=f"{b} er nesten {rnd}. Regn med {rnd} og trekk fra det du har for mye.",
                 math=f"{a} · {b} = {a} · ({rnd} − {k})",
                 show=_area([a], [rnd], [[None]], cut=k)),
            Step(say="Regn ut hele rektangelet.",
                 math=f"= {a} · {rnd} − {a} · {k}",
                 show=_area([a], [rnd], [[big]], cut=k),
                 ask=ask(f"{a} · {rnd} = ?", "int", big)),
            Step(say="Regn ut stripen som er for mye.",
                 math=f"= {n_(big)} − {small}",
                 show=_area([a], [rnd], [[big]], cut=k, cutval=small),
                 ask=ask(f"{a} · {k} = ?", "int", small)),
            Step(say="Trekk stripen fra.",
                 math=f"= {n_(total)}",
                 show=_area([a], [rnd], [[big]], cut=k, cutval=small),
                 ask=ask(f"{n_(big)} − {small} = ?", "int", total)),
        ]
        start = _area([a], [b], [[None]])
        traps = [(big - k, f"Du trakk fra {k}, men du har {a} rader for mye. Trekk fra {a} · {k}.")]
        work = [f"{a} · {b}", f"{a} · {rnd} − {a} · {k}", f"{big} − {small}", str(total)]
    else:
        x = rng.randint(12, 39)
        y = rng.randint(12, 29)
        x1, x2 = x - x % 10, x % 10
        y1, y2 = y - y % 10, y % 10
        if not x2 or not y2:
            return gen_distrib(level, rng)
        p = [[x1 * y1, x1 * y2], [x2 * y1, x2 * y2]]
        total = x * y
        cells = [[None, None], [None, None]]
        steps = [Step(say=f"Del opp begge tallene. Rektangelet får fire deler.",
                      math=f"{x} · {y} = ({x1} + {x2}) · ({y1} + {y2})",
                      show=_area([x1, x2], [y1, y2], cells))]
        order = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, j in order:
            cells = [row[:] for row in cells]
            cells[i][j] = p[i][j]
            rv, cv = (x1, x2)[i], (y1, y2)[j]
            steps.append(Step(say="Regn ut neste del av rektangelet.",
                              math=f"{rv} · {cv} = {p[i][j]}",
                              show=_area([x1, x2], [y1, y2], cells),
                              ask=ask(f"{rv} · {cv} = ?", "int", p[i][j])))
        s = sum(sum(r) for r in p)
        steps.append(Step(say="Legg sammen alle fire delene.",
                          math=f"{x} · {y} = {' + '.join(str(v) for r in p for v in r)} = {n_(total)}",
                          show=_area([x1, x2], [y1, y2], p),
                          ask=ask(f"{' + '.join(str(v) for r in p for v in r)} = ?", "int", s)))
        start = _area([x], [y], [[None]])
        traps = [(x1 * y1 + x2 * y2, "Du ganget tiere med tiere og enere med enere. Du mangler de to andre delene av rektangelet.")]
        work = [f"{x} · {y}", f"({x1} + {x2}) · ({y1} + {y2})",
                " + ".join(str(v) for r in p for v in r), str(total)]

    return Problem(
        task="Regn ut ved å dele opp tallet.",
        expr=steps[0].math.split(" = ")[0],
        steps=steps,
        final=ask("Svar", "int", total, traps),
        start=start,
        work=work,
    )


SKILLS = [
    Skill("regroup", "strategier", "Lur rekkefølge",
          "Bytt om og grupper tall så hoderegningen blir enkel.",
          ["Pluss", "Gange", "Fire faktorer"], gen_regroup,
          ["kommutativ", "assosiativ"]),
    Skill("distrib", "strategier", "Del opp tallet",
          "Den distributive loven, vist som et rektangel.",
          ["Tiere og enere", "Nesten runde tall", "To tosifrede tall"], gen_distrib,
          ["distributiv"]),
]
