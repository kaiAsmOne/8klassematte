/* Mattelab 8 - browser side.
   The Python server generates problems, checks answers and decides what comes next.
   This file only draws things and remembers progress in localStorage. */
"use strict";

const KEY = "mattelab8.progress.v1";
const $ = (s) => document.querySelector(s);
const MODES = {
  worked: ["Se hvordan", "Følg med steg for steg. Neste oppgave løser vi sammen."],
  guided: ["Sammen", "Ett steg om gangen. Du får hjelp hvis du står fast."],
  solo: ["Alene", "Svar på egen hånd. Fire av fem riktige låser opp neste nivå."],
  review: ["Repetisjon", "Noe du har lært før. Å hente det frem igjen er det som får det til å sitte."],
};
const CHOSEN = {
  guided: "Du har valgt å få hjelp. Trykk «Jeg prøver selv» når du er klar.",
  solo: "Du har valgt å prøve selv. Står du fast, trykk «Hjelp meg» eller «Vis meg».",
};
const RANK = { worked: 0, guided: 1, solo: 2, review: 2 };

let CUR = null;          // curriculum from the server
let SKILL = {};          // skill id -> {skill, topic}
let progress = load();
let S = null;            // current problem session

/* ---------------------------------------------------------------- storage */
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || { skills: {}, solved: 0 }; }
  catch { return { skills: {}, solved: 0 }; }
}
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(progress)); } catch { /* private mode */ }
}
async function api(path, body) {
  const r = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : {});
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
const today = () => new Date().toISOString().slice(0, 10);

/* ---------------------------------------------------------------- maths markup
   {a/b} fraction, ^x or ^(x) superscript, √(x) root, [[x]] highlight, !!x!! struck */
function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function md(src) {
  let s = esc(src)
    .replace(/\[\[/g, "\u0001").replace(/\]\]/g, "\u0002")
    .replace(/!!(.+?)!!/g, "\u0003$1\u0004");
  s = s.replace(/\{([^{}\/]+)\/([^{}]+)\}/g, '<span class="frac"><span>$1</span><span>$2</span></span>');
  s = s.replace(/√\(([^()]*)\)/g, '<span class="sqrt">√<span class="rad">$1</span></span>');
  s = s.replace(/\^\(([^()]*)\)/g, "<sup>$1</sup>").replace(/\^([\w?\u2212-]+)/g, "<sup>$1</sup>");
  return s.replace(/\u0001/g, '<mark class="hl">').replace(/\u0002/g, "</mark>")
          .replace(/\u0003/g, '<s class="strike">').replace(/\u0004/g, "</s>");
}

/* ---------------------------------------------------------------- board
   Every object on the board is a <g data-k="..."> with a stable key. Between steps,
   drawBoard() moves objects that kept their key (FLIP) and pops in the new ones,
   so a pupil sees what changed instead of a new picture. */
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;

const svg = (w, h, body, label = "") =>
  `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}" xmlns="http://www.w3.org/2000/svg">
   <defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
   <line x1="0" y1="0" x2="0" y2="7" class="hatch-line"/></pattern></defs>${body}</svg>`;
const T = (x, y, t, cls = "t-lbl") => `<text x="${x}" y="${y}" class="${cls}">${esc(t)}</text>`;

/* A tactile tile: a face over a darker edge 3 px lower, like a physical block. */
function tile(k, x, y, w, h, cls, label = "", rx = 9, edge = 3) {
  return `<g class="tile ${cls}" data-k="${esc(k)}">` +
    `<rect class="edge" x="${x}" y="${y + edge}" width="${w}" height="${h}" rx="${rx}"/>` +
    `<rect class="face" x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>` +
    (label !== "" && label != null ? `<text x="${x + w / 2}" y="${y + h / 2}">${esc(label)}</text>` : "") + `</g>`;
}
function fracSvg(x, y, n, d, k) {
  return `<g data-k="${k}">` + T(x, y - 12, n) +
    `<line x1="${x - 14}" x2="${x + 14}" y1="${y}" y2="${y}" class="stroke-ink"/>` + T(x, y + 13, d) + `</g>`;
}
function badge(k, x, y, text) {
  const w = 16 + String(text).length * 10;
  return `<g class="badge" data-k="${k}"><rect x="${x - w / 2}" y="${y - 14}" width="${w}" height="28" rx="14"/>` +
    `<text x="${x}" y="${y}">${esc(text)}</text></g>`;
}
function fit(parts, total, min) {
  const sum = parts.reduce((a, b) => a + b, 0);
  const w = parts.map((p) => Math.max(min, (p / sum) * total));
  const k = total / w.reduce((a, b) => a + b, 0);
  return w.map((x) => Math.max(min * 0.8, x * k));
}
const COLS = ["a", "b", "c", "o"];

