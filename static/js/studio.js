// Studio di funzione: input, passaggi, schema dei segni, grafico.

const ESEMPI = ['x^3 - 3x', 'x e^(-x)', 'ln(x)/x', '(x^2 - 1)/(x - 2)', 'e^(-x^2)', '|x^2 - 4|', 'x^5 - 5x^3', 'sen(x) + cos(x)'];

const $ = id => document.getElementById(id);
const grafico = new Grafico($('grafico'), { xmin: -6, xmax: 6, ymin: -5, ymax: 5 });
let D = null, F = null, F1 = null, F2 = null, scelto = null, vistaIniziale = null, testoF = '';
const mostra = { f: true, f1: false, f2: false, asintoti: true, tangenti: true };

$('esempi').insertAdjacentHTML('beforeend',
  ESEMPI.map(e => `<button type="button">${esc(e)}</button>`).join(', '));
$('esempi').addEventListener('click', e => {
  if (e.target.tagName !== 'BUTTON') return;
  $('f').value = e.target.textContent;
  $('a').value = ''; $('b').value = '';
  studia();
});

// mentre scrivi, la funzione appare scritta "in bella"
let timer = null;
$('f').addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const t = $('f').value.trim();
    if (!t) { $('scritta').innerHTML = ''; return; }
    const r = await api('anteprima', { f: t });
    if ($('f').value.trim() === t && r.ok) $('scritta').innerHTML = k('f(x) = ' + r.dati.tex, true);
  }, 280);
});

$('modulo').addEventListener('submit', e => { e.preventDefault(); studia(); });

async function studia() {
  const f = $('f').value.trim();
  if (!f) { $('f').focus(); return; }
  testoF = f;
  history.replaceState(null, '', '#' + new URLSearchParams({ f, a: $('a').value, b: $('b').value }));
  $('errore').classList.add('nascosto');
  $('attesa').classList.remove('nascosto');
  $('vai').disabled = true;
  try {
    const r = await api('studio', { f, a: $('a').value, b: $('b').value });
    if (!r.ok) { $('errore').textContent = r.errore; $('errore').classList.remove('nascosto'); return; }
    D = r.dati;
    $('scritta').innerHTML = k('f(x) = ' + D.f_tex, true);
    disegnaStudio();
  } catch (err) {
    $('errore').textContent = 'Il programma di calcolo non risponde. Riaprilo con avvia.command.';
    $('errore').classList.remove('nascosto');
  } finally {
    $('attesa').classList.add('nascosto');
    $('vai').disabled = false;
  }
}

// ---------------------------------------------------------------- testi

const intero = t => /^-?\d+$/.test(t);
const xDi = p => p.x_tex ?? p.x_txt;
const yDi = p => p.y_tex ?? p.y_txt;
const circa = (tex, v) => tex != null && !intero(tex) && Number.isFinite(v) ? ` <span class="secondaria">≈ ${num(v, 4)}</span>` : '';

// intervalli con lo stesso segno; due intervalli attaccati in un punto del dominio diventano uno solo
function unione(righe, segno) {
  const pezzi = [];
  righe.forEach((r, i) => {
    if (r.segno !== segno) return;
    const prec = righe[i - 1], ultimo = pezzi[pezzi.length - 1];
    if (ultimo && prec && prec.segno === segno && prec.a != null && Math.abs(prec.a - r.da) < 1e-9 && Number.isFinite(F(r.da))) {
      ultimo.a_tex = r.a_tex;
    } else pezzi.push({ da_tex: r.da_tex, a_tex: r.a_tex });
  });
  return pezzi.length ? k(pezzi.map(p => `\\left(${p.da_tex},\\ ${p.a_tex}\\right)`).join(' \\cup ')) : null;
}

function verificaHTML(ordine) {
  return `<form class="verifica" data-ordine="${ordine}">
    <label for="mia-${ordine}">L'hai calcolata a mano? Scrivila qui:</label>
    <input type="text" id="mia-${ordine}" placeholder="${ordine === 1 ? '3x^2 - 3' : '6x'}" spellcheck="false">
    <button type="submit">Controlla</button>
    <div class="esito" aria-live="polite"></div>
  </form>`;
}

