// Piano cartesiano su <canvas>: trascina per spostare, rotella / pizzico per lo zoom,
// punti trascinabili ("maniglie") per le dimostrazioni interattive.

class Grafico {
  constructor(canvas, vista = {}, opzioni = {}) {
    this.c = canvas;
    this.ctx = canvas.getContext('2d');
    this.v = { xmin: -5, xmax: 5, ymin: -4, ymax: 4, ...vista };
    this.opz = { pi: false, zoom: true, sposta: true, proporzionale: false, ...opzioni };
    this.disegna = () => {};
    this.maniglie = [];
    this.alPassaggio = null;
    this._coord = canvas.parentElement.querySelector('.coordinate');
    this._ptr = new Map();
    this._ascolta();
    new ResizeObserver(() => this.ridisegna()).observe(canvas);
  }

  col(nome) { return getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || nome; }
  get W() { return this.c.clientWidth; }
  get H() { return this.c.clientHeight; }
  px(x) { return (x - this.v.xmin) / (this.v.xmax - this.v.xmin) * this.W; }
  py(y) { return (this.v.ymax - y) / (this.v.ymax - this.v.ymin) * this.H; }
  ux(px) { return this.v.xmin + px / this.W * (this.v.xmax - this.v.xmin); }
  uy(py) { return this.v.ymax - py / this.H * (this.v.ymax - this.v.ymin); }

  imposta(vista) { Object.assign(this.v, vista); this.ridisegna(); }

  ridisegna() {
    if (this._rq) return;
    this._rq = requestAnimationFrame(() => { this._rq = null; this._disegna(); });
  }

  _disegna() {
    const dpr = window.devicePixelRatio || 1, W = this.W, H = this.H;
    if (!W || !H) return;
    if (this.c.width !== Math.round(W * dpr) || this.c.height !== Math.round(H * dpr)) {
      this.c.width = Math.round(W * dpr); this.c.height = Math.round(H * dpr);
    }
    const g = this.ctx;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    this._assi();
    this.disegna(this);
    for (const m of this.maniglie) {
      const p = m.pos();
      this.punto(p.x, p.y, { colore: m.colore || this.col('--accento'), r: 7, anello: true, etichetta: m.etichetta });
    }
  }

  _passo(intervallo, pixel, minPx = 70) {
    const grezzo = intervallo * minPx / pixel;
    if (this.opz.pi) {
      const mult = [Math.PI / 6, Math.PI / 4, Math.PI / 2, Math.PI, 2 * Math.PI, 4 * Math.PI, 8 * Math.PI];
      const s = mult.find(m => m >= grezzo);
      if (s) return s;
    }
    const p = Math.pow(10, Math.floor(Math.log10(grezzo)));
    for (const m of [1, 2, 5, 10]) if (m * p >= grezzo) return m * p;
    return 10 * p;
  }

  _etichetta(v, passo, asseX) {
    if (asseX && this.opz.pi && Math.abs(passo / Math.PI - Math.round(passo / Math.PI * 12) / 12) < 1e-9) {
      return frazionePi(v);
    }
    const dec = Math.max(0, -Math.floor(Math.log10(passo) + 1e-9));
    return (Math.abs(v) < passo / 1e6 ? 0 : v).toFixed(dec).replace('-', '−').replace('.', ',');
  }

