"""Potenser, potensregler, kvadratrøtter og standardform."""
from __future__ import annotations

import random
from fractions import Fraction

from ..core import MINUS, NBSP, Problem, Skill, Step, ask, dec_, f_, fr_, n_, p_


def plain_(x) -> str:
    """Exact decimal as a machine-readable string, e.g. '9.2'."""
    return dec_(x).replace(",", ".").replace(NBSP, "").replace(MINUS, "-")


def _chips(*rows):
    return {"type": "chips", "rows": [
        {"items": items, "cancel": cancel or [], "label": label} for label, items, cancel in rows]}


# ------------------------------------------------------------ evaluate

def gen_power(level: int, rng: random.Random) -> Problem:
    if level == 1:
        if rng.random() < 0.2:
            b, e = 10, rng.randint(3, 6)
        else:
            while True:
                b, e = rng.randint(2, 6), rng.randint(2, 5)
                if b ** e <= 1300 and not (e == 2 and b < 4):
                    break
        val = b ** e
        items = [str(b)] * e
        steps = [
            Step(say="En potens er gjentatt multiplikasjon. Eksponenten sier hvor mange ganger grunntallet er faktor.",
                 math=f"{b}^{e} = " + " · ".join(items),
                 show=_chips(("", items, None)),
                 ask=ask(f"Hvor mange ganger står {b} som faktor?", "int", e,
                         [(b, f"{b} er grunntallet. Eksponenten er det lille tallet oppe til høyre.")] if b != e else None)),
            Step(say="Gang sammen én faktor om gangen.",
                 math=f"= {n_(val)}",
                 show=_chips(("", items, None)),
                 ask=ask(f"{b}^{e} = ?", "int", val, [(b * e, "Du ganget grunntallet med eksponenten.")])),
        ]
        traps = [(b * e, f"Du regnet {b} · {e}. En potens betyr {' · '.join(items)}.")]
        work = [f"{b}^{e}", " · ".join(items), str(val)]
        expr = f"{b}^{e}"
    elif level == 2:
        b, e = rng.randint(2, 5), rng.randint(2, 4)
        paren = rng.random() < 0.6
        pos = b ** e
        if paren:
            val = pos if e % 2 == 0 else -pos
            expr = f"({MINUS}{b})^{e}"
            items = [f"({MINUS}{b})"] * e
            steps = [
                Step(say="Parentesen betyr at minustegnet hører med til grunntallet. Skriv ut alle faktorene.",
                     math=f"{expr} = " + " · ".join(items),
                     show=_chips(("", items, None)),
                     ask=ask("Hvor mange minustegn blir det?", "int", e)),
                Step(say="To minus ganget sammen gir pluss. Et partall minustegn gir pluss, et oddetall gir minus.",
                     math="Fortegn: " + ("+" if val > 0 else MINUS),
                     show=_chips(("", items, None)),
                     ask=ask("Blir svaret positivt eller negativt?", "sign", "+" if val > 0 else "-")),
                Step(say="Regn ut tallverdien og sett på fortegnet.",
                     math=f"= {n_(val)}",
                     show=_chips(("", items, None)),
                     ask=ask(f"{expr} = ?", "int", val, [(-val, "Tallet er riktig, men sjekk fortegnet.")])),
            ]
        else:
            val = -pos
            expr = f"{MINUS}{b}^{e}"
            items = [str(b)] * e
            steps = [
                Step(say=f"Uten parentes gjelder eksponenten bare {b}. Minustegnet står utenfor og tas til slutt.",
                     math=f"{expr} = {MINUS}(" + " · ".join(items) + ")",
                     show=_chips((MINUS, items, None)),
                     ask=ask(f"{b}^{e} = ?", "int", pos)),
                Step(say="Sett minustegnet foran.",
                     math=f"= {n_(val)}",
                     show=_chips((MINUS, items, None))),
            ]
        traps = [(-val, "Tallet er riktig, men sjekk fortegnet. Står minustegnet inne i parentesen eller utenfor?")]
        work = [expr, (" · ".join(items) if paren else f"{MINUS}(" + " · ".join(items) + ")"), n_(val)]
    else:
        if rng.random() < 0.4:
            b = rng.randint(2, 9)
            rows = [(f"{b}^{k}", b ** k) for k in (3, 2, 1)]
            val = 1
            expr = f"{b}^0"
            steps = [
                Step(say=f"Se på mønsteret. Hver gang eksponenten blir én mindre, deler vi på {b}.",
                     math="   ".join(f"{s} = {v}" for s, v in rows),
                     show={"type": "ladderpow", "base": b, "rows": [[3, b ** 3], [2, b ** 2], [1, b], [0, None]]}),
                Step(say=f"Fortsett mønsteret ett steg til: del {b} på {b}.",
                     math=f"{b}^0 = {b} : {b} = 1",
                     show={"type": "ladderpow", "base": b, "rows": [[3, b ** 3], [2, b ** 2], [1, b], [0, 1]]},
                     ask=ask(f"{b} : {b} = ?", "int", 1)),
            ]
            work = [f"{b}^0", f"{b} : {b}", "1"]
            traps = [(0, "Eksponent 0 gir ikke 0. Fortsett mønsteret: del på grunntallet én gang til."),
                     (b, "Det er " + f"{b}^1. Del på {b} én gang til.")]
        else:
            while True:
                a, c = rng.randint(1, 5), rng.randint(2, 7)
                if a < c and Fraction(a, c).denominator == c:
                    break
            e = rng.choice([2, 2, 3])
            val = Fraction(a ** e, c ** e)
            expr = f"({f_(a, c)})^{e}"
            steps = [
                Step(say="Potensen gjelder hele brøken. Opphøy både teller og nevner.",
                     math=f"{expr} = {f_(f'{a}^{e}', f'{c}^{e}')}",
                     show=_chips(("", [f"{{{a}/{c}}}"] * e, None))),
                Step(say="Regn ut telleren.", math=f"Teller: {a}^{e} = {a ** e}",
                     ask=ask(f"{a}^{e} = ?", "int", a ** e)),
                Step(say="Regn ut nevneren.", math=f"= {f_(a ** e, c ** e)}",
                     ask=ask(f"{c}^{e} = ?", "int", c ** e)),
            ]
            traps = [([a ** e, c], "Nevneren skal også opphøyes.")]
            return Problem(task="Regn ut potensen.", expr=expr, steps=steps,
                           final=ask("Svar", "frac", [val.numerator, val.denominator], traps),
                           start=_chips(("", [f"{{{a}/{c}}}"] * e, None)),
                           work=[f"({a}/{c})^{e}", f"{a}^{e}/{c}^{e}", f"{a ** e}/{c ** e}"])
    return Problem(task="Regn ut potensen.", expr=expr, steps=steps,
                   final=ask("Svar", "int", val, traps), start=steps[0].show, work=work)