const R = {
  area(s) {
    const L = 48, Tp = 36, W = 330, H = 200, gap = 4;
    const cw = fit(s.cols, W, 50), rh = fit(s.rows, H, 44);
    let out = "", x = L;
    s.cols.forEach((c, j) => { out += `<g data-k="cl${j}-${c}">${T(x + cw[j] / 2, 16, c, "t-muted")}</g>`; x += cw[j]; });
    let y = Tp;
    s.rows.forEach((r, i) => {
      out += `<g data-k="rl${i}-${r}">${T(L - 20, y + rh[i] / 2, r, "t-muted")}</g>`;
      x = L;
      s.cols.forEach((c, j) => {
        const v = s.cells?.[i]?.[j];
        const cls = v == null ? "empty" : COLS[(i * 2 + j) % 4];
        out += tile(`cell${i}-${j}-${v == null ? "e" : "f"}`, x + gap / 2, y + gap / 2, cw[j] - gap, rh[i] - gap, cls, v ?? "", 12);
        x += cw[j];
      });
      y += rh[i];
    });
    if (s.cut) {
      const full = cw[0], sw = Math.max(26, (s.cut / s.cols[0]) * full), sx = L + full - sw - gap / 2;
      out += `<g class="tile cut" data-k="cut"><rect class="face" x="${sx}" y="${Tp + gap / 2}" width="${sw}" height="${y - Tp - gap}" rx="10"/></g>`;
      out += `<g data-k="cutlbl">${T(sx + sw / 2, y + 22, `−${s.cut}`, "t-err")}</g>`;
      if (s.cutval != null) out += badge("cutval", sx - 60, y + 22, `−${s.cutval}`);
    }
    return svg(L + W + 12, y + (s.cut ? 44 : 14), out, "Arealmodell");
  },

  cards(s) {
    const cw = 64, ch = 52, opw = 30, gpad = 10;
    let x = 14, out = "", trays = "", seen = {};
    s.groups.forEach((g, gi) => {
      const grouped = g.items.length > 1;
      const start = x;
      if (grouped) x += gpad;
      g.items.forEach((v, k) => {
        seen[v] = (seen[v] || 0) + 1;
        out += tile(`c${v}-${seen[v]}`, x, 22, cw, ch, grouped ? COLS[gi % 3] : "plain", v, 12);
        x += cw;
        if (k < g.items.length - 1) { out += `<g data-k="op${gi}-${k}">${T(x + opw / 2, 48, s.op, "t-op")}</g>`; x += opw; }
      });
      if (grouped) {
        x += gpad;
        trays += `<g data-k="tray${gi}"><rect class="tray ${["", "b", "c"][gi % 3]}" x="${start}" y="10" width="${x - start}" height="${ch + 26}" rx="18"/></g>`;
        if (g.sum != null) out += badge(`sum${gi}`, (start + x) / 2, 112, `= ${g.sum}`);
      }
      if (gi < s.groups.length - 1) { out += `<g data-k="gop${gi}">${T(x + opw / 2, 48, s.op, "t-op")}</g>`; x += opw; }
    });
    return svg(x + 14, 132, trays + out, "Tallkort");
  },

  tree(s) {
    let leaf = 0, maxD = 0;
    const nodes = [], edges = [];
    (function walk(n, d, path) {
      maxD = Math.max(maxD, d);
      n._k = path;
      if (n.c) {
        const xs = n.c.map((c, i) => walk(c, d + 1, `${path}-${i}`));
        n._x = (xs[0] + xs[xs.length - 1]) / 2;
        n.c.forEach((c) => edges.push([n, c]));
      } else n._x = leaf++;
      n._d = d; nodes.push(n);
      return n._x;
    })(s.root, 0, "n");
    const dx = 70, dy = 70, ox = 44, oy = 38;
    const X = (n) => ox + n._x * dx, Y = (n) => oy + n._d * dy;
    let out = edges.map(([a, b]) =>
      `<g data-k="e${b._k}"><line x1="${X(a)}" y1="${Y(a) + 22}" x2="${X(b)}" y2="${Y(b) - 22}" class="stroke"/></g>`).join("");
    nodes.forEach((n) => {
      const r = String(n.v).length > 3 ? 28 : 25;
      const cls = n.prime ? "c" : n.c ? "plain" : "plain";
      out += `<g class="tile ${cls}" data-k="${n._k}-${n.v}">` +
        `<circle class="edge" cx="${X(n)}" cy="${Y(n) + 3}" r="${r}"/><circle class="face" cx="${X(n)}" cy="${Y(n)}" r="${r}"/>` +
        `<text x="${X(n)}" y="${Y(n)}">${n.v}</text></g>`;
    });
    return svg(Math.max(leaf - 1, 1) * dx + ox * 2, maxD * dy + oy * 2, out, "Faktortre");
  },

  bars(s) {
    const units = Math.max(1, ...s.rows.map((r) => Math.ceil(r.n / r.d)));
    const W = 310, uw = W / units, bh = 40, L = 58, gap = 3;
    let out = "";
    s.rows.forEach((r, i) => {
      const y = 16 + i * (bh + 26);
      out += fracSvg(26, y + bh / 2, r.n, r.d, `lbl${i}-${r.n}-${r.d}`);
      for (let u = 0; u < units; u++) {
        for (let k = 0; k < r.d; k++) {
          const idx = u * r.d + k, sw = uw / r.d, x = L + u * uw + k * sw;
          const filled = idx < r.n;
          out += tile(`b${i}-${r.d}-${idx}-${filled ? 1 : 0}`, x + gap / 2, y, Math.max(2, sw - gap), bh,
                      filled ? ["a", "b", "c"][i % 3] : "empty", "", Math.min(8, sw / 3), filled ? 3 : 0);
        }
      }
    });
    return svg(L + W + 10, 22 + s.rows.length * (bh + 26), out, "Brøkstriper");
  },

  fracgrid(s) {
    const [n1, d1] = s.a, [n2, d2] = s.b, size = 220, L = 60, Tp = 58, gap = 3;
    const cw = size / d1, rh = size / d2;
    let out = fracSvg(L + size / 2, 24, n1, d1, "fa") + fracSvg(26, Tp + size / 2, n2, d2, "fb");
    for (let c = 0; c < d1; c++) for (let r = 0; r < d2; r++) {
      const inA = c < n1, inB = r < n2;
      const cls = inA && inB ? (s.overlap ? "o" : "a") : inA ? "a" : inB ? "b" : "empty";
      out += tile(`g${c}-${r}-${cls}`, L + c * cw + gap / 2, Tp + r * rh + gap / 2, cw - gap, rh - gap, cls, "", 6, cls === "empty" ? 0 : 2);
    }
    if (s.count) out += `<g data-k="cnt">${T(L + size + 20 + 50, Tp + size / 2 - 14, `${n1 * n2} lilla`)}${T(L + size + 20 + 50, Tp + size / 2 + 14, `av ${d1 * d2} ruter`, "t-muted")}</g>`;
    return svg(L + size + (s.count ? 150 : 20), Tp + size + 14, out, "Rutenett for brøk ganger brøk");
  },

  square(s) {
    const big = s.n2 || s.n, u = Math.min(24, 230 / big), L = 44, Tp = 16, gap = Math.max(1, u * 0.12);
    let out = "";
    const extra = s.target ? s.target - s.n * s.n : 0;
    const ring = [];
    for (let y = 0; y < s.n; y++) ring.push([s.n, y]);
    for (let x = 0; x <= s.n; x++) ring.push([x, s.n]);
    if (s.n2) out += `<g data-k="outline"><rect x="${L - 3}" y="${Tp - 3}" width="${s.n2 * u + 6}" height="${s.n2 * u + 6}" rx="8" class="stroke" stroke-dasharray="6 6"/></g>`;
    for (let x = 0; x < s.n; x++) for (let y = 0; y < s.n; y++)
      out += tile(`q${x}-${y}`, L + x * u + gap / 2, Tp + y * u + gap / 2, u - gap, u - gap, "a", "", Math.min(5, u / 4), u > 12 ? 2 : 0);
    ring.slice(0, extra).forEach(([x, y]) =>
      out += tile(`x${x}-${y}`, L + x * u + gap / 2, Tp + y * u + gap / 2, u - gap, u - gap, "b", "", Math.min(5, u / 4), u > 12 ? 2 : 0));
    const side = s.side ?? (s.n2 ? s.n : "?");
    out += `<g data-k="side-${side}">${T(L - 20, Tp + (s.n * u) / 2, side)}${T(L + (s.n * u) / 2, Tp + big * u + 22, side)}</g>`;
    const right = L + big * u + 22;
    if (s.label != null) out += badge("area", right + 50, Tp + 22, `${s.label} ruter`);
    if (s.target) {
      out += `<g data-k="notes">${T(right + 60, Tp + 22, `${s.n}·${s.n} = ${s.n * s.n}`)}` +
             `${T(right + 60, Tp + 52, `${s.target} ruter`, "t-err")}${T(right + 60, Tp + 82, `${s.n2}·${s.n2} = ${s.n2 * s.n2}`, "t-muted")}</g>`;
    }
    return svg(right + 128, Tp + big * u + 44, out, "Kvadrat");
  },

  shift(s) {
    const bw = 36, L = 18, y = 74, digits = s.digits.split("");
    let out = "";
    const cx = (p) => L + p * bw;
    digits.forEach((d, i) => {
      const marked = s.mark && i === s.mark - 1;
      out += tile(`d${i}`, cx(i) + 3, y - 20, bw - 6, 42, marked ? "b" : "plain", d, 8);
    });
    const comma = (p, cls, k) => `<g data-k="${k}"><text x="${cx(p)}" y="${y + 30}" class="${cls}">,</text></g>`;
    if (s.from !== s.to) {
      out += comma(s.from, "comma-old", "c-old");
      const dir = s.to > s.from ? 1 : -1;
      for (let p = s.from, k = 1; p !== s.to; p += dir, k++) {
        const a = cx(p), b = cx(p + dir);
        out += `<g data-k="hop${p}"><path d="M${a} ${y - 26} Q ${(a + b) / 2} ${y - 54} ${b} ${y - 26}" class="hop" style="--d:${k * 70}ms"/>` +
               T((a + b) / 2, y - 56, k, "t-muted") + `</g>`;
      }
      out += comma(s.to, "comma-new", "c-new");
    } else {
      out += comma(s.from, "comma-new", "c-new");
    }
    return svg(L * 2 + digits.length * bw, y + 40, out, "Kommaet flytter seg");
  },

  pattern(s) {
    const g = 18, gap = 44, Tp = 14, r = 7;
    let x = 16, out = "";
    const dims = s.figs.map((f) => ({
      w: Math.max(...f.dots.map((d) => d[0])) + 1,
      h: Math.max(...f.dots.map((d) => d[1])) + 1,
    }));
    const H = Math.max(...dims.map((d) => d.h)) * g;
    s.figs.forEach((f, i) => {
      f.dots.forEach(([dx, dy, c], j) => {
        const cx = x + dx * g + g / 2, cy = Tp + H - dy * g - g / 2;
        out += `<g data-k="f${i}-${dx}-${dy}"><circle cx="${cx}" cy="${cy}" r="${r}" class="marble ${c}"/>` +
               `<circle cx="${cx - 2.2}" cy="${cy - 2.4}" r="2.2" class="marble-shine"/></g>`;
      });
      out += `<g data-k="fl${i}">${T(x + (dims[i].w * g) / 2, Tp + H + 22, f.label, "t-muted")}</g>`;
      x += dims[i].w * g + gap;
    });
    return svg(x, Tp + H + 40, out, "Figurmønster");
  },

  chips(s) {
    return `<div class="chips">${s.rows.map((r, ri) =>
      `<div class="chip-row">${r.label ? `<span class="lbl">${md(r.label)}</span>` : ""}${r.items.map((it, i) =>
        `<span class="chip${r.cancel.includes(i) ? " x" : ""}" data-k="ch${ri}-${i}">${md(it)}</span>`).join("")}</div>`).join("")}</div>`;
  },

  ladder(s) {
    const rungs = [["( )", "Parenteser"], ["a<sup>n</sup>", "Potenser"], ["· :", "Ganging og deling"], ["+ −", "Pluss og minus"]];
    return `<ol class="ladder">${rungs.map(([sym, name], i) =>
      `<li class="${s.active === i ? "on" : ""}"><b>${sym}</b><span>${name}</span></li>`).join("")}</ol>`;
  },

  ladderpow(s) {
    return `<ul class="powlad">${s.rows.map(([e, v], i) =>
      (i ? `<li class="step">: ${s.base}</li>` : "") +
      `<li class="${v == null ? "q" : ""}" data-k="pw${e}-${v ?? "q"}">${md(`${s.base}^${e}`)} = ${v == null ? "?" : v}</li>`).join("")}</ul>`;
  },
};

