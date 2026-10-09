"""Høsthalvåret 8. trinn, koblet til LK20 MAT01-06 (gjeldende fra 1. august 2026).

Rekkefølgen følger det vanlige oppsettet i skolenes årsplaner:
tall og tallregning (uke 34-47), deretter start på algebra med mønstre.
Den nasjonale læreplanen sier ikke noe om halvår; sjekk skolens årsplan.
"""
from __future__ import annotations

from .topics import fractions, order, patterns, powers, primes, strategies

AIMS = {
    1: "regne med potenser og kvadratrøtter og forklare framgangsmåter og resultat",
    2: "bruke kommutative, assosiative og distributive egenskaper til å utvikle og kommunisere "
       "strategier for hoderegning og skriftlig regning",
    3: "beskrive og utforske faktorisering og primtallsfaktorisering og bruke det i brøkregning",
    4: "utforske og generalisere geometriske mønstre og tallmønstre med egne ord og algebraisk",
}

TOPICS = [
    {"id": "strategier", "title": "Regnestrategier", "weeks": "Uke 35–36", "aims": [2]},
    {"id": "primtall", "title": "Primtall og faktorisering", "weeks": "Uke 37", "aims": [3]},
    {"id": "brok", "title": "Brøk", "weeks": "Uke 38–40", "aims": [3]},
    {"id": "potenser", "title": "Potenser og kvadratrøtter", "weeks": "Uke 42–45", "aims": [1]},
    {"id": "rekkefolge", "title": "Regnerekkefølge", "weeks": "Uke 45–46", "aims": [1, 2]},
    {"id": "monster", "title": "Mønstre og figurtall", "weeks": "Uke 48–50", "aims": [4]},
]

SKILLS = {s.id: s for mod in (strategies, primes, fractions, powers, order, patterns) for s in mod.SKILLS}


def public_curriculum() -> dict:
    return {
        "plan": "LK20 MAT01-06, kompetansemål etter 8. trinn",
        "topics": [
            {**t,
             "aims": [AIMS[a] for a in t["aims"]],
             "skills": [{"id": s.id, "title": s.title, "blurb": s.blurb, "levels": s.levels}
                        for s in SKILLS.values() if s.topic == t["id"]]}
            for t in TOPICS
        ],
    }
