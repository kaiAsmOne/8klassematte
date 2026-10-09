"""Typed example under the answer box: a different problem of the same kind,
written the way the pupil can type it, so pattern-spotters see what we want."""
from __future__ import annotations

import random

from .answers import answer_text
from .core import Skill


def example_for(skill: Skill, level: int, current_expr: str, rng: random.Random | None = None) -> dict | None:
    rng = rng or random.Random()
    sib = None
    for _ in range(8):
        sib = skill.gen(level, rng)
        if sib.expr != current_expr:
            break
    if sib is None:
        return None
    if sib.work:
        return {"typed": " = ".join(sib.work), "task": None}
    typed = answer_text(sib.final)
    return {"typed": typed, "task": sib.expr} if typed else None