let boardType = null;
function drawBoard(spec) {
  const b = $("#board");
  if (!spec || !R[spec.type]) { b.innerHTML = ""; boardType = null; return; }
  const before = new Map();
  if (spec.type === boardType) b.querySelectorAll("[data-k]").forEach((e) => before.set(e.dataset.k, e.getBoundingClientRect()));
  b.innerHTML = R[spec.type](spec);
  const fresh = spec.type !== boardType;
  boardType = spec.type;
  if (REDUCED) return;
  const els = [...b.querySelectorAll("[data-k]")];
  const stagger = Math.max(4, Math.min(40, 600 / Math.max(1, els.length)));
  let i = 0;
  els.forEach((e) => {
    const old = before.get(e.dataset.k);
    if (!old) {
      e.style.setProperty("--d", `${Math.round((fresh ? i++ : i++) * stagger)}ms`);
      e.classList.add("enter");
      return;
    }
    const now = e.getBoundingClientRect();
    const dx = old.left - now.left, dy = old.top - now.top;
    if (Math.abs(dx) + Math.abs(dy) < 1) return;
    const k = e.ownerSVGElement ? e.ownerSVGElement.getScreenCTM().a : 1;
    e.style.transition = "none";
    e.style.transform = `translate(${dx / k}px, ${dy / k}px)`;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      e.style.transition = "transform .5s cubic-bezier(.2,.8,.2,1)";
      e.style.transform = "";
    }));
  });
}