# ------------------------------------------------------------ rules

def gen_rules(level: int, rng: random.Random) -> Problem:
    a = rng.choice(["a", "a", "x", "2", "3", "5"])
    kind = level if level < 3 else rng.choice([3, 3, 4])
    if kind == 1:
        m, n = rng.randint(2, 5), rng.randint(2, 5)
        res = m + n
        expr = f"{a}^{m} · {a}^{n}"
        start = _chips((f"{a}^{m}", [a] * m, None), (f"{a}^{n}", [a] * n, None))
        steps = [
            Step(say="Skriv ut begge potensene som gjentatt multiplikasjon.",
                 math=f"{expr} = ({' · '.join([a] * m)}) · ({' · '.join([a] * n)})",
                 show=start,
                 ask=ask(f"Hvor mange faktorer {a} blir det til sammen?", "int", res,
                         [(m * n, "Tell faktorene. Det er to grupper som legges ved siden av hverandre.")],
                         hint="Tell alle brikkene på tavla.")),
            Step(say="Ved ganging legger vi sammen eksponentene.",
                 math=f"= {a}^{res}",
                 show=_chips((f"{a}^{res}", [a] * res, None))),
        ]
        traps = [(m * n, "Du ganget eksponentene. Når potenser med samme grunntall ganges, legger vi sammen eksponentene.")]
    elif kind == 2:
        n = rng.randint(1, 4)
        m = n + rng.randint(1, 4)
        res = m - n
        expr = f"{f_(f'{a}^{m}', f'{a}^{n}')}"
        steps = [
            Step(say="Skriv ut teller og nevner. Hver faktor i nevneren kan strykes mot en i telleren.",
                 math=f"{expr} = {f_(' · '.join([a] * m), ' · '.join([a] * n))}",
                 show=_chips(("teller", [a] * m, None), ("nevner", [a] * n, None))),
            Step(say="Stryk like faktorer over og under brøkstreken.",
                 math=f"= {a}^{res}",
                 show=_chips(("teller", [a] * m, list(range(n))), ("nevner", [a] * n, list(range(n)))),
                 ask=ask(f"Hvor mange faktorer {a} blir igjen i telleren?", "int", res)),
            Step(say="Ved deling trekker vi eksponenten i nevneren fra eksponenten i telleren.",
                 math=f"{a}^{m} : {a}^{n} = {a}^({m} − {n}) = {a}^{res}"),
        ]
        traps = [(m + n, "Ved deling trekker vi fra eksponentene, vi legger ikke sammen.")]
        if m % n == 0 and m // n != res:
            traps.append((m // n, "Du delte eksponentene. Ved deling trekker vi dem fra hverandre."))
    elif kind == 3:
        m, n = rng.randint(2, 4), rng.randint(2, 3)
        res = m * n
        expr = f"({a}^{m})^{n}"
        rows = tuple((f"{a}^{m}", [a] * m, None) for _ in range(n))
        steps = [
            Step(say=f"({a}^{m})^{n} betyr {a}^{m} ganget med seg selv {n} ganger.",
                 math=f"{expr} = " + " · ".join([f"{a}^{m}"] * n),
                 show=_chips(*rows),
                 ask=ask(f"Hvor mange faktorer {a} blir det til sammen?", "int", res,
                         [(m + n, "Tell alle faktorene i alle radene.")])),
            Step(say="Potens av en potens: vi ganger eksponentene.",
                 math=f"= {a}^({m} · {n}) = {a}^{res}"),
        ]
        traps = [(m + n, "Her er det potens av en potens. Da ganger vi eksponentene.")]
    else:
        m, n = rng.randint(2, 5), rng.randint(2, 5)
        k = rng.randint(1, m + n - 1)
        res = m + n - k
        expr = f"{f_(f'{a}^{m} · {a}^{n}', f'{a}^{k}')}"
        steps = [
            Step(say="Start med telleren: ganging betyr at vi legger sammen eksponentene.",
                 math=f"{expr} = {f_(f'{a}^{m + n}', f'{a}^{k}')}",
                 show=_chips(("teller", [a] * (m + n), None), ("nevner", [a] * k, None)),
                 ask=ask("Eksponenten i telleren = ?", "int", m + n)),
            Step(say="Så delingen: trekk fra eksponenten i nevneren.",
                 math=f"= {a}^{res}",
                 show=_chips(("teller", [a] * (m + n), list(range(k))), ("nevner", [a] * k, list(range(k)))),
                 ask=ask("Eksponenten i svaret = ?", "int", res)),
        ]
        traps = [(m * n - k, "I telleren skal eksponentene legges sammen, ikke ganges.")]
    return Problem(
        task=f"Skriv som én potens. Hvilken eksponent får {a}?",
        expr=f"{expr} = {a}^?",
        steps=steps,
        final=ask("Eksponent", "int", res, traps, fmt="Skriv bare eksponenten"),
        start=steps[0].show,
    )


# ------------------------------------------------------------ sqrt

def gen_sqrt(level: int, rng: random.Random) -> Problem:
    if level == 1:
        n = rng.randint(2, 15)
        sq = n * n
        steps = [
            Step(say=f"Kvadratroten er sidelengden i et kvadrat med {sq} ruter. "
                     f"Hvilket tall ganget med seg selv gir {sq}?",
                 math=f"√({sq}) = {n}, fordi {n} · {n} = {sq}",
                 show={"type": "square", "n": n, "label": sq, "side": None},
                 ask=ask("Sidelengden = ?", "int", n, hint="Prøv deg fram: 5 · 5, 6 · 6, 7 · 7 …")),
            Step(say="Sjekk ved å telle ruter langs én side.",
                 math=f"√({sq}) = {n}",
                 show={"type": "square", "n": n, "label": sq, "side": n}),
        ]
        traps = [(sq // 2, "Kvadratroten er ikke halvparten. Finn tallet som ganget med seg selv gir tallet.")] if sq % 2 == 0 else []
        return Problem(task="Regn ut kvadratroten.", expr=f"√({sq})", steps=steps,
                       final=ask("Svar", "int", n, traps),
                       start={"type": "square", "n": n, "label": sq, "side": None},
                       work=[f"√{sq}", str(n)])
    if level == 2:
        k = rng.randint(3, 13)
        m = rng.randint(k * k + 1, (k + 1) ** 2 - 1)
        near = k if m - k * k < (k + 1) ** 2 - m else k + 1
        vis = {"type": "square", "n": k, "n2": k + 1, "target": m}
        steps = [
            Step(say=f"{m} er ikke et kvadrattall. Finn kvadrattallene rett under og rett over.",
                 math=f"{k}^2 = {k * k} < {m}",
                 show=vis,
                 ask=ask(f"Største kvadrattall som er mindre enn {m} = ?", "int", k * k)),
            Step(say="Og kvadrattallet rett over.",
                 math=f"{m} < {(k + 1) ** 2} = {k + 1}^2",
                 show=vis,
                 ask=ask(f"Minste kvadrattall som er større enn {m} = ?", "int", (k + 1) ** 2)),
            Step(say=f"√({m}) ligger altså mellom {k} og {k + 1}. Hvilket kvadrattall ligger {m} nærmest?",
                 math=f"√({m}) ≈ {near}",
                 show=vis,
                 ask=ask("Nærmeste hele tall = ?", "int", near)),
        ]
        return Problem(task="Hvilket helt tall ligger kvadratroten nærmest?", expr=f"√({m}) ≈ ?",
                       steps=steps, final=ask("Nærmeste hele tall", "int", near,
                                              [(m // 2, "Kvadratroten er ikke halvparten.")]),
                       start=vis)
    a = rng.randint(2, 9)
    b = rng.choice([10, 10, 3, 4, 5])
    if b == a:
        b = 10
    N = (a * b) ** 2
    steps = [
        Step(say="Del opp tallet i to kvadrattall som er lette å ta roten av.",
             math=f"√({n_(N)}) = √({a * a} · {b * b})",
             show={"type": "square", "n": a, "label": a * a, "side": None},
             ask=ask(f"√({a * a}) = ?", "int", a)),
        Step(say="Ta roten av den andre faktoren.",
             math=f"= √({a * a}) · √({b * b})",
             ask=ask(f"√({b * b}) = ?", "int", b)),
        Step(say="Gang røttene sammen.",
             math=f"= {a} · {b} = {a * b}",
             ask=ask(f"{a} · {b} = ?", "int", a * b)),
    ]
    return Problem(task="Regn ut kvadratroten uten kalkulator.", expr=f"√({n_(N)})", steps=steps,
                   final=ask("Svar", "int", a * b), start=None,
                   work=[f"√{N}", f"√{a * a} · √{b * b}", f"{a} · {b}", str(a * b)])


# ------------------------------------------------------------ standard form

def _mantissa(rng):
    digits = rng.choice([2, 2, 3])
    first = rng.randint(1, 9)
    rest = "".join(str(rng.randint(0, 9)) for _ in range(digits - 1)).rstrip("0") or ""
    return Fraction(f"{first}.{rest}" if rest else str(first)), first, rest


def gen_std(level: int, rng: random.Random) -> Problem:
    mant, first, rest = _mantissa(rng)
    if level in (1, 2):
        e = rng.randint(3, 9)
    else:
        e = -rng.randint(2, 6)
    value = mant * Fraction(10) ** e
    msig = f"{first}{rest}"
    if e > 0:
        digits = msig + "0" * (e - len(rest))
        frm, to = len(digits), 1
    else:
        digits = "0" * (-e) + msig
        frm, to = 1, 1 - e
    shift = {"type": "shift", "digits": digits, "from": frm, "to": to}

    if level == 2:
        steps = [
            Step(say="10 opphøyd i eksponenten sier hvor mange plasser kommaet skal flyttes mot høyre.",
                 math=f"{dec_(mant)} · 10^{e}",
                 show={**shift, "from": 1, "to": 1},
                 ask=ask("Hvor mange plasser?", "int", e)),
            Step(say="Flytt kommaet og fyll på med nuller.",
                 math=f"{dec_(mant)} · 10^{e} = {dec_(value)}",
                 show={**shift, "from": 1, "to": frm},
                 ask=ask("Skriv tallet", "num", plain_(value))),
        ]
        wrong = mant * Fraction(10) ** (e - 1)
        return Problem(task="Skriv tallet på vanlig form.", expr=f"{dec_(mant)} · 10^{e} = ?", steps=steps,
                       final=ask("Tallet", "num", plain_(value),
                                 [(plain_(wrong), "Du flyttet kommaet én plass for lite. Tell plassene, ikke nullene.")]),
                       start={**shift, "from": 1, "to": 1},
                       work=[f"{dec_(mant)}·10^{e}", dec_(value).replace(NBSP, " ")])

    direction = "til venstre" if e > 0 else "til høyre"
    steps = [
        Step(say="På standardform står tallet a · 10^n, der a er minst 1 og mindre enn 10. "
                 "Sett kommaet rett bak det første sifferet som ikke er null.",
             math=f"a = {dec_(mant)}",
             show={**shift, "to": frm, "mark": to},
             ask=ask("Hva blir a?", "num", plain_(mant), hint="a skal være minst 1 og mindre enn 10.")),
        Step(say=f"Tell hvor mange plasser kommaet flyttet seg {direction}.",
             math=f"Kommaet flyttet seg {abs(e)} plasser {direction}",
             show=shift,
             ask=ask("Hvor mange plasser?", "int", abs(e))),
        Step(say=("Store tall får positiv eksponent." if e > 0 else
                  "Små tall (mindre enn 1) får negativ eksponent."),
             math=f"{dec_(value)} = {dec_(mant)} · 10^({n_(e)})" if e < 0 else f"{dec_(value)} = {dec_(mant)} · 10^{e}",
             show=shift),
    ]
    return Problem(task="Skriv tallet på standardform.", expr=f"{dec_(value)} = ?", steps=steps,
                   final=ask("Standardform", "std", [plain_(mant), e]), start={**shift, "to": frm},
                   work=[dec_(value).replace(NBSP, " "), f"{dec_(mant)}·10^{n_(e)}"])


SKILLS = [
    Skill("power", "potenser", "Regne ut potenser",
          "Gjentatt multiplikasjon, negative grunntall og eksponent 0.",
          ["Positive grunntall", "Negative grunntall", "Eksponent 0 og brøk"], gen_power,
          ["grunntall", "eksponent"]),
    Skill("rules", "potenser", "Potensregler",
          "Oppdag reglene ved å skrive ut faktorene.",
          ["Ganging", "Deling", "Potens av potens"], gen_rules, ["potensregler"]),
    Skill("sqrt", "potenser", "Kvadratrot",
          "Kvadratroten er sidelengden i et kvadrat.",
          ["Kvadrattall", "Anslå", "Del opp"], gen_sqrt, ["kvadrattall"]),
    Skill("stdform", "potenser", "Standardform",
          "Store og små tall skrevet med tierpotens.",
          ["Store tall", "Tilbake til vanlig form", "Små tall"], gen_std, ["tierpotens"]),
]