function derivataHTML(nome, tex, fatt, grezza, ordine) {
  return `<div class="formula">${k(nome + ' = ' + tex, true)}</div>
    ${fatt ? `<p class="secondaria">Scomposta: ${k(nome + ' = ' + fatt)}</p>` : ''}
    ${grezza ? `<p class="secondaria">Prima di semplificare: ${k(grezza)}</p>` : ''}
    ${verificaHTML(ordine)}`;
}

function disegnaStudio() {
  $('studio').classList.remove('nascosto');
  F = compila(D.f_js); F1 = compila(D.f1_js); F2 = compila(D.f2_js);
  scelto = null;

  // 1. dominio
  $('p-dominio').innerHTML =
    (D.dominio_tex ? `<div class="formula">${k('D = ' + D.dominio_tex, true)}</div>` : '<p>Non sono riuscito a scrivere il dominio in forma esatta.</p>') +
    (D.limiti.length ? `<p class="secondaria">Limiti agli estremi del dominio:</p>` +
      D.limiti.map(l => `<div class="formula">${k(l.tex)}</div>`).join('') : '');

  // 2. derivata prima
  $('p-f1').innerHTML = derivataHTML("f'(x)", D.f1_tex, D.f1_fatt_tex, D.f1_grezza_tex, 1);

  // 3. punti stazionari
  const staz = D.stazionari;
  const nd = D.speciali;
  let h = staz.length
    ? `<p>Pongo ${k("f'(x) = 0")}: ${staz.length === 1 ? 'c’è un punto stazionario' : `ci sono ${staz.length} punti stazionari`}${D.ristretto ? ' nell’intervallo studiato' : ''}.</p>
       <ul class="stazionari">${staz.map((p, i) => `
        <li class="cliccabile" data-tipo="staz" data-i="${i}">
          <span class="evid">${k('x = ' + xDi(p))}</span>${circa(p.x_tex, p.x)}
          <span>${k(`f(${xDi(p)}) = ${yDi(p)}`)}${circa(p.y_tex, p.y)}</span>
          <span class="natura ${p.classe}">${esc(p.tipo)}</span>
          ${p.f2_tex != null ? `<span class="perche">${k(`f''(${xDi(p)}) = ${p.f2_tex}`)}</span>` : ''}
        </li>`).join('')}</ul>`
    : `<p>${k("f'(x) = 0")} non ha soluzioni${D.ristretto ? ' nell’intervallo studiato' : ''}: la funzione non ha punti stazionari.</p>`;
  if (nd.length) {
    h += `<p style="margin-top:14px">Punti in cui ${k('f')} non è derivabile (anche questi vanno controllati per massimi e minimi):</p>
      <ul class="stazionari">${nd.map((p, i) => `
        <li class="cliccabile" data-tipo="nd" data-i="${i}">
          <span class="x-val">${k('x = ' + xDi(p))}</span>
          <span class="natura nd">${esc(p.tipo)}</span>
          <span class="perche">${k(`f'_-(x) \\to ${p.sx_tex ?? '\\text{—}'},\\quad f'_+(x) \\to ${p.dx_tex ?? '\\text{—}'}`)}</span>
        </li>`).join('')}</ul>`;
  }
  $('p-staz').innerHTML = h;
  $('p-staz').querySelectorAll('.cliccabile').forEach(li => li.addEventListener('click', () =>
    vaiAlPunto((li.dataset.tipo === 'staz' ? staz : nd)[+li.dataset.i])));

  // 4. monotonia
  const cresc = unione(D.monotonia, '+'), decr = unione(D.monotonia, '−');
  const maxs = D.estremi.filter(p => p.classe === 'max'), mins = D.estremi.filter(p => p.classe === 'min');
  const elenco = ps => ps.map(p => k(`(${xDi(p)};\\ ${yDi(p)})`)).join(', ');
  $('p-mono').innerHTML = `<p>Studio il segno di ${k("f'(x)")}: dove è positiva la funzione cresce, dove è negativa decresce.</p>` +
    schema(D.monotonia, F1, "f'(x)", D.estremi, 'mono') +
    `<p>${cresc ? `${k('f')} è crescente in ${cresc}` : ''}${cresc && decr ? ' e ' : ''}${decr ? `decrescente in ${decr}` : ''}.</p>` +
    (maxs.length ? `<p>Massimi relativi: ${elenco(maxs)}.</p>` : '') +
    (mins.length ? `<p>Minimi relativi: ${elenco(mins)}.</p>` : '') +
    (!maxs.length && !mins.length ? '<p>Non ci sono massimi né minimi relativi.</p>' : '') +
    (D.assoluti ? `<p>Nell’intervallo ${k(`[${$('a').value},\\ ${$('b').value}]`)} il massimo assoluto è ${k(`f(${D.assoluti.max.x_tex ?? D.assoluti.max.x_txt}) = ${D.assoluti.max.y_tex ?? D.assoluti.max.y_txt}`)} e il minimo assoluto ${k(`f(${D.assoluti.min.x_tex ?? D.assoluti.min.x_txt}) = ${D.assoluti.min.y_tex ?? D.assoluti.min.y_txt}`)} (teorema di Weierstrass).</p>` : '');

  // 5. derivata seconda
  $('p-f2').innerHTML = derivataHTML("f''(x)", D.f2_tex, D.f2_fatt_tex, D.f2_grezza_tex, 2);

  // 6. concavità e flessi
  const su = unione(D.concavita, '+'), giu = unione(D.concavita, '−');
  $('p-conc').innerHTML = `<p>Studio il segno di ${k("f''(x)")}: dove è positiva la concavità è verso l’alto, dove è negativa verso il basso.</p>` +
    schema(D.concavita, F2, "f''(x)", D.flessi, 'conc') +
    `<p>${su ? `Concava verso l’alto in ${su}` : ''}${su && giu ? ', ' : ''}${giu ? `${su ? 'verso il basso' : 'Concava verso il basso'} in ${giu}` : ''}.</p>` +
    (D.flessi.length
      ? '<ul class="stazionari">' + D.flessi.map((p, i) => `
        <li class="cliccabile" data-i="${i}">
          <span class="x-val">${k(`F\\,(${xDi(p)};\\ ${yDi(p)})`)}</span>
          <span class="natura flex">${esc(p.tipo)}</span>
          ${p.tangente_tex ? `<span class="perche">tangente inflessionale ${k(p.tangente_tex)}</span>` : ''}
        </li>`).join('') + '</ul>'
      : '<p>Non ci sono punti di flesso.</p>');
  $('p-conc').querySelectorAll('.cliccabile').forEach(li => li.addEventListener('click', () => vaiAlPunto(D.flessi[+li.dataset.i])));

  // 7. asintoti
  $('p-asin').innerHTML = D.asintoti.length
    ? D.asintoti.map(a => `<p>Asintoto ${esc(a.tipo)} ${k(a.tex)} <span class="secondaria">per ${esc(a.dove)}</span></p>`).join('')
    : `<p>Nessun asintoto${D.ristretto ? ' nell’intervallo studiato' : ''}.</p>`;

  $('note').innerHTML = D.note.map(n => `<p class="nota">${kt(n)}</p>`).join('');
  document.querySelectorAll('form.verifica').forEach(fm => fm.addEventListener('submit', controllaMia));

  inquadra();
}