/* ---------------------------------------------------------------- views */
function show(id) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== id));
  window.scrollTo(0, 0);
}

function skillState(id) { return progress.skills?.[id]; }
function skillScore(id) {
  const st = skillState(id), n = SKILL[id]?.skill.levels.length || 1;
  if (!st) return 0;
  if (st.mastered) return 1;
  return Math.min(0.95, ((st.lvl - 1) + (st.hist || []).filter(Boolean).length / 5) / n);
}
function dueCount() {
  const t = today();
  return Object.values(progress.skills || {}).filter((s) => s.mastered && (s.due || "") <= t).length;
}
function ring(frac, label) {
  const r = 19, c = 2 * Math.PI * r;
  return `<span class="ring-wrap"><svg class="ring" viewBox="0 0 44 44" aria-hidden="true">
    <circle class="bg" cx="22" cy="22" r="${r}"/>
    <circle class="fg" cx="22" cy="22" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - frac)}" ${frac ? "" : 'stroke-opacity="0"'}/>
    </svg><span>${label}</span></span>`;
}
const GLYPHS = {
  strategier: `<rect x="2" y="12" width="12" height="12" rx="3" class="g-a"/><rect x="16" y="12" width="12" height="12" rx="3" class="g-a"/><rect x="34" y="12" width="12" height="12" rx="3" class="g-b"/><path d="M4 30h22" class="g-line"/>`,
  primtall: `<path d="M24 12L14 26M24 12l10 14" class="g-line"/><circle cx="24" cy="10" r="7" class="g-b"/><circle cx="13" cy="30" r="6" class="g-c"/><circle cx="35" cy="30" r="6" class="g-c"/>`,
  brok: `<rect x="4" y="8" width="40" height="11" rx="3" class="g-a" opacity=".25"/><rect x="4" y="8" width="20" height="11" rx="3" class="g-a"/><rect x="4" y="24" width="40" height="11" rx="3" class="g-b" opacity=".25"/><rect x="4" y="24" width="30" height="11" rx="3" class="g-b"/>`,
  potenser: `<rect x="6" y="14" width="10" height="10" rx="2" class="g-a"/><rect x="17" y="14" width="10" height="10" rx="2" class="g-a"/><rect x="6" y="25" width="10" height="10" rx="2" class="g-a"/><rect x="17" y="25" width="10" height="10" rx="2" class="g-a"/><text x="33" y="16" class="g-ink">2</text>`,
  rekkefolge: `<rect x="6" y="6" width="36" height="7" rx="3.5" class="g-b"/><rect x="6" y="16" width="30" height="7" rx="3.5" class="g-a" opacity=".55"/><rect x="6" y="26" width="24" height="7" rx="3.5" class="g-a" opacity=".35"/><rect x="6" y="36" width="18" height="7" rx="3.5" class="g-a" opacity=".2"/>`,
  monster: `<circle cx="8" cy="30" r="4" class="g-a"/><circle cx="20" cy="30" r="4" class="g-a"/><circle cx="20" cy="20" r="4" class="g-b"/><circle cx="32" cy="30" r="4" class="g-a"/><circle cx="32" cy="20" r="4" class="g-a"/><circle cx="32" cy="10" r="4" class="g-b"/>`,
};
const glyph = (id) => `<svg viewBox="0 0 48 44">${GLYPHS[id] || ""}</svg>`;

