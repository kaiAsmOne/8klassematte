"""Core building blocks shared by every topic.

A Problem is a task plus a list of Steps. Every Step can carry:
  say  - the explanation (must NOT reveal the answer to its own `ask`)
  math - the line written in the ledger once the step is done
  show - a visual spec the browser draws on the board (see static/app.js)
  ask  - an optional question the pupil answers in guided mode

The same Problem drives all three learning modes:
  worked -> all steps are shown one by one (worked example)
  guided -> the pupil answers each `ask` (faded guidance)
  solo   -> only the final answer is asked, steps are shown afterwards
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Callable

MINUS = "\u2212"
NBSP = "\u00a0"

FORMAT_HINTS = {
    "int": "Skriv et helt tall",
    "num": "Bruk komma som desimaltegn, f.eks. 4,5",
    "frac": "Skriv brøk som 3/4",
    "frac_simplest": "Skriv brøk som 3/4, forkortet så langt det går",
    "factors": "Skriv som 2·2·3 eller 2^2·3",
    "std": "Skriv som 4,5·10^6",
    "expr_n": "Skriv med n, f.eks. 3n+1",
    "sign": "Skriv + eller −",
}


@dataclass
class Step:
    say: str
    math: str = ""
    show: dict | None = None
    ask: dict | None = None


@dataclass
class Problem:
    task: str
    expr: str
    steps: list[Step]
    final: dict
    start: dict | None = None
    work: list[str] = field(default_factory=list)
    """The solution as the pupil would type it: task = ... = answer, one entry per
    link in the chain. Every entry must evaluate to the answer (tests check this).
    Used as the typed example under the input box. Leave empty when the chain
    cannot be typed as plain numbers (letters, ≈)."""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Skill:
    id: str
    topic: str
    title: str
    blurb: str
    levels: list[str]
    gen: Callable[[int, random.Random], Problem]
    keys: list[str] = field(default_factory=list)


def ask(q: str, kind: str, expect, traps=None, fmt: str | None = None, hint: str | None = None) -> dict:
    """hint is shown on a wrong answer that matches no known trap.

    Traps that happen to equal the correct answer (it happens with some number
    combinations, e.g. 2·2 = 2+2) are dropped so they can never confuse the check.
    """
    traps = [(v, m) for v, m in (traps or []) if v is not None and not _same(kind, v, expect)]
    return {
        "hint": hint,
        "q": q,
        "kind": kind,
        "expect": expect,
        "traps": [{"v": v, "msg": m} for v, m in (traps or [])],
        "fmt": fmt or FORMAT_HINTS[kind],
    }


def _same(kind: str, a, b) -> bool:
    try:
        if kind in ("int", "num"):
            return Fraction(str(a)) == Fraction(str(b))
        if kind in ("frac", "frac_simplest"):
            return a[1] != 0 and Fraction(a[0], a[1]) == Fraction(b[0], b[1])
    except (ValueError, TypeError, ZeroDivisionError):
        return False
    return a == b


def n_(x: int) -> str:
    """Integer for display: real minus sign, space as thousands separator from 10 000."""
    s = str(abs(x))
    if abs(x) >= 10000:
        s = f"{abs(x):,}".replace(",", NBSP)
    return (MINUS if x < 0 else "") + s


def p_(x: int) -> str:
    """Integer that may follow an operator: negative numbers get parentheses."""
    return f"({n_(x)})" if x < 0 else n_(x)


def f_(num, den) -> str:
    """Fraction markup understood by the browser: {teller/nevner}."""
    return "{" + f"{num}/{den}" + "}"


def fr_(x: Fraction) -> str:
    return n_(x.numerator) if x.denominator == 1 else f_(n_(x.numerator), x.denominator)


def dec_(x) -> str:
    """Exact decimal with Norwegian comma, no trailing zeros."""
    x = Fraction(x)
    with localcontext() as ctx:
        ctx.prec = 40
        d = (Decimal(x.numerator) / Decimal(x.denominator)).normalize()
    s = format(d, "f")
    whole, _, frac = s.partition(".")
    sign = MINUS if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    if len(whole) > 4:
        whole = f"{int(whole):,}".replace(",", NBSP)
    return sign + whole + ("," + frac if frac else "")


def prime_factors(n: int) -> list[int]:
    out, p = [], 2
    while p * p <= n:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1:
        out.append(n)
    return out


def is_prime(n: int) -> bool:
    return n > 1 and prime_factors(n) == [n]


def power_form(factors: list[int]) -> str:
    """[2, 2, 3, 5] -> '2^2 · 3 · 5'"""
    parts = []
    for p in sorted(set(factors)):
        k = factors.count(p)
        parts.append(f"{p}^{k}" if k > 1 else str(p))
    return " · ".join(parts)


def lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)