// ---------------------------------------------------------------- schema dei segni

function schema(righe, G, nomeDer, puntiNotevoli, tipo) {
  if (!righe.length) return '';
  // sequenza di celle: punto, intervallo, punto, ... (con "buchi" dove la funzione non è definita)
  const celle = [];
  const punto = (x, tex) => celle.push({ pt: true, x, tex });
  if (righe[0].da != null) punto(righe[0].da, righe[0].da_tex);
  righe.forEach((r, i) => {
    celle.push({ pt: false, r });
    const dopo = righe[i + 1];
    if (r.a == null) return;
    if (dopo && Math.abs(dopo.da - r.a) < 1e-9) punto(r.a, r.a_tex);
    else {
      punto(r.a, r.a_tex);
      if (dopo) { celle.push({ buco: true }); punto(dopo.da, dopo.da_tex); }
    }
  });

  const colonne = ['auto', ...celle.map(c => c.pt ? 'auto' : c.buco ? 'minmax(2.4rem, .5fr)' : 'minmax(4.5rem, 1fr)')].join(' ');
  const riga1 = [`<div class="nome">${k('x')}</div>`], riga2 = [`<div class="nome">${k(nomeDer)}</div>`], riga3 = [`<div class="nome">${k('f(x)')}</div>`];
  for (const c of celle) {
    if (c.buco) {
      riga1.push('<div class="cella buco"></div>'); riga2.push('<div class="cella buco"></div>'); riga3.push('<div class="cella buco"></div>');
      continue;
    }
    if (!c.pt) {
      const s = c.r.segno, cl = s === '+' ? 'piu' : s === '−' ? 'meno' : '';
      riga1.push('<div class="cella int"></div>');
      riga2.push(`<div class="cella int riga-s"><div class="tratto ${cl}"><span>${s}</span></div></div>`);
      const segnoF = tipo === 'mono' ? { '+': '↗', '−': '↘' }[s] : { '+': '∪', '−': '∩' }[s];
      riga3.push(`<div class="cella int"><span class="freccia">${segnoF ?? ''}</span></div>`);
      continue;
    }
    const dentro = Number.isFinite(F(c.x));
    const d = G ? G(c.x) : NaN;
    const valore = !dentro ? '' : Number.isFinite(d) && Math.abs(d) < 1e-6 ? '0' : '∄';
    const notevole = puntiNotevoli.find(p => Math.abs(p.x - c.x) < 1e-7);
    const etich = !notevole ? '' : notevole.classe === 'flex' ? 'flesso' : notevole.classe;
    riga1.push(`<div class="cella pt riga-x">${k(c.tex)}</div>`);
    riga2.push(`<div class="cella pt riga-s ${dentro ? '' : 'fuori'}">${valore}</div>`);
    riga3.push(`<div class="cella pt"><span class="etich ${etich === 'flesso' ? 'flesso' : ''}">${etich}</span></div>`);
  }
  return `<div class="schema-box"><div class="schema" style="grid-template-columns:${colonne}" role="img" aria-label="Schema dei segni di ${nomeDer}">
    ${riga1.join('')}${riga2.join('')}${riga3.join('')}</div></div>`;
}