function renderHome() {
  show("home");
  $("#topics").innerHTML = CUR.topics.map((t) => {
    const score = t.skills.reduce((a, s) => a + skillScore(s.id), 0) / t.skills.length;
    const done = t.skills.filter((s) => skillState(s.id)?.mastered).length;
    return `<li><a class="topic-link" href="#/t/${t.id}">
      <span class="t-glyph" aria-hidden="true">${glyph(t.id)}</span>
      <span><span class="t-name">${esc(t.title)}</span><br>
      <span class="t-meta">${esc(t.weeks)}, ${t.skills.length} ${t.skills.length === 1 ? "ferdighet" : "ferdigheter"}</span></span>
      ${ring(score, `${done}/${t.skills.length}`)}
    </a></li>`;
  }).join("");
  const due = dueCount();
  const started = Object.keys(progress.skills || {}).length;
  $("#mix-note").textContent = due ? `${due} ${due === 1 ? "ferdighet er" : "ferdigheter er"} klar for repetisjon`
    : started ? "Blander det du har øvd på" : "Blir tilgjengelig når du har øvd litt";
  $("#mix-btn").classList.toggle("primary", due > 0);
  $("#plan-note").textContent = `${CUR.plan}. Ukene følger et vanlig oppsett i skolenes årsplaner.`;
}

