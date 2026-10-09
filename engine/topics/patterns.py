"""Tallmønstre og figurtall: fra å telle til å skrive en formel med n."""
from __future__ import annotations

import random

from ..core import Problem, Skill, Step, ask


def _linear_fig(n, a, b):
    dots = [[0, y, "base"] for y in range(b)]
    x0 = 1 if b else 0
    for col in range(n):
        cls = "new" if (col == n - 1 and n > 1) else "old"
        dots += [[x0 + col, y, cls] for y in range(a)]
    return dots


def _square_fig(n, b):
    dots = [[x, y, "old"] for x in range(n) for y in range(n)]
    dots += [[n + k % 2, k // 2, "base"] for k in range(b)]
    return dots


def _pattern(figs):
    return {"type": "pattern", "figs": [{"label": f"Figur {i}", "dots": d} for i, d in enumerate(figs, 1)]}


def gen_pattern(level: int, rng: random.Random) -> Problem:
    if level in (1, 2):
        a, b = rng.randint(2, 4), rng.randint(0, 3)
        f = lambda n: a * n + b
        vis = _pattern([_linear_fig(n, a, b) for n in (1, 2, 3)])
        if level == 1:
            N = rng.choice([6, 8, 10, 12, 20])
            steps = [
                Step(say="Tell prikkene i hver figur.",
                     math=f"Figur 1: {f(1)}   Figur 2: {f(2)}   Figur 3: {f(3)}",
                     show=vis, ask=ask("Hvor mange prikker har figur 3?", "int", f(3))),
                Step(say="De nye prikkene er markert. Hvor mange kommer til for hver figur?",
                     math=f"Figuren vokser med {a} hver gang",
                     show=vis, ask=ask("Hvor mange nye prikker per figur?", "int", a,
                                       hint="Sammenlign figur 1 og figur 2. Tell bare de gule prikkene.")),
                Step(say=f"Fra figur 1 til figur {N} er det {N - 1} steg.",
                     math=f"Figur {N}: {f(1)} + {N - 1} · {a} = {f(N)}",
                     show=vis, ask=ask(f"{f(1)} + {N - 1} · {a} = ?", "int", f(N),
                                       [((f(1) + N - 1) * a, "Gang først, legg sammen etterpå.")])),
            ]
            traps = [(f(3) * N // 3, f"Figurene vokser ikke i samme forhold. Tell hvor mange som kommer til per figur."),
                     (a * N, f"Du glemte prikkene som er med fra starten." if b else "Ikke riktig ennå.")]
            if f(3) * N % 3:
                traps = traps[1:]
            if not b:
                traps = [t for t in traps if t[0] != a * N]
            return Problem(task=f"Hvor mange prikker har figur {N}?", expr=f"Figur {N} = ?",
                           steps=steps, final=ask(f"Figur {N}", "int", f(N), traps), start=vis,
                           work=[f"Figur {N}", f"{f(1)} + {N - 1} · {a}", str(f(N))])
        steps = [
            Step(say="Hvor mange nye prikker kommer til for hver figur?",
                 math=f"Vokser med {a} per figur, altså {a}n",
                 show=vis, ask=ask("Økning per figur = ?", "int", a)),
            Step(say=f"{a}n gir {a} prikker i figur 1. Hvor mange prikker er det i tillegg?",
                 math=f"Konstantledd: {f(1)} − {a} = {b}",
                 show=vis, ask=ask(f"{f(1)} − {a} = ?", "int", b)),
            Step(say="Sett sammen og test formelen på figur 3.",
                 math=f"Formel: {a}n + {b}" if b else f"Formel: {a}n",
                 show=vis),
        ]
        want = [f(n) for n in range(1, 7)]
        traps = [([a * n for n in range(1, 7)], "Du mangler prikkene som er der fra starten.")] if b else []
        traps.append(([n + a for n in range(1, 7)], f"Figuren vokser med {a} for hver figur. Da må n ganges med {a}."))
        return Problem(task="Skriv en formel for antall prikker i figur n.", expr="Figur n = ?",
                       steps=steps, final=ask("Formel", "expr_n", want, traps), start=vis)

    b = rng.randint(1, 4)
    f = lambda n: n * n + b
    vis = _pattern([_square_fig(n, b) for n in (1, 2, 3)])
    steps = [
        Step(say="Se på de blå prikkene. De danner et kvadrat.",
             math="Figur 1: 1·1   Figur 2: 2·2   Figur 3: 3·3",
             show=vis, ask=ask("Hvor mange blå prikker har figur 3?", "int", 9)),
        Step(say="Kvadratet i figur n har n · n = n^2 prikker. Hvor mange grå prikker har hver figur i tillegg?",
             math=f"Ekstra prikker: {b}",
             show=vis, ask=ask("Grå prikker = ?", "int", b)),
        Step(say="Sett sammen.", math=f"Formel: n^2 + {b}", show=vis),
    ]
    want = [f(n) for n in range(1, 7)]
    traps = [([2 * n + b for n in range(1, 7)], "n^2 betyr n · n, ikke 2 · n."),
             ([n * n for n in range(1, 7)], "Du mangler de grå prikkene.")]
    return Problem(task="Skriv en formel for antall prikker i figur n.", expr="Figur n = ?",
                   steps=steps, final=ask("Formel", "expr_n", want, traps), start=vis)


SKILLS = [
    Skill("pattern", "monster", "Figurtall",
          "Finn systemet og skriv det med n.",
          ["Finn figur 10", "Formel med n", "Kvadrattall"], gen_pattern, ["mønster", "variabel"]),
]
