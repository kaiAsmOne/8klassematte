"""Brøk: forkorte med primtallsfaktorer, legge sammen/trekke fra, gange."""
from __future__ import annotations

import math
import random
from collections import Counter
from fractions import Fraction

from ..core import Problem, Skill, Step, ask, f_, fr_, lcm, prime_factors


def _bars(*rows):
    return {"type": "bars", "rows": [{"n": n, "d": d} for n, d in rows]}


def _struck(fs: list[int], common: Counter) -> str:
    left, out = Counter(common), []
    for p in fs:
        if left[p]:
            out.append(f"!!{p}!!")
            left[p] -= 1
        else:
            out.append(str(p))
    return "·".join(out) or "1"


# -------------------------------------------------------------- simplify

def gen_simplify(level: int, rng: random.Random) -> Problem:
    ks = {1: [2, 3, 4, 5, 6], 2: [6, 8, 9, 10, 12, 14, 15, 18]}[min(level, 2)]
    while True:
        b = rng.randint(3, 9 if level == 1 else 11)
        a = rng.randint(1, b - 1)
        if math.gcd(a, b) == 1:
            break
    k = rng.choice(ks)
    n, d = a * k, b * k
    fn, fd = prime_factors(n), prime_factors(d)
    common = Counter(fn) & Counter(fd)
    steps = [
        Step(say="Skriv teller og nevner som produkt av primtall.",
             math=f"{f_(n, d)} = {f_('·'.join(map(str, fn)), '·'.join(map(str, fd)))}",
             show=_bars((n, d))),
        Step(say="Stryk faktorer som står både over og under brøkstreken. Ganget sammen blir de største felles faktor.",
             math=f"= {f_(_struck(fn, common), _struck(fd, common))}",
             show=_bars((n, d)),
             ask=ask(f"Største felles faktor for {n} og {d} = ?", "int", k,
                     [(n - d, "Vi ser etter et tall som går opp i begge, ikke forskjellen.")])),
        Step(say="Det som blir igjen, er brøken forkortet. Stripene viser at den er like stor som før.",
             math=f"= {f_(a, b)}",
             show=_bars((n, d), (a, b)),
             ask=ask("Forkortet brøk = ?", "frac_simplest", [a, b])),
    ]
    return Problem(
        task="Forkort brøken så langt det går.",
        expr=f_(n, d),
        steps=steps,
        final=ask("Forkortet brøk", "frac_simplest", [a, b]),
        work=[f"{n}/{d}", f"({n} : {k})/({d} : {k})", f"{a}/{b}"],
        start=_bars((n, d)),
    )


# -------------------------------------------------------------- add / sub

def _pick_dens(level: int, rng: random.Random):
    if level == 1:
        d1 = rng.randint(2, 6)
        d2 = d1 * rng.choice([2, 3] if d1 <= 4 else [2])
    elif level == 2:
        d1, d2 = rng.sample([2, 3, 4, 5, 7], 2)
    else:
        d1, d2 = rng.choice([(4, 6), (6, 8), (6, 9), (8, 12), (4, 10), (9, 12), (6, 10), (10, 15)])
    return (d1, d2) if rng.random() < 0.5 else (d2, d1)


def _expand_step(which, n, d, k, N, L, vis):
    if k == 1:
        return Step(say=f"{which.capitalize()} har allerede nevner {L}.", math=f"{f_(n, d)} = {f_(N, L)}", show=vis)
    return Step(say=f"Utvid {which} så nevneren blir {L}.",
                math=f"{f_(n, d)} = {f_(f'{n}·{k}', f'{d}·{k}')} = {f_(N, L)}",
                show=vis,
                ask=ask(f"{f_(n, d)} = {f_('?', L)}. Hva blir telleren?", "int", N,
                        [(n, f"Når nevneren ganges med {k}, må telleren også ganges med {k}.")]))