function renderTopic(id) {
  const t = CUR.topics.find((x) => x.id === id);
  if (!t) return (location.hash = "#/");
  show("topic");
  $("#t-glyph").innerHTML = glyph(t.id);
  $("#t-title").textContent = t.title;
  $("#t-weeks").textContent = t.weeks;
  $("#t-aims").innerHTML = `<p class="muted small">Fra læreplanen: eleven skal kunne</p>` +
    t.aims.map((a) => `<p>${esc(a)}</p>`).join("");
  $("#skills").innerHTML = t.skills.map((s) => {
    const st = skillState(s.id);
    const lvl = st?.lvl || 1;
    return `<li class="skill-row">
      <div><h2>${esc(s.title)}</h2><p>${esc(s.blurb)}</p>
      <ol class="levels">${s.levels.map((l, i) => {
        const done = st?.mastered || i + 1 < lvl, now = !st?.mastered && i + 1 === lvl;
        return `<li class="${done ? "done" : now ? "now" : ""}"><b>${done ? "✓" : i + 1}</b>${esc(l)}</li>`;
      }).join("")}</ol></div>
      <div class="go">
        <a class="btn ${st?.mastered ? "" : "primary"}" href="#/s/${s.id}">${st?.mastered ? "Repeter" : st ? "Fortsett" : "Start"}</a>
        ${st?.mastered ? "" : `<a class="btn" href="#/s/${s.id}/solo">Jeg prøver selv</a>`}
      </div>
    </li>`;
  }).join("");
}

/* ---------------------------------------------------------------- practice */
async function startPractice(skillId, want = null) {
  show("practice");
  const back = skillId ? `#/t/${SKILL[skillId].topic.id}` : "#/";
  $("#p-back").href = back;
  $("#p-back span").textContent = skillId ? SKILL[skillId].topic.title : "Alle temaer";
  await nextProblem(skillId, want);
}

async function nextProblem(skillId, want = null) {
  const data = await api("/api/next", { progress, skill: skillId ?? null, want });
  if (data.progress) { progress = data.progress; save(); }
  if (data.empty) {
    S = null;
    $("#switch").hidden = true;
    resetPanel();
    $("#p-skill").textContent = "Blandet repetisjon";
    $("#p-level").textContent = "";
    $("#p-track").innerHTML = "";
    $("#p-mode").textContent = "";
    $("#p-modehelp").textContent = "";
    $("#p-task").textContent = "Her kommer oppgaver fra ferdigheter du har øvd på. Start med et tema først.";
    $("#p-expr").textContent = "";
    drawBoard(null);
    $("#actions").innerHTML = `<a class="btn primary" href="#/">Velg et tema</a>`;
    return;
  }
  S = { data, p: data.problem, step: -1, misses: 0, stepMisses: 0, attempts: 0, requested: skillId ?? null, board: null, done: false };
  begin();
}

function begin() {
  const data = S.data;
  S.step = -1; S.misses = 0; S.stepMisses = 0; S.attempts = 0; S.board = null; S.done = false;
  $("#switch").hidden = false;
  renderHeader();
  resetPanel();
  $("#p-task").textContent = S.p.task;
  $("#p-expr").innerHTML = md(S.p.expr);
  setBoard(S.p.start);
  if (data.mode === "worked") actions([["Vis første steg", workedNext, true]]);
  else if (data.mode === "guided") guidedNext();
  else askFinal();
}