  _assi() {
    const g = this.ctx, W = this.W, H = this.H, v = this.v;
    const sx = this._passo(v.xmax - v.xmin, W), sy = this._passo(v.ymax - v.ymin, H, 50);
    g.lineWidth = 1;
    g.strokeStyle = this.col('--griglia');
    g.beginPath();
    for (let x = Math.ceil(v.xmin / sx) * sx; x <= v.xmax; x += sx) { const p = Math.round(this.px(x)) + .5; g.moveTo(p, 0); g.lineTo(p, H); }
    for (let y = Math.ceil(v.ymin / sy) * sy; y <= v.ymax; y += sy) { const p = Math.round(this.py(y)) + .5; g.moveTo(0, p); g.lineTo(W, p); }
    g.stroke();
    const X0 = Math.min(Math.max(this.px(0), 0), W), Y0 = Math.min(Math.max(this.py(0), 0), H);
    g.strokeStyle = this.col('--assi');
    g.lineWidth = 1.2;
    g.beginPath();
    g.moveTo(0, Math.round(Y0) + .5); g.lineTo(W, Math.round(Y0) + .5);
    g.moveTo(Math.round(X0) + .5, 0); g.lineTo(Math.round(X0) + .5, H);
    g.stroke();
    g.fillStyle = this.col('--inchiostro-2');
    g.font = '11px ' + this.col('--mono');
    g.textAlign = 'center'; g.textBaseline = 'top';
    const yt = Y0 > H - 18 ? Y0 - 16 : Y0 + 4;
    for (let x = Math.ceil(v.xmin / sx) * sx; x <= v.xmax; x += sx) {
      if (Math.abs(x) < sx / 1e6) continue;
      g.fillText(this._etichetta(x, sx, true), this.px(x), yt);
    }
    g.textAlign = X0 > W - 40 ? 'right' : 'left'; g.textBaseline = 'middle';
    const xt = X0 > W - 40 ? X0 - 5 : X0 + 5;
    for (let y = Math.ceil(v.ymin / sy) * sy; y <= v.ymax; y += sy) {
      if (Math.abs(y) < sy / 1e6) continue;
      g.fillText(this._etichetta(y, sy, false), xt, this.py(y));
    }
  }

  // --- primitive di disegno (coordinate matematiche)

  curva(f, { colore = this.col('--f'), spessore = 2.5, tratteggio = null, da = -Infinity, a = Infinity, alfa = 1 } = {}) {
    const g = this.ctx, W = this.W, H = this.H;
    const passi = Math.ceil(W * 1.5);
    const x0 = Math.max(this.v.xmin, da), x1 = Math.min(this.v.xmax, a);
    if (x1 <= x0) return;
    g.save();
    g.globalAlpha = alfa;
    g.strokeStyle = colore; g.lineWidth = spessore; g.lineJoin = 'round'; g.lineCap = 'round';
    g.setLineDash(tratteggio || []);
    g.beginPath();
    let prima = true, yPrec = null;
    const n = Math.max(2, Math.ceil(passi * (x1 - x0) / (this.v.xmax - this.v.xmin)));
    for (let i = 0; i <= n; i++) {
      const x = x0 + (x1 - x0) * i / n;
      const y = f(x);
      if (!Number.isFinite(y)) { prima = true; yPrec = null; continue; }
      let Y = this.py(y);
      // salto verticale (asintoto): spezza la linea
      if (yPrec != null && Math.abs(Y - yPrec) > H * 1.5 && ((Y < 0 && yPrec > H) || (Y > H && yPrec < 0))) prima = true;
      Y = Math.max(-H * 4, Math.min(H * 5, Y));
      const X = this.px(x);
      if (prima) { g.moveTo(X, Y); prima = false; } else g.lineTo(X, Y);
      yPrec = Y;
    }
    g.stroke();
    g.restore();
  }

  parametrica(fx, fy, t0, t1, { colore = this.col('--f'), spessore = 2.5, tratteggio = null, alfa = 1, n = 600 } = {}) {
    const g = this.ctx;
    g.save();
    g.globalAlpha = alfa;
    g.strokeStyle = colore; g.lineWidth = spessore; g.lineJoin = 'round'; g.lineCap = 'round';
    g.setLineDash(tratteggio || []);
    g.beginPath();
    let prima = true;
    for (let i = 0; i <= n; i++) {
      const t = t0 + (t1 - t0) * i / n, X = this.px(fx(t)), Y = this.py(fy(t));
      if (!Number.isFinite(X) || !Number.isFinite(Y)) { prima = true; continue; }
      if (prima) { g.moveTo(X, Y); prima = false; } else g.lineTo(X, Y);
    }
    g.stroke();
    g.restore();
  }

  // retta per (x0, y0) con pendenza m
  retta(x0, y0, m, opz = {}) {
    if (!Number.isFinite(m)) return this.verticale(x0, opz);
    const { da = this.v.xmin, a = this.v.xmax } = opz;
    this.segmento(da, y0 + m * (da - x0), a, y0 + m * (a - x0), opz);
  }