def gen_addsub(level: int, rng: random.Random) -> Problem:
    while True:
        d1, d2 = _pick_dens(level, rng)
        n1, n2 = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
        op = rng.choice("+−")
        x, y = Fraction(n1, d1), Fraction(n2, d2)
        res = x + y if op == "+" else x - y
        if math.gcd(n1, d1) > 1 or math.gcd(n2, d2) > 1:
            continue
        if res > 0 and (level > 1 or res <= 1):
            break
    L = lcm(d1, d2)
    k1, k2 = L // d1, L // d2
    N1, N2 = n1 * k1, n2 * k2
    S = N1 + N2 if op == "+" else N1 - N2
    expr = f"{f_(n1, d1)} {op} {f_(n2, d2)}"
    wrong_L = [(d1 * d2, "Det virker som fellesnevner, men det finnes en mindre.")] if d1 * d2 != L else []
    naive = (n1 + n2, d1 + d2) if op == "+" else (n1 - n2, d1 - d2)
    steps = [
        Step(say="Bitene må være like store før vi kan legge sammen eller trekke fra. "
                 "Finn det minste tallet begge nevnerne går opp i.",
             math=f"Fellesnevner: {L}",
             show=_bars((n1, d1), (n2, d2)),
             ask=ask(f"Minste fellesnevner for {d1} og {d2} = ?", "int", L, wrong_L,
                     hint=f"Gå gjennom {max(d1, d2)}-gangen til du finner et tall som {min(d1, d2)} også går opp i.")),
        _expand_step("den første brøken", n1, d1, k1, N1, L, _bars((N1, L), (n2, d2))),
        _expand_step("den andre brøken", n2, d2, k2, N2, L, _bars((N1, L), (N2, L))),
        Step(say="Nå er bitene like store. Regn med tellerne, nevneren beholdes.",
             math=f"{f_(N1, L)} {op} {f_(N2, L)} = {f_(S, L)}",
             show=_bars((N1, L), (N2, L), (S, L)),
             ask=ask(f"{N1} {op} {N2} = ?", "int", S)),
    ]
    if Fraction(S, L).denominator != L:
        steps.append(Step(say="Forkort svaret hvis det går.",
                          math=f"= {fr_(res)}",
                          show=_bars((S, L), (res.numerator, res.denominator)),
                          ask=ask(f"{f_(S, L)} forkortet = ?", "frac_simplest",
                                  [res.numerator, res.denominator])))
    traps = [(list(naive), "Du regnet med nevnerne også. Nevneren sier hvor store bitene er, "
                           "og de må være like store før vi kan legge sammen.")] if naive[1] else []
    traps.append(([n1 + n2 if op == "+" else n1 - n2, L],
                  "Nevneren er riktig, men tellerne må utvides før du legger sammen."))
    return Problem(
        task="Regn ut. Forkort svaret hvis det går.",
        expr=expr,
        steps=steps,
        final=ask("Svar", "frac", [res.numerator, res.denominator], traps),
        start=_bars((n1, d1), (n2, d2)),
        work=[f"{n1}/{d1} {op} {n2}/{d2}", f"{N1}/{L} {op} {N2}/{L}", f"{S}/{L}"]
             + ([f"{res.numerator}/{res.denominator}"] if res.denominator != L else []),
    )


# -------------------------------------------------------------- multiply

def gen_mult(level: int, rng: random.Random) -> Problem:
    while True:
        d1, d2 = rng.randint(2, 6 if level == 1 else 9), rng.randint(2, 6 if level == 1 else 9)
        n1, n2 = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
        if math.gcd(n1, d1) > 1 or math.gcd(n2, d2) > 1:
            continue
        if level == 1 or math.gcd(n1, d2) > 1 or math.gcd(n2, d1) > 1:
            break
    res = Fraction(n1 * n2, d1 * d2)
    grid = {"type": "fracgrid", "a": [n1, d1], "b": [n2, d2]}
    steps = [
        Step(say=f"Rutenettet har {d1} kolonner og {d2} rader. Den første brøken farger kolonner, den andre rader.",
             math=f"{f_(n1, d1)} · {f_(n2, d2)} = {f_(f'{n1}·{n2}', f'{d1}·{d2}')}",
             show=grid),
        Step(say="Teller: rutene som er farget av begge brøkene.",
             math=f"Teller: {n1}·{n2} = {n1 * n2}",
             show={**grid, "overlap": True},
             ask=ask(f"{n1} · {n2} = ?", "int", n1 * n2)),
        Step(say="Nevner: alle rutene i rutenettet.",
             math=f"Nevner: {d1}·{d2} = {d1 * d2}",
             show={**grid, "overlap": True, "count": True},
             ask=ask(f"{d1} · {d2} = ?", "int", d1 * d2,
                     [(d1 + d2, "Nevnerne skal ganges, ikke legges sammen.")])),
    ]
    if res.denominator != d1 * d2:
        steps.append(Step(say="Forkort svaret.",
                          math=f"{f_(n1 * n2, d1 * d2)} = {fr_(res)}",
                          show={**grid, "overlap": True, "count": True},
                          ask=ask(f"{f_(n1 * n2, d1 * d2)} forkortet = ?", "frac_simplest",
                                  [res.numerator, res.denominator])))
    else:
        steps.append(Step(say="Svaret kan ikke forkortes.",
                          math=f"= {fr_(res)}",
                          show={**grid, "overlap": True, "count": True}))
    traps = [([n1 * n2, d1], "Nevnerne skal også ganges sammen."),
             ([n1 * n2, d1 + d2], "Nevnerne skal ganges, ikke legges sammen.")]
    if d1 == d2:
        traps = traps[1:]
    return Problem(
        task="Regn ut. Forkort svaret hvis det går.",
        expr=f"{f_(n1, d1)} · {f_(n2, d2)}",
        steps=steps,
        final=ask("Svar", "frac", [res.numerator, res.denominator], traps),
        start=grid,
        work=[f"{n1}/{d1} · {n2}/{d2}", f"({n1} · {n2})/({d1} · {d2})", f"{n1 * n2}/{d1 * d2}"]
             + ([f"{res.numerator}/{res.denominator}" if res.denominator > 1 else str(res.numerator)]
                if res.denominator != d1 * d2 else []),
    )


SKILLS = [
    Skill("simplify", "brok", "Forkorte brøk",
          "Bruk primtallsfaktorer til å forkorte.",
          ["Små tall", "Store tall"], gen_simplify, ["forkorte", "felles faktor"]),
    Skill("addsub", "brok", "Pluss og minus med brøk",
          "Finn fellesnevner og gjør bitene like store.",
          ["Den ene nevneren går opp i den andre", "Ulike nevnere", "Minste fellesnevner"], gen_addsub,
          ["fellesnevner", "utvide"]),
    Skill("mult", "brok", "Gange brøker",
          "Se brøkmultiplikasjon som et rutenett.",
          ["Små nevnere", "Forkort underveis"], gen_mult, ["brøk ganger brøk"]),
]