// ---------------------------------------------------------------- grafico

function inquadra() {
  let xmin, xmax;
  const tutti = [...D.estremi, ...D.flessi, ...D.speciali, ...D.stazionari];
  const xs = tutti.map(p => p.x).concat(D.asintoti.filter(a => a.tipo === 'verticale').map(a => a.xv));
  if (D.intervallo) {
    const pad = (D.intervallo[1] - D.intervallo[0]) * .06;
    [xmin, xmax] = [D.intervallo[0] - pad, D.intervallo[1] + pad];
  } else if (D.ristretto) {
    [xmin, xmax] = D.finestra;
  } else if (xs.length) {
    const lo = Math.min(...xs), hi = Math.max(...xs), m = Math.max(2.5, (hi - lo) * .6);
    [xmin, xmax] = [lo - m, hi + m];
  } else {
    [xmin, xmax] = [-6, 6];
  }
  grafico.opz.pi = /sin|cos|tan|cot/.test(D.f_js || '');
  grafico.inquadra([F], xmin, xmax, tutti.map(p => p.y));
  vistaIniziale = { ...grafico.v };
}

function vaiAlPunto(p) {
  scelto = p;
  if (!Number.isFinite(p.y)) return;
  const w = grafico.v.xmax - grafico.v.xmin, h = grafico.v.ymax - grafico.v.ymin;
  grafico.imposta({ xmin: p.x - w / 2, xmax: p.x + w / 2, ymin: p.y - h / 2, ymax: p.y + h / 2 });
  if (innerWidth <= 1000) $('grafico').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function evidenzia(g, x, y) {
  const c = g.ctx, X = g.px(x), Y = g.py(y);
  c.save();
  c.fillStyle = g.col('--evidenziatore');
  c.beginPath(); c.ellipse(X, Y, 15, 12, -0.3, 0, 2 * Math.PI); c.fill();
  c.restore();
}

grafico.disegna = g => {
  if (!D || !F) return;
  const ext = D.intervallo ? { da: D.intervallo[0], a: D.intervallo[1] } : {};
  if (mostra.asintoti) {
    const op = { colore: g.col('--matita-2'), tratteggio: [6, 5], spessore: 1.2 };
    for (const a of D.asintoti) {
      if (a.tipo === 'verticale') g.verticale(a.xv, op);
      else if (a.m != null && a.q != null) g.retta(0, a.q, a.m, op);
    }
  }
  if (mostra.f2 && F2) g.curva(F2, { colore: g.col('--matita-2'), spessore: 1.6, tratteggio: [7, 5], ...ext });
  if (mostra.f1 && F1) g.curva(F1, { colore: g.col('--rosso'), spessore: 1.6, tratteggio: [7, 5], ...ext });

  for (const p of D.stazionari) if (Number.isFinite(p.y)) evidenzia(g, p.x, p.y);
  if (mostra.f) g.curva(F, { colore: g.col('--penna'), spessore: 2.6, ...ext });

  const L = (g.v.xmax - g.v.xmin) * .1;
  if (mostra.tangenti) {
    const op = { colore: g.col('--verde'), spessore: 1.3, tratteggio: [4, 4] };
    for (const p of D.flessi) {
      if (!Number.isFinite(p.y)) continue;
      if (p.tipo.includes('verticale')) g.segmento(p.x, p.y - L, p.x, p.y + L, op);
      else if (p.tipo.includes('orizzontale')) g.segmento(p.x - L, p.y, p.x + L, p.y, op);
      else if (Number.isFinite(p.m)) g.retta(p.x, p.y, p.m, { ...op, da: p.x - L, a: p.x + L });
    }
  }
  const lettera = { max: 'M', min: 'm', flex: 'F', nd: 'P' };
  for (const p of [...D.speciali, ...D.flessi, ...D.estremi]) {
    if (!Number.isFinite(p.y)) continue;
    const colore = p.classe === 'flex' ? g.col('--verde') : p.classe === 'nd' ? g.col('--matita') : g.col('--rosso');
    g.punto(p.x, p.y, {
      colore, r: 4.5, forma: p.classe === 'nd' ? 'quadrato' : 'cerchio',
      etichetta: lettera[p.classe], sotto: p.classe === 'min', anello: p === scelto || (scelto && Math.abs(scelto.x - p.x) < 1e-9),
    });
  }
};

$('mostra').addEventListener('change', e => { mostra[e.target.dataset.k] = e.target.checked; grafico.ridisegna(); });
$('zoom-piu').onclick = () => grafico.zoomCentro(1 / 1.5);
$('zoom-meno').onclick = () => grafico.zoomCentro(1.5);
$('zoom-reset').onclick = () => { if (vistaIniziale) { scelto = null; grafico.imposta({ ...vistaIniziale }); } };

// ---------------------------------------------------------------- controllo della derivata scritta a mano

async function controllaMia(e) {
  e.preventDefault();
  const fm = e.target, esito = fm.querySelector('.esito');
  const t = fm.querySelector('input').value.trim();
  if (!t) return;
  esito.className = 'esito'; esito.textContent = 'Controllo…';
  const r = await api('verifica', { f: testoF, tentativo: t, ordine: +fm.dataset.ordine });
  if (!r.ok) { esito.className = 'esito no'; esito.textContent = r.errore; return; }
  esito.className = 'esito ' + (r.dati.corretta ? 'si' : r.dati.corretta === false ? 'no' : '');
  esito.textContent = r.dati.msg;
}

// riapre l'ultima funzione studiata (è scritta nell'indirizzo)
(() => {
  const p = new URLSearchParams(location.hash.slice(1));
  if (p.get('f')) {
    $('f').value = p.get('f'); $('a').value = p.get('a') || ''; $('b').value = p.get('b') || '';
    studia();
  }
})();
