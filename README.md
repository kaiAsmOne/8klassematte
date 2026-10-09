# Mattelab 8

This is an example of using AI to learn not to just give answer. 

Using topics you dont neccesarily understand, and you dont need to either. 

The goal is to increase our knowledge in math using a visual learning process
Or as an inspiration to do it your way with Ai. If you use Ai to make you learn 
you will have a an advantage. I like both paperversion and digital of learning


Flask web app for 8th grade maths, autumn term (LK20 MAT01-06, valid from 1 Aug 2026).
Python generates every problem, checks every answer and decides what comes next.
The browser only draws and stores progress.

## Run

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python3 app.py

Open http://127.0.0.1:5000. Tests: `python tests/test_engine.py` (generates 300 problems per
skill level and checks that the engine accepts its own answers).

## PythonAnywhere

Its a cheap and simple way to host our webapp online so others can access it. 
Im this far in the README mark down file and i havent test ran it yet.

Same setup as division.thorsrud.io: new web app (Flask, manual config), point the WSGI file at
`app:app`, static mapping `/static/` -> `<project>/static`, and set a real secret:

    MATTELAB_SECRET=<long random string>

in the WSGI file before the import (`os.environ[...] = ...`). The secret signs the problem tokens.

## Layout

    app.py                     routes: /api/curriculum, /api/next, /api/check, /api/record
    engine/core.py             Problem, Step, Skill, ask(), number formatting
    engine/answers.py          parses what the pupil typed, misconception feedback
    engine/scheduler.py        worked -> guided -> solo -> spaced review
    engine/curriculum.py       topics, weeks, competence aims
    engine/topics/*.py         one generator per skill
    static/app.js              board renderers (SVG/HTML), practice flow
    tests/test_engine.py

## Adding a skill

Write a function `gen(level, rng) -> Problem` in a topic file and add a `Skill(...)` to that
file's `SKILLS` list. A Problem is a list of Steps; each Step has:

- `say`: explanation. Must not contain the answer to its own `ask`.
- `math`: the ledger line shown once the step is done.
- `show`: a board spec, e.g. `{"type": "bars", "rows": [{"n": 3, "d": 4}]}`.
- `ask`: `ask(question, kind, expected, traps, hint=...)`.

Kinds: `int`, `num`, `frac`, `frac_simplest`, `factors`, `std`, `expr_n`, `sign`.
Traps are `(wrong_value, explanation)` pairs for known misconceptions.

The same Problem feeds all modes, so one generator gives you a worked example, a guided
walkthrough and a solo question for free.

Board types in app.js: area, cards, tree, bars, fracgrid, square, shift, pattern, chips,
ladder, ladderpow. A new visual means a new function in the `R` object.

## Learning design

- Worked example first, then two guided problems with step prompts (faded guidance).
- Free-text answers, no multiple choice (generation over recognition).
- Known wrong answers get a specific explanation (misconception feedback).
- Two attempts in solo; after that the full solution and a new problem of the same type.
- Mastery: 4 of the last 5 solo answers correct unlocks the next level.
  Two misses in a row gives one more guided problem.
- Mastered skills return after 1, 3, 7, 14, 30 days and are mixed into other practice ~25% of
  the time (spaced repetition, interleaving).
- Every problem has a picture next to the symbols (dual coding).

## Decisions that will constrain later

- Progress lives in localStorage on one device. A leaderboard, teacher view or the Discord bot
  sharing progress needs server-side storage (SQLite on PythonAnywhere is enough). The
  scheduler already works on a plain dict, so only where it is stored changes.
- The server is stateless and trusts the `correct` flag from the browser. Fine for practice,
  not for anything competitive.
- UI text is bokmål, written inside the generators. Nynorsk means extracting strings.