  segmento(x1, y1, x2, y2, { colore = this.col('--inchiostro'), spessore = 1.6, tratteggio = null, alfa = 1 } = {}) {
    const g = this.ctx;
    g.save();
    g.globalAlpha = alfa;
    g.strokeStyle = colore; g.lineWidth = spessore; g.setLineDash(tratteggio || []);
    g.beginPath(); g.moveTo(this.px(x1), this.py(y1)); g.lineTo(this.px(x2), this.py(y2)); g.stroke();
    g.restore();
  }

  verticale(x, opz = {}) { this.segmento(x, this.v.ymin, x, this.v.ymax, opz); }
  orizzontale(y, opz = {}) { this.segmento(this.v.xmin, y, this.v.xmax, y, opz); }

  fascia(x1, x2, colore, alfa = .08) {
    const g = this.ctx;
    g.save(); g.globalAlpha = alfa; g.fillStyle = colore;
    g.fillRect(this.px(x1), 0, this.px(x2) - this.px(x1), this.H);
    g.restore();
  }

  punto(x, y, { colore = this.col('--inchiostro'), r = 5, vuoto = false, anello = false, etichetta = null, sotto = false, forma = 'cerchio' } = {}) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const g = this.ctx, X = this.px(x), Y = this.py(y);
    g.save();
    g.beginPath();
    if (forma === 'rombo') { g.moveTo(X, Y - r * 1.25); g.lineTo(X + r * 1.25, Y); g.lineTo(X, Y + r * 1.25); g.lineTo(X - r * 1.25, Y); g.closePath(); }
    else if (forma === 'quadrato') g.rect(X - r, Y - r, 2 * r, 2 * r);
    else g.arc(X, Y, r, 0, 2 * Math.PI);
    if (vuoto) { g.fillStyle = this.col('--carta'); g.fill(); g.lineWidth = 2; g.strokeStyle = colore; g.stroke(); }
    else { g.fillStyle = colore; g.fill(); g.lineWidth = 2; g.strokeStyle = this.col('--carta'); g.stroke(); }
    if (anello) { g.beginPath(); g.arc(X, Y, r + 4, 0, 2 * Math.PI); g.strokeStyle = colore; g.globalAlpha = .35; g.lineWidth = 2; g.stroke(); g.globalAlpha = 1; }
    if (etichetta) this.testo(x, y, etichetta, { colore, dy: sotto ? r + 16 : -(r + 9) });
    g.restore();
  }

  testo(x, y, s, { colore = this.col('--inchiostro'), dx = 0, dy = 0, allinea = 'center', dimensione = 13 } = {}) {
    const g = this.ctx;
    g.save();
    g.font = `600 ${dimensione}px ` + this.col('--sans');
    g.textAlign = allinea; g.textBaseline = 'middle';
    const X = this.px(x) + dx, Y = this.py(y) + dy;
    g.lineWidth = 4; g.strokeStyle = this.col('--carta'); g.strokeText(s, X, Y);
    g.fillStyle = colore; g.fillText(s, X, Y);
    g.restore();
  }

  // inquadra: x fissato, y dai valori della funzione (scarta gli estremi)
  inquadra(funzioni, xmin, xmax, puntiExtra = []) {
    const ys = [];
    for (const f of funzioni) {
      for (let i = 0; i <= 400; i++) {
        const y = f(xmin + (xmax - xmin) * i / 400);
        if (Number.isFinite(y)) ys.push(y);
      }
    }
    for (const p of puntiExtra) if (Number.isFinite(p)) ys.push(p);
    ys.sort((a, b) => a - b);
    const extra = puntiExtra.filter(Number.isFinite);
    // con punti notevoli: inquadro soprattutto loro (gli asintoti verticali non devono schiacciare tutto)
    const q = extra.length ? .2 : .05;
    let lo = ys.length ? ys[Math.floor(ys.length * q)] : -1;
    let hi = ys.length ? ys[Math.ceil(ys.length * (1 - q)) - 1] : 1;
    for (const p of extra) { lo = Math.min(lo, p); hi = Math.max(hi, p); }
    if (extra.length) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }   // l'asse x resta sempre in vista
    if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
    const m = (hi - lo) * (extra.length ? .6 : .18);
    this.imposta({ xmin, xmax, ymin: lo - m, ymax: hi + m });
  }

  // --- interazione

  _ascolta() {
    const c = this.c;
    const pos = e => { const r = c.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    c.addEventListener('pointerdown', e => {
      c.setPointerCapture(e.pointerId);
      const [X, Y] = pos(e);
      this._ptr.set(e.pointerId, [X, Y]);
      if (this._ptr.size === 1) {
        this._presa = null;
        for (const m of this.maniglie) {
          const p = m.pos();
          if (Math.hypot(this.px(p.x) - X, this.py(p.y) - Y) < 16) { this._presa = m; break; }
        }
      }
    });
    c.addEventListener('pointermove', e => {
      const [X, Y] = pos(e);
      if (this._coord) this._coord.textContent = `x = ${num(this.ux(X), 4)}   y = ${num(this.uy(Y), 4)}`;
      if (this.alPassaggio) this.alPassaggio(this.ux(X), this.uy(Y));
      if (!this._ptr.has(e.pointerId)) {
        const sopra = this.maniglie.some(m => { const p = m.pos(); return Math.hypot(this.px(p.x) - X, this.py(p.y) - Y) < 16; });
        c.style.cursor = sopra ? 'pointer' : '';
        return;
      }
      const [X0, Y0] = this._ptr.get(e.pointerId);
      if (this._ptr.size === 2) {
        const [a, b] = [...this._ptr.values()];
        const d0 = Math.hypot(a[0] - b[0], a[1] - b[1]);
        this._ptr.set(e.pointerId, [X, Y]);
        const [a2, b2] = [...this._ptr.values()];
        const d1 = Math.hypot(a2[0] - b2[0], a2[1] - b2[1]);
        if (d0 > 0 && this.opz.zoom) this._zoom((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2, d0 / d1);
        return;
      }
      this._ptr.set(e.pointerId, [X, Y]);
      if (this._presa) { this._presa.sposta(this.ux(X), this.uy(Y)); this.ridisegna(); return; }
      if (!this.opz.sposta) return;
      const dx = (X - X0) / this.W * (this.v.xmax - this.v.xmin), dy = (Y - Y0) / this.H * (this.v.ymax - this.v.ymin);
      this.v.xmin -= dx; this.v.xmax -= dx; this.v.ymin += dy; this.v.ymax += dy;
      this.ridisegna();
    });
    const fine = e => { this._ptr.delete(e.pointerId); if (!this._ptr.size) this._presa = null; };
    c.addEventListener('pointerup', fine);
    c.addEventListener('pointercancel', fine);
    c.addEventListener('pointerleave', () => { if (this._coord) this._coord.textContent = ''; if (this.alPassaggio) this.alPassaggio(null, null); });
    c.addEventListener('wheel', e => {
      // rotella semplice = scorre la pagina; ctrl/⌘ + rotella o pizzico sul trackpad = zoom
      if (!this.opz.zoom || !(e.ctrlKey || e.metaKey || e.altKey)) return;
      e.preventDefault();
      const [X, Y] = pos(e);
      this._zoom(X, Y, Math.exp(e.deltaY * 0.0015));
    }, { passive: false });
  }

  _zoom(X, Y, fattore) {
    const x = this.ux(X), y = this.uy(Y), v = this.v;
    v.xmin = x + (v.xmin - x) * fattore; v.xmax = x + (v.xmax - x) * fattore;
    v.ymin = y + (v.ymin - y) * fattore; v.ymax = y + (v.ymax - y) * fattore;
    this.ridisegna();
  }

  zoomCentro(fattore) { this._zoom(this.W / 2, this.H / 2, fattore); }
}

function frazionePi(v) {
  const q = Math.round(v / Math.PI * 12);
  if (q === 0) return '0';
  const mcd = (a, b) => b ? mcd(b, a % b) : Math.abs(a);
  const d = mcd(q, 12), n = q / d, den = 12 / d;
  const segno = n < 0 ? '−' : '', an = Math.abs(n);
  const testa = an === 1 ? 'π' : an + 'π';
  return segno + (den === 1 ? testa : testa + '/' + den);
}