function renderHeader() {
  const d = S.data, st = skillState(d.skill);
  $("#p-skill").textContent = d.skill_title;
  $("#p-level").textContent = `Nivå ${d.level} av ${d.levels}: ${d.level_name}`;
  const hist = st && !st.mastered && d.mode !== "review" ? st.hist || [] : [];
  $("#p-track").innerHTML = d.mode === "solo"
    ? Array.from({ length: 5 }, (_, i) => `<span class="${hist[i] === true ? "ok" : hist[i] === false ? "no" : ""}"></span>`).join("")
    : "";
  const [name, help] = MODES[d.mode];
  $("#p-mode").textContent = d.mode === "review" ? name : "";
  $("#p-mode").className = `mode ${d.mode}`;
  $("#p-modehelp").textContent = d.mode === "review" && d.requested && d.requested !== d.skill
    ? "En oppgave fra et annet tema. Å blande temaer gjør det lettere å huske."
    : (d.pref && d.pref === d.mode && CHOSEN[d.mode]) || help;
  const cur = d.mode === "review" ? "solo" : d.mode;
  document.querySelectorAll("#switch button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.mode === cur)));
  $("#switch").dataset.at = String(["worked", "guided", "solo"].indexOf(cur));
}

/* Pupil picks how to work. More help keeps the problem in front of them;
   less help (or a finished problem) starts a fresh one, since steps may already be visible. */
async function switchMode(want) {
  if (!S) return;
  const cur = S.data.mode === "review" ? "solo" : S.data.mode;
  if (want === cur && !S.done) return;
  if (S.done || RANK[want] >= RANK[cur]) return nextProblem(S.requested ?? S.data.skill, want);
  const res = await api("/api/switch", { token: S.data.token, want, progress });
  progress = res.progress; save();
  S.data = { ...S.data, token: res.token, mode: res.mode, pref: res.pref };
  begin();
}

function resetPanel() {
  $("#ledger").innerHTML = "";
  $("#coach").innerHTML = "";
  $("#feedback").innerHTML = "";
  $("#actions").innerHTML = "";
  $("#answer").hidden = true;
}

function setBoard(spec) {
  if (spec) S.board = spec;
  drawBoard(S.board);
}

/* On small screens the feedback can sit outside the viewport; bring it in. */
function reveal(el) {
  if (!el || !el.innerHTML) return;
  const r = el.getBoundingClientRect();
  if (r.top < 70 || r.bottom > innerHeight) el.scrollIntoView({ block: "center", behavior: REDUCED ? "auto" : "smooth" });
}

function addLine(math, cls = "") {
  if (!math) return;
  const li = document.createElement("li");
  li.className = cls;
  li.innerHTML = md(math);
  $("#ledger").appendChild(li);
}

function actions(list) {
  $("#actions").innerHTML = "";
  list.forEach(([label, fn, primary]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `btn ${primary ? "primary" : ""}`;
    b.textContent = label;
    b.addEventListener("click", fn);
    $("#actions").appendChild(b);
  });
  $("#actions .btn.primary")?.focus({ preventScroll: true });
}

/* worked example */
function workedNext() {
  S.step++;
  const st = S.p.steps[S.step];
  $("#coach").innerHTML = md(st.say);
  addLine(st.math);
  setBoard(st.show);
  const last = S.step === S.p.steps.length - 1;
  actions([[last ? "Nå løser vi en sammen" : "Neste steg", last ? () => finish(true) : workedNext, true]]);
}

/* guided: one ask per step */
function guidedNext() {
  S.step++;
  S.stepMisses = 0;
  if (S.step >= S.p.steps.length) {
    const ok = S.misses <= 1;
    $("#coach").innerHTML = "";
    $("#feedback").innerHTML = ok
      ? `<div class="ok">${checkMark()} Du løste hele oppgaven.</div>`
      : `<div class="note">Ferdig. Vi tar én til sammen, så sitter det bedre.</div>`;
    return finish(ok, ok ? [["Jeg prøver selv", () => nextProblem(S.requested ?? S.data.skill, "solo"), false]] : []);
  }
  const st = S.p.steps[S.step];
  $("#coach").innerHTML = md(st.say);
  setBoard(st.show);
  if (st.ask) {
    askSpec(st.ask, S.step, (res) => {
      if (res.ok) {
        addLine(st.math);
        $("#feedback").innerHTML = `<div class="ok">${checkMark()} Riktig</div>` + (res.msg ? `<div class="note">${md(res.msg)}</div>` : "");
        $("#answer").hidden = true;
        actions([["Neste steg", guidedNext, true]]);
      } else {
        S.misses++; S.stepMisses++;
        if (S.stepMisses >= 2) {
          addLine(st.math, "given");
          $("#answer").hidden = true;
          $("#feedback").innerHTML = `<div class="no">${md(res.msg)}</div><div class="note">Her er steget. Les utregningen og gå videre.</div>`;
          actions([["Neste steg", guidedNext, true]]);
        } else {
          $("#feedback").innerHTML = `<div class="no">${md(res.msg)}</div><div class="note">Prøv igjen.</div>`;
        }
      }
    });
  } else {
    addLine(st.math);
    $("#answer").hidden = true;
    actions([["Neste steg", guidedNext, true]]);
  }
}

/* solo and review: only the final answer */
function askFinal() {
  $("#coach").innerHTML = "";
  askSpec(S.p.final, "final", (res) => {
    S.attempts++;
    if (res.ok) {
      $("#answer").hidden = true;
      const first = S.attempts === 1;
      $("#feedback").innerHTML = `<div class="ok">${checkMark()} ${first ? "Riktig" : "Riktig på andre forsøk"}</div>` +
        (res.msg ? `<div class="note">${md(res.msg)}</div>` : "");
      finish(first, [["Se utregningen", showSolution, false]], "Neste oppgave");
    } else if (S.attempts === 1) {
      $("#feedback").innerHTML = `<div class="no">${md(res.msg)}</div><div class="note">Prøv en gang til.</div>`;
    } else {
      $("#answer").hidden = true;
      $("#feedback").innerHTML = `<div class="no">${md(res.msg)}</div><div class="note">Her er utregningen. Neste oppgave er av samme type.</div>`;
      showSolution();
      finish(false, [["Løs neste sammen", () => nextProblem(S.requested ?? S.data.skill, "guided"), false]]);
    }
  });
}

function showSolution() {
  $("#ledger").innerHTML = "";
  S.p.steps.forEach((st) => addLine(st.math));
  const lastShow = [...S.p.steps].reverse().find((st) => st.show);
  setBoard(lastShow?.show);
  document.querySelectorAll("#actions .btn").forEach((b) => { if (b.textContent === "Se utregningen") b.remove(); });
}

function askSpec(spec, step, onResult) {
  const form = $("#answer"), input = $("#a-in");
  form.hidden = false;
  $("#a-q").innerHTML = md(spec.q);
  const ex = step === "final" ? S.p.example : null;
  const chainable = ["int", "num", "frac", "frac_simplest", "factors", "std"].includes(spec.kind);
  $("#a-fmt").textContent = step === "final" && chainable
    ? `${spec.fmt}. Du kan også skrive hele utregningen med =.` : spec.fmt;
  $("#a-ex").hidden = !ex;
  if (ex) {
    $("#a-ex").innerHTML = ex.task
      ? `Eksempel: for ${md(ex.task)} skriver du <span class="typed">${esc(ex.typed)}</span>`
      : `Eksempel på en annen oppgave: <span class="typed">${esc(ex.typed)}</span>`;
  }
  $("#key-n").hidden = spec.kind !== "expr_n";
  input.value = "";
  input.inputMode = ["int", "num", "sign"].includes(spec.kind) ? "decimal" : "text";
  $("#actions").innerHTML = "";
  form.onsubmit = async (e) => {
    e.preventDefault();
    const answer = input.value.trim();
    if (!answer) return input.focus();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const res = await api("/api/check", { token: S.data.token, step, answer });
      if (res.invalid) {
        $("#feedback").innerHTML = `<div class="note">${md(res.msg)}</div>`;
      } else {
        onResult(res);
      }
      reveal($("#feedback"));
    } finally {
      btn.disabled = false;
      if (!form.hidden) { input.select(); input.focus({ preventScroll: true }); }
    }
  };
  input.focus({ preventScroll: true });
}

