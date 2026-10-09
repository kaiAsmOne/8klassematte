"""Parse what the pupil typed and compare it with the expected answer.

check(spec, raw) returns {"ok": bool, "msg": str, "invalid": bool}.
  invalid=True means we could not read the input at all; the browser
  does not count that as an attempt.

Traps are known wrong answers (typical misconceptions). When the pupil
hits one, they get the explanation for that specific mistake instead of
a generic "wrong".
"""
from __future__ import annotations

import ast
import operator
import re
from collections import Counter
from fractions import Fraction

from .core import dec_, fr_, is_prime, prime_factors

# ---------------------------------------------------------------- normalise

def norm(raw: str) -> str:
    s = (raw or "").strip()
    for ch in "\u2212\u2013\u2014":
        s = s.replace(ch, "-")
    for ch in "*×⋅∙•":
        s = s.replace(ch, "·")
    s = s.replace("²", "^2").replace("³", "^3").replace(":", "/")
    return s


def parse_number(raw: str) -> Fraction | None:
    s = norm(raw).replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        return Fraction(s)
    return None


def parse_frac(raw: str):
    """Returns (value, written_numerator, written_denominator) or None."""
    s = norm(raw).replace(",", ".")
    m = re.fullmatch(r"\s*([+-]?)\s*(\d+)\s+(\d+)\s*/\s*(\d+)\s*", s)  # blandet tall 1 1/2
    if m:
        sign, w, n, d = m.groups()
        if int(d) == 0:
            return None
        num = int(w) * int(d) + int(n)
        num = -num if sign == "-" else num
        return Fraction(num, int(d)), num, int(d)
    m = re.fullmatch(r"\s*([+-]?)\s*(\d+)\s*/\s*([+-]?)\s*(\d+)\s*", s)
    if m:
        s1, n, s2, d = m.groups()
        if int(d) == 0:
            return None
        num = int(n) * (-1 if s1 == "-" else 1) * (-1 if s2 == "-" else 1)
        return Fraction(num, int(d)), num, int(d)
    v = parse_number(raw)
    if v is not None and v.denominator == 1:
        return v, v.numerator, 1
    return None


def parse_factors(raw: str) -> list[int] | None:
    s = norm(raw).replace(" ", "").replace("x", "·")
    if not s:
        return None
    out = []
    for part in s.split("·"):
        m = re.fullmatch(r"(\d+)(?:\^\(?(\d+)\)?)?", part)
        if not m:
            return None
        base, exp = int(m.group(1)), int(m.group(2) or 1)
        if exp > 30:
            return None
        out += [base] * exp
    return out


def parse_std(raw: str):
    """'4,5·10^6' -> (Fraction(9, 2), 6)"""
    s = norm(raw).replace(" ", "").replace(",", ".")
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)[eE]([+-]?\d+)", s)
    if not m:
        m = re.fullmatch(r"(?:([+-]?\d+(?:\.\d+)?)·?)?10\^\(?([+-]?\d+)\)?", s)
    if not m:
        return None
    mant = Fraction(m.group(1)) if m.group(1) else Fraction(1)
    return mant, int(m.group(2))


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow}


def _eval(node, n):
    if isinstance(node, ast.Expression):
        return _eval(node.body, n)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return Fraction(node.value)
    if isinstance(node, ast.Name) and node.id == "n":
        return Fraction(n)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand, n)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval(node.left, n), _eval(node.right, n)
        if isinstance(node.op, ast.Pow):
            if b.denominator != 1 or abs(b) > 6:
                raise ValueError("eksponent")
            return a ** int(b)
        return _OPS[type(node.op)](a, b)
    raise ValueError("ikke tillatt")


def parse_expr_n(raw: str, ns=range(1, 7)) -> list[Fraction] | None:
    """Pupil's formula in n, evaluated safely for n = 1..6."""
    s = norm(raw).lower().replace(" ", "").replace("·", "*").replace("^", "**").replace(",", ".")
    s = re.sub(r"(\d)(n|\()", r"\1*\2", s)
    s = re.sub(r"(n|\))(\d|n|\()", r"\1*\2", s)
    if not s or not re.fullmatch(r"[0-9n+\-*/().]+", s) or "n" not in s:
        return None
    try:
        tree = ast.parse(s, mode="eval")
        return [_eval(tree, k) for k in ns]
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None


def parse_sign(raw: str) -> str | None:
    s = norm(raw).lower()
    if s in {"+", "pluss", "positiv", "positivt"}:
        return "+"
    if s in {"-", "minus", "negativ", "negativt"}:
        return "-"
    return None


# ------------------------------------------------------------------ check

def _res(ok, msg="", invalid=False):
    return {"ok": ok, "msg": msg, "invalid": invalid}


