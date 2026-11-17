// Funzioni condivise.

async function api(azione, dati) {
  const r = await fetch('/api/' + azione, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dati),
  });
  return r.json();
}

// LaTeX -> HTML (KaTeX locale)
function k(tex, grande = false) {
  if (tex == null) return '';
  try {
    return katex.renderToString(tex, { displayMode: grande, throwOnError: false, strict: false });
  } catch (e) {
    return esc(tex);
  }
}

// testo con $...$ dentro
function kt(testo) {
  if (!testo) return '';
  return testo.split(/(\$[^$]+\$)/g).map(p => p.startsWith('$') && p.endsWith('$') && p.length > 1 ? k(p.slice(1, -1)) : esc(p)).join('');
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function rendiFormule(radice = document) {
  radice.querySelectorAll('.m').forEach(el => { if (!el.dataset.fatto) { el.innerHTML = k(el.textContent); el.dataset.fatto = 1; } });
}

// il codice JS arriva dal server, generato da sympy a partire da un'espressione già letta e controllata
function compila(codice) {
  if (!codice) return null;
  try {
    const f = new Function('x', '"use strict"; return (' + codice + ');');
    return t => { const v = f(t); return Number.isFinite(v) ? v : NaN; };
  } catch (e) {
    return null;
  }
}

function num(v, cifre = 4) {
  if (v == null || !Number.isFinite(v)) return '—';
  if (Math.abs(v) < 1e-12) return '0';
  return Number(v.toPrecision(cifre)).toString().replace('-', '−').replace('.', ',');
}

document.addEventListener('DOMContentLoaded', () => rendiFormule());