async function finish(correct, extra = [], nextLabel = null) {
  S.done = true;
  const res = await api("/api/record", { token: S.data.token, correct, progress });
  progress = res.progress;
  save();
  const d = S.data;
  const again = () => nextProblem(S.requested);
  const label = d.mode === "worked" ? null : nextLabel || (correct ? "Neste oppgave" : "Ny oppgave av samme type");
  if (label) actions([[label, again, true], ...extra]);
  else again();
  if (d.mode === "solo") renderHeader();
  res.events.forEach((ev) => {
    const levels = SKILL[d.skill].skill.levels;
    if (ev === "level_up") toast(`Nytt nivå: ${levels[d.level]}`);
    if (ev === "mastered") toast(`${d.skill_title} er mestret. Den kommer tilbake som repetisjon.`);
    if (ev === "step_back") toast("Vi tar neste oppgave sammen.");
  });
}

const checkMark = () =>
  `<svg class="check-mark" width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="14"/><path d="M8 14.5l4 4 8-9"/></svg>`;

let toastTimer = null;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3800);
}

/* ---------------------------------------------------------------- wiring */
document.querySelectorAll("#keys button").forEach((b) =>
  b.addEventListener("click", () => {
    const i = $("#a-in"), a = i.selectionStart ?? i.value.length, z = i.selectionEnd ?? a;
    i.value = i.value.slice(0, a) + b.dataset.ins + i.value.slice(z);
    i.focus();
    i.setSelectionRange(a + b.dataset.ins.length, a + b.dataset.ins.length);
  }));

document.querySelectorAll("#switch button").forEach((b) =>
  b.addEventListener("click", () => switchMode(b.dataset.mode).catch(fail)));

$("#reset").addEventListener("click", () => {
  if (!confirm("Slette all fremgang på denne enheten?")) return;
  progress = { skills: {}, solved: 0 };
  save();
  renderHome();
});

function route() {
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, id, want] = h.split("/");
  if (kind === "t") return renderTopic(id);
  if (kind === "s" && SKILL[id]) return startPractice(id, ["worked", "guided", "solo"].includes(want) ? want : null).catch(fail);
  if (kind === "mix") return startPractice(null).catch(fail);
  renderHome();
}
function fail(err) {
  console.error(err);
  toast("Fikk ikke kontakt med serveren. Sjekk nettet og prøv igjen.");
}

(async function init() {
  try {
    CUR = await api("/api/curriculum");
  } catch (e) { return fail(e); }
  CUR.topics.forEach((t) => t.skills.forEach((s) => (SKILL[s.id] = { skill: s, topic: t })));
  window.addEventListener("hashchange", route);
  route();
})();