def _trap(spec, value):
    for t in spec.get("traps", []):
        v = t["v"]
        if isinstance(v, list) and len(v) == 2 and spec["kind"].startswith("frac"):
            v = Fraction(v[0], v[1])
        elif isinstance(v, (int, str)) and spec["kind"] in ("int", "num"):
            v = Fraction(str(v))
        elif isinstance(v, list) and spec["kind"] == "expr_n":
            v = [Fraction(x) for x in v]
        if v == value:
            return t["msg"]
    return None


# ------------------------------------------------------------ chains
# A pupil may type the whole working: "16 + 23 + 84 = (16 + 84) + 23 = 123".
# The last part is checked as the answer; every earlier part is evaluated and
# must equal it, because "=" means "is the same amount as".

CHAIN_KINDS = {"int", "num", "frac", "frac_simplest", "factors", "std"}


def _sqrt(v: Fraction) -> Fraction:
    import math
    if v < 0:
        raise ValueError("rot")
    rn, rd = math.isqrt(v.numerator), math.isqrt(v.denominator)
    if rn * rn == v.numerator and rd * rd == v.denominator:
        return Fraction(rn, rd)
    raise ValueError("ikke eksakt")


def _eval_num(node):
    if isinstance(node, ast.Expression):
        return _eval_num(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval_num(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" \
            and len(node.args) == 1 and not node.keywords:
        return _sqrt(_eval_num(node.args[0]))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval_num(node.left), _eval_num(node.right)
        if isinstance(node.op, ast.Pow):
            if b.denominator != 1 or abs(b) > 12 or abs(a) > 10 ** 6:
                raise ValueError("eksponent")
            return a ** int(b)
        return _OPS[type(node.op)](a, b)
    raise ValueError("ikke tillatt")


def evaluate(text: str) -> Fraction | None:
    """Exact value of a typed arithmetic expression, or None if it is not one."""
    s = norm(text)
    s = re.sub(r"(?<=\d)[ \u00a0](?=\d{3}(?!\d))", "", s)
    s = s.replace(",", ".").replace("·", "*").replace("^", "**").replace("x", "*")
    s = re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", s).replace("√", "sqrt")
    s = re.sub(r"(\d|\))\s*\(", r"\1*(", s)
    s = re.sub(r"\)\s*(\d)", r")*\1", s)
    if not s.strip() or not re.fullmatch(r"[0-9+\-*/(). sqrt]+", s):
        return None
    try:
        return _eval_num(ast.parse(s.strip(), mode="eval"))
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None


def target_value(spec) -> Fraction | None:
    k, e = spec["kind"], spec["expect"]
    if k in ("int", "num"):
        return Fraction(str(e))
    if k in ("frac", "frac_simplest"):
        return Fraction(e[0], e[1])
    if k == "factors":
        return Fraction(e)
    if k == "std":
        return Fraction(e[0]) * Fraction(10) ** e[1]
    return None


def show_value(v: Fraction) -> str:
    d = v.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    return dec_(v) if d == 1 else fr_(v)


def _check_chain(spec: dict, parts: list[str]) -> dict:
    last = parts[-1]
    res = check(spec, last)
    if res["invalid"]:
        if evaluate(last) is not None:
            return _res(False, "Avslutt utregningen med svaret: «… = svaret».", True)
        return res
    values = [evaluate(p) for p in parts]
    target = target_value(spec)
    if res["ok"]:
        for p, v in zip(parts[:-1], values[:-1]):
            if v is not None and v != target:
                return _res(False, f"Svaret er riktig, men «{p.strip()}» blir {show_value(v)}, ikke "
                                   f"{show_value(target)}. Likhetstegnet betyr at begge sider er like mye.")
        return _res(True, (res["msg"] + " " if res["msg"] else "") + "Hele utregningen stemmer.")
    for (a, va), (b, vb) in zip(zip(parts, values), zip(parts[1:], values[1:])):
        if va is not None and vb is not None and va != vb:
            if parse_number(b) is not None:
                return _res(False, f"Her gikk det galt: «{a.strip()}» blir {show_value(va)}, ikke {b.strip()}.")
            return _res(False, f"Her gikk det galt: «{a.strip()}» blir {show_value(va)}, "
                               f"men «{b.strip()}» blir {show_value(vb)}.")
    return res


def check(spec: dict, raw: str) -> dict:
    kind, expect = spec["kind"], spec["expect"]
    if "=" in (raw or "") and kind in CHAIN_KINDS:
        parts = [p for p in raw.split("=") if p.strip()]
        if len(parts) > 1:
            return _check_chain(spec, parts)
        raw = parts[0] if parts else ""
    unreadable = _res(False, f"Jeg klarer ikke å lese svaret. {spec.get('fmt', '')}.", True)

    if kind in ("int", "num"):
        v = parse_number(raw)
        if v is None:
            pf = parse_frac(raw)
            v = pf[0] if pf else None
        if v is None:
            return unreadable
        if v == Fraction(str(expect)):
            return _res(True)
        return _res(False, _trap(spec, v) or spec.get("hint") or "Ikke riktig ennå.")

    if kind in ("frac", "frac_simplest"):
        p = parse_frac(raw)
        if p is None:
            return unreadable
        v, wn, wd = p
        target = Fraction(expect[0], expect[1])
        if v == target:
            reduced = Fraction(wn, wd)
            if (reduced.numerator, reduced.denominator) == (wn, wd):
                return _res(True)
            if kind == "frac_simplest":
                return _res(False, "Riktig verdi, men brøken kan forkortes mer.")
            return _res(True, f"Riktig verdi! Den kan forkortes til {fr_(target)}.")
        return _res(False, _trap(spec, v) or spec.get("hint") or "Ikke riktig ennå.")

    if kind == "factors":
        fs = parse_factors(raw)
        if fs is None:
            return unreadable
        prod = 1
        for f in fs:
            prod *= f
        if prod != expect:
            return _res(False, f"Faktorene dine ganget sammen blir {prod}, ikke {expect}.")
        bad = sorted({f for f in fs if not is_prime(f)})
        if bad:
            return _res(False, f"Produktet stemmer, men {bad[0]} er ikke et primtall. Del det opp videre.")
        if Counter(fs) == Counter(prime_factors(expect)):
            return _res(True)
        return _res(False, spec.get("hint") or "Ikke riktig ennå.")

    if kind == "std":
        p = parse_std(raw)
        if p is None:
            return unreadable
        mant, exp = p
        want_m, want_e = Fraction(expect[0]), expect[1]
        if mant * Fraction(10) ** exp == want_m * Fraction(10) ** want_e:
            if 1 <= abs(mant) < 10:
                return _res(True)
            return _res(False, "Verdien stemmer, men i standardform skal tallet foran 10-potensen være mellom 1 og 10.")
        if mant == want_m and exp == -want_e:
            return _res(False, "Sjekk fortegnet på eksponenten: store tall får positiv, små tall negativ eksponent.")
        if mant == want_m:
            return _res(False, "Tallet foran er riktig, men eksponenten stemmer ikke. Tell plassene på nytt.")
        return _res(False, spec.get("hint") or "Ikke riktig ennå.")

    if kind == "expr_n":
        vals = parse_expr_n(raw)
        if vals is None:
            return unreadable
        want = [Fraction(x) for x in expect]
        if vals == want:
            return _res(True)
        t = _trap(spec, vals)
        if t:
            return _res(False, t)
        for k, (a, b) in enumerate(zip(vals, want), start=1):
            if a != b:
                return _res(False, f"Sjekk formelen: med n = {k} gir den {dec_(a)}, men figur {k} har {dec_(b)}.")

    if kind == "sign":
        s = parse_sign(raw)
        if s is None:
            return unreadable
        if s == expect:
            return _res(True)
        return _res(False, "Tell minustegnene en gang til.")

    return unreadable


# ------------------------------------------------------------ answer text

def answer_text(spec: dict) -> str | None:
    """The expected answer as a pupil would type it."""
    k, e = spec["kind"], spec["expect"]
    if k == "int":
        return str(e).replace("-", "\u2212")
    if k == "num":
        return dec_(Fraction(str(e)))
    if k in ("frac", "frac_simplest"):
        return (f"{e[0]}/{e[1]}" if e[1] != 1 else str(e[0])).replace("-", "\u2212")
    if k == "factors":
        from .core import power_form
        return power_form(prime_factors(e)).replace(" ", "")
    if k == "std":
        return f"{dec_(Fraction(e[0]))}·10^{e[1]}".replace("-", "\u2212")
    if k == "sign":
        return "+" if e == "+" else "\u2212"
    if k == "expr_n":
        vals = [Fraction(x) for x in e]
        d1 = [b - a for a, b in zip(vals, vals[1:])]
        if len(set(d1)) == 1:
            a, b = d1[0], vals[0] - d1[0]
            head = "n" if a == 1 else f"{a}n"
            return head if b == 0 else f"{head} + {b}" if b > 0 else f"{head} \u2212 {-b}"
        d2 = [b - a for a, b in zip(d1, d1[1:])]
        if len(set(d2)) == 1 and d2[0] == 2 and d1[0] == 3:
            c = vals[0] - 1
            return "n^2" if c == 0 else f"n^2 + {c}"
    return None
