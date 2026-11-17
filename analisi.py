"""Motore di calcolo dello studio di funzione (sympy)."""
import math
import random
import re
import signal
from contextlib import contextmanager

import sympy as sp
from sympy.calculus.util import continuous_domain
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                        parse_expr, standard_transformations)
from sympy.printing.jscode import JavascriptCodePrinter
from sympy.printing.latex import LatexPrinter

x = sp.Symbol('x', real=True)


class ErroreInput(Exception):
    pass


# ---------------------------------------------------------------- tempo massimo

@contextmanager
def limite(secondi):
    """Interrompe il blocco dopo `secondi` (funziona nel processo figlio del server)."""
    def scaduto(*_):
        raise TimeoutError
    try:
        vecchio = signal.signal(signal.SIGALRM, scaduto)
    except ValueError:          # non siamo nel thread principale: niente limite
        yield
        return
    signal.setitimer(signal.ITIMER_REAL, secondi)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, vecchio)


def prova(fn, secondi, default=None):
    try:
        with limite(secondi):
            return fn()
    except Exception:
        return default


# ---------------------------------------------------------------- lettura input

def radice_cubica(u):
    return sp.sign(u) * sp.Abs(u) ** sp.Rational(1, 3)


NOMI = {
    'x': x, 'e': sp.E, 'E': sp.E, 'pi': sp.pi, 'oo': sp.oo, 'inf': sp.oo,
    'sen': sp.sin, 'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan, 'tan': sp.tan,
    'cotg': sp.cot, 'ctg': sp.cot, 'cot': sp.cot,
    'arcsen': sp.asin, 'arcsin': sp.asin, 'asin': sp.asin,
    'arccos': sp.acos, 'acos': sp.acos,
    'arctg': sp.atan, 'arctan': sp.atan, 'atan': sp.atan,
    'senh': sp.sinh, 'sinh': sp.sinh, 'cosh': sp.cosh, 'tgh': sp.tanh, 'tanh': sp.tanh,
    'ln': sp.log, 'log': sp.log, 'exp': sp.exp,
    'sqrt': sp.sqrt, 'radice': sp.sqrt, 'cbrt': radice_cubica, 'radice3': radice_cubica,
    'abs': sp.Abs, 'Abs': sp.Abs,
}
_FUNZ = sorted([k for k, v in NOMI.items() if callable(v) and not isinstance(v, sp.Basic)],
               key=len, reverse=True)
_RE_FUNZ = re.compile(r'(?<=[x0-9)])(' + '|'.join(_FUNZ) + r')(?=[\s(])')
TRASF = standard_transformations + (implicit_multiplication_application, convert_xor)


def _barre_valore_assoluto(s):
    out, aperte = [], 0
    for i, ch in enumerate(s):
        if ch != '|':
            out.append(ch)
            continue
        prec = ''.join(out).rstrip()[-1:]
        if aperte == 0 or prec in ('', '+', '-', '*', '/', '^', '(', ','):
            out.append('abs(')
            aperte += 1
        else:
            out.append(')')
            aperte -= 1
    return ''.join(out)


def _prepara(s):
    s = (s or '').strip()
    for a, b in {'·': '*', '×': '*', '÷': '/', '−': '-', '²': '^2', '³': '^3', '√': 'sqrt',
                 '∛': 'cbrt', 'π': 'pi', '∞': 'oo', '**': '^', '[': '(', ']': ')',
                 '{': '(', '}': ')'}.items():
        s = s.replace(a, b)
    if s.lower().startswith(('f(x)=', 'y=', 'g(x)=')):
        s = s.split('=', 1)[1]
    s = _barre_valore_assoluto(s)
    s = _RE_FUNZ.sub(r'*\1', s)
    return s


def leggi(s, nome='f'):
    testo = _prepara(s)
    if not testo:
        raise ErroreInput(f'Scrivi la funzione {nome}(x).')
    try:
        e = parse_expr(testo, local_dict=dict(NOMI), transformations=TRASF)
    except Exception:
        raise ErroreInput(f'Non riesco a leggere «{s}». Controlla parentesi e simboli '
                          '(es. 3x^2 - 2x, e^(-x), ln(x)/x, sen(2x)).')
    if isinstance(e, (tuple, sp.Tuple)):
        raise ErroreInput('Usa il punto per i decimali (0.5, non 0,5).')
    if not isinstance(e, sp.Expr):
        raise ErroreInput(f'«{s}» non è una funzione di x.')
    altre = e.free_symbols - {x}
    if altre:
        nomi = ', '.join(sorted(str(a) for a in altre))
        raise ErroreInput(f'Non conosco il simbolo «{nomi}». La variabile deve essere x '
                          '(per le funzioni: sen, cos, tg, ln, e^x, sqrt, cbrt, abs, arctg…).')
    return radici_reali(e)


def _radice_dispari(t):
    if not (t.is_Pow and t.exp.is_Rational and not t.exp.is_Integer and t.exp.q % 2 == 1):
        return False
    return t.base.has(x) and not isinstance(t.base, sp.Abs)


def radici_reali(e):
    """x^(p/q) con q dispari = radice reale (come ∛ a scuola), definita anche per x < 0."""
    def conv(t):
        b, r = t.args
        return sp.Abs(b) ** r if r.p % 2 == 0 else sp.sign(b) * sp.Abs(b) ** r
    return e.replace(_radice_dispari, conv)


def leggi_numero(s, nome):
    testo = _prepara(s)
    if not testo:
        raise ErroreInput(f'Manca il valore di {nome}.')
    try:
        v = parse_expr(testo, local_dict=dict(NOMI), transformations=TRASF)
    except Exception:
        raise ErroreInput(f'{nome}: non riesco a leggere «{s}».')
    if not isinstance(v, sp.Expr) or v.free_symbols:
        raise ErroreInput(f'{nome} deve essere un numero (es. 2, -1/2, pi/3, e, oo).')
    if v in (sp.oo, -sp.oo):
        return v
    if not v.is_real:
        raise ErroreInput(f'{nome} deve essere un numero reale.')
    return v


# ---------------------------------------------------------------- stampa

class Latex(LatexPrinter):
    def __init__(self):
        super().__init__({'ln_notation': True, 'inv_trig_style': 'full'})

    def _print_sign(self, e, exp=None):
        s = r'\operatorname{sgn}\left(%s\right)' % self._print(e.args[0])
        return s if exp is None else r'%s^{%s}' % (s, exp)

    @staticmethod
    def _e_radice(t):
        return (t.is_Pow and isinstance(t.base, sp.Abs) and t.exp.is_Rational
                and not t.exp.is_Integer and t.exp.q % 2 == 1)

    def _radice(self, u, r, assoluto=False):
        """Radice reale ∛(u^p) per r = p/q; ritorna (tex, al_denominatore)."""
        p, q = abs(r.p), r.q
        base = self._print(sp.Abs(u)) if assoluto else self._print(u)
        if p != 1:
            base = (r'\left(%s\right)^{%d}' if (u.is_Add or u.is_Mul or u.is_Pow) and not assoluto
                    else '%s^{%d}') % (base, p)
        return r'\sqrt[%d]{%s}' % (q, base), r.p < 0

    def _print_Pow(self, e, *args, **kw):
        if self._e_radice(e):
            u, r = e.base.args[0], e.exp
            rad, den = self._radice(u, r, assoluto=r.p % 2 == 1)
            return r'\frac{1}{%s}' % rad if den else rad
        return super()._print_Pow(e, *args, **kw)

    def _print_Mul(self, e):
        fatt = list(e.args)
        radici = [t for t in fatt if self._e_radice(t)]
        if not radici:
            return super()._print_Mul(e)
        segni = [t for t in fatt if isinstance(t, sp.sign)]
        su, giu, usati = [], [], []
        for t in radici:
            u, r = t.base.args[0], t.exp
            s = next((s for s in segni if s.args[0] == u and s not in usati), None)
            if r.p % 2 == 1 and s is not None:
                usati.append(s)
                rad, den = self._radice(u, r)
            else:
                rad, den = self._radice(u, r, assoluto=r.p % 2 == 1)
            (giu if den else su).append(rad)
        resto = sp.Mul(*[t for t in fatt if t not in radici and t not in usati])
        n, d = sp.fraction(sp.together(resto))
        meno = n.could_extract_minus_sign()
        if meno:
            n = -n
        num = ([] if n == 1 else [(r'\left(%s\right)' if n.is_Add and su else '%s') % self._print(n)]) + su
        den = ([] if d == 1 else [(r'\left(%s\right)' if d.is_Add and giu else '%s') % self._print(d)]) + giu
        num_s = ' '.join(num) or '1'
        s = num_s if not den else r'\frac{%s}{%s}' % (num_s, ' '.join(den))
        return ('- ' if meno else '') + s


def tex(e):
    if e is None:
        return None
    if e is sp.oo:
        return r'+\infty'
    return Latex().doprint(e)


class JS(JavascriptCodePrinter):
    def _print_sign(self, e):
        return 'Math.sign(%s)' % self._print(e.args[0])

    def _print_Pow(self, e):
        b, p = e.args
        if p == sp.S.Half:
            return '(Math.sqrt(%s))' % self._print(b)
        if p == -1:
            return '(1/(%s))' % self._print(b)
        return '(Math.pow(%s, %s))' % (self._print(b), self._print(p))

    def _print_Rational(self, e):
        return '(%d/%d)' % (e.p, e.q)


def js(e):
    try:
        s = JS().doprint(e)
    except Exception:
        return None
    return None if 'Not supported' in s or '//' in s else s


# ---------------------------------------------------------------- numeri

_MAPPA = [{'sign': lambda v: (v > 0) - (v < 0), 'Abs': abs, 'DiracDelta': lambda *a: 0.0}, 'math']


def numerica(e):
    """Funzione float -> float (None se fuori dominio)."""
    try:
        g = sp.lambdify(x, e, modules=_MAPPA)
    except Exception:
        return lambda t: None

    def f(t):
        try:
            v = g(t)
            if isinstance(v, complex):
                if abs(v.imag) > 1e-12:
                    return None
                v = v.real
            v = float(v)
            return v if math.isfinite(v) else None
        except Exception:
            return None
    return f


def a_float(v):
    try:
        c = complex(sp.N(v, 20))
        if abs(c.imag) > 1e-12:
            return None
        return c.real
    except Exception:
        return None


def fmt(v):
    if v is None:
        return '—'
    if abs(v) < 5e-13:
        return '0'
    s = f'{v:.6g}'
    return s.replace('e+0', 'e').replace('e-0', 'e-')


def pulisci(d):
    """Rimuove DiracDelta e sgn(u)^2 che nascono derivando |u| e cbrt."""
    d = d.replace(sp.DiracDelta, lambda *a: sp.S.Zero)
    d = d.replace(lambda t: t.is_Pow and isinstance(t.base, sp.sign) and t.exp.is_even,
                  lambda t: sp.S.One)
    d = d.replace(lambda t: isinstance(t, sp.Abs) and t.args[0].is_Pow and t.args[0].exp.is_Rational
                  and not t.args[0].exp.is_Integer,
                  lambda t: sp.Abs(t.args[0].base) ** t.args[0].exp)
    return radici_reali(d)


def _frazione(e):
    n, d = sp.fraction(sp.together(e))
    n = min([sp.expand(n), prova(lambda: sp.factor(n), 3, n)], key=sp.count_ops)
    d = prova(lambda: sp.factor(d), 3, d)
    return n / d


def _come_se_positivo(e):
    """Semplifica per x > 0 e riporta alle radici reali; valido solo se coincide numericamente."""
    xp = sp.Symbol('xp', positive=True)
    s = pulisci(sp.simplify(e.subs(x, xp)).subs(xp, x))
    a, b = numerica(e), numerica(s)
    rnd, prove = random.Random(3), 0
    for _ in range(200):
        t = rnd.uniform(-9, 9)
        va = a(t)
        if va is None:
            continue
        vb = b(t)
        if vb is None or abs(va - vb) > 1e-8 * (1 + abs(va)):
            return None
        prove += 1
        if prove >= 20:
            break
    return s if prove >= 5 else None


def semplifica(e, secondi=6):
    e = pulisci(e)
    candidati = [e]
    trasf = [lambda: sp.simplify(e), lambda: _frazione(e)]
    if e.has(sp.Abs, sp.sign):
        trasf.append(lambda: _come_se_positivo(e))
    for fn in trasf:
        s = prova(fn, secondi)
        if s is not None:
            s = pulisci(s)
            if not (s.has(sp.Piecewise) and not e.has(sp.Piecewise)):
                candidati.append(s)
    return min(reversed(candidati), key=sp.count_ops)


def per_dominio(e, derivata=True):
    """sgn(u) -> u/|u| esclude i punti dove la derivata di |u| non esiste."""
    e = pulisci(e)
    return e.replace(sp.sign, (lambda u: u / sp.Abs(u)) if derivata else (lambda u: sp.S.One))


def dominio(e, su=sp.S.Reals, derivata=True):
    return prova(lambda: continuous_domain(per_dominio(e, derivata), x, su), 8)


# ---------------------------------------------------------------- zeri

def _intervallo_finestra(f_insieme, finestra):
    return prova(lambda: sp.Intersection(f_insieme, sp.Interval(*finestra)), 4)


def zeri_numerici(g, a, b, n=4000):
    xs = [a + (b - a) * i / n for i in range(n + 1)]
    vs = [g(t) for t in xs]
    out = []
    for i in range(n):
        v0, v1 = vs[i], vs[i + 1]
        if v0 is None or v1 is None:
            continue
        if v0 == 0:
            out.append(xs[i])
            continue
        if v0 * v1 > 0:
            continue
        lo, hi, flo = xs[i], xs[i + 1], v0
        ok = True
        for _ in range(80):
            m = (lo + hi) / 2
            fm = g(m)
            if fm is None:
                ok = False
                break
            if (fm < 0) == (flo < 0):
                lo, flo = m, fm
            else:
                hi = m
        c = (lo + hi) / 2
        gc = g(c)
        if ok and gc is not None and abs(gc) < 1e-6 * (1 + min(abs(v0), abs(v1))):
            out.append(c)
    if vs[-1] == 0:
        out.append(xs[-1])
    pulito = []
    for c in sorted(out):
        if not pulito or abs(c - pulito[-1]) > 1e-7 * (1 + abs(c)):
            pulito.append(c)
    return pulito


def zeri(e, D, finestra):
    """Zeri di e in D. Restituisce (lista di punti, esatti?, limitati alla finestra?)."""
    eq = per_dominio(e)
    S = prova(lambda: sp.solveset(eq, x, D), 10)
    ristretto = False
    if S is not None and not isinstance(S, sp.FiniteSet) and S is not sp.S.EmptySet:
        ristretto = True
        Dw = _intervallo_finestra(D, finestra)
        S = prova(lambda: sp.solveset(eq, x, Dw), 10) if Dw is not None else None
    if S is sp.S.EmptySet:
        return [], True, ristretto
    if isinstance(S, sp.FiniteSet):
        punti = []
        for p in S:
            v = a_float(p)
            if v is not None:
                punti.append(punto(p, v))
        return sorted(punti, key=lambda q: q['v']), True, ristretto
    g = numerica(e)
    return [punto(None, c) for c in zeri_numerici(g, *finestra)], False, True


def punto(esatto, v):
    if esatto is not None:
        esatto = prova(lambda: sp.nsimplify(sp.simplify(esatto)) if esatto.is_Float else
                       sp.radsimp(sp.simplify(esatto)), 3, esatto)
    return {'e': esatto, 'v': v}


def insieme_finito(S, finestra=None):
    """Punti (esatti) di un insieme se finito; altrimenti None."""
    if S is None:
        return None
    if S is sp.S.EmptySet:
        return []
    if isinstance(S, sp.FiniteSet):
        return [punto(p, a_float(p)) for p in S if a_float(p) is not None]
    if finestra is not None:
        return insieme_finito(_intervallo_finestra(S, finestra))
    return None


# ---------------------------------------------------------------- dominio a intervalli

def componenti(D, finestra, f_num):
    """Lista di intervalli (lo, hi, lo_incluso, hi_incluso) con estremi sympy."""
    def da(S):
        if isinstance(S, sp.Interval):
            return [S]
        if isinstance(S, sp.Union) and all(isinstance(a, (sp.Interval, sp.FiniteSet)) for a in S.args):
            return [a for a in S.args if isinstance(a, sp.Interval)]
        return None
    if D is not None:
        c = da(D)
        if c is None and finestra:
            c = da(_intervallo_finestra(D, finestra))
        if c is not None:
            return [(i.start, i.end, not i.left_open, not i.right_open) for i in c
                    if i.measure != 0]
    # numerico: dove f è definita
    a, b = finestra
    n = 3000
    out, inizio = [], None
    for i in range(n + 1):
        t = a + (b - a) * i / n
        ok = f_num(t) is not None
        if ok and inizio is None:
            inizio = t
        if (not ok or i == n) and inizio is not None:
            fine = t if ok else a + (b - a) * (i - 1) / n
            if fine > inizio:
                out.append((sp.Float(inizio, 6), sp.Float(fine, 6), True, True))
            inizio = None
    return out


# ---------------------------------------------------------------- studio di funzione

def _segno(g, t):
    v = g(t)
    if v is None:
        return None
    if abs(v) < 1e-10:
        return 0
    return 1 if v > 0 else -1


def _passo(c, tutti):
    vicini = [abs(c - t) for t in tutti if abs(c - t) > 1e-12]
    h = 1e-4 * (1 + abs(c))
    if vicini:
        h = min(h, min(vicini) / 4)
    return h


def _limite(e, punto_, direzione, secondi=5):
    r = prova(lambda: sp.limit(e, x, punto_, direzione), secondi)
    if r is None or r.has(sp.AccumBounds) or r is sp.nan or r.has(sp.nan):
        return None
    if r is sp.zoo:
        return None
    return r


def _tex_lim(l):
    if l is None:
        return r'\nexists'
    return tex(l)


def studio(testo, a_txt='', b_txt=''):
    f = leggi(testo)
    intervallo = None
    if (a_txt or '').strip() or (b_txt or '').strip():
        a = leggi_numero(a_txt, 'a')
        b = leggi_numero(b_txt, 'b')
        if a.is_infinite or b.is_infinite or not (a < b):
            raise ErroreInput("L'intervallo deve avere a < b, entrambi finiti.")
        intervallo = (a, b)

    note = []
    f1_grezza = pulisci(sp.diff(f, x))
    f1 = semplifica(f1_grezza)
    f2_grezza = pulisci(sp.diff(f1, x))
    f2 = semplifica(f2_grezza)

    fn, f1n, f2n = numerica(f), numerica(f1), numerica(f2)

    base = sp.Interval(*intervallo) if intervallo else sp.S.Reals
    D_tutto = dominio(f, base, derivata=False)
    periodica = D_tutto is not None and D_tutto.has(sp.ImageSet)
    if intervallo:
        finestra_s = intervallo
    elif periodica or f.has(sp.sin, sp.cos, sp.tan, sp.cot):
        finestra_s = (-2 * sp.pi, 2 * sp.pi)
    else:
        finestra_s = (sp.Integer(-20), sp.Integer(20))
    finestra = (float(finestra_s[0]), float(finestra_s[1]))

    stazionari, es1, rist1 = zeri(f1, D_tutto if D_tutto is not None else base, finestra)
    zeri2, es2, rist2 = zeri(f2, D_tutto if D_tutto is not None else base, finestra)
    ristretto = bool(intervallo) or rist1 or rist2 or periodica or D_tutto is None

    # se lavoriamo in una finestra, il dominio va ricalcolato lì (es. tg: escluse solo ±π/2, ±3π/2)
    D = dominio(f, sp.Interval(*finestra_s), derivata=False) if ristretto and not intervallo else D_tutto
    if D is None:
        note.append('Non sono riuscito a calcolare il dominio in modo esatto: lo stimo numericamente.')
    D1 = dominio(f1, D) if D is not None else None
    D2 = dominio(f2, D) if D is not None else None
    if ristretto:
        dentro = lambda ps: [p for p in ps if finestra[0] - 1e-12 <= p['v'] <= finestra[1] + 1e-12]
        stazionari, zeri2 = dentro(stazionari), dentro(zeri2)

    non_der = insieme_finito(prova(lambda: sp.Complement(D, D1), 5), finestra) \
        if D is not None and D1 is not None else []
    non_der2 = insieme_finito(prova(lambda: sp.Complement(D, D2), 5), finestra) \
        if D is not None and D2 is not None else []
    non_der = non_der or []
    non_der2 = non_der2 or []

    if ristretto and not intervallo:
        note.append(f'La funzione ha infiniti punti notevoli (o non li trovo in forma esatta): '
                    f'la studio in $[{tex(finestra_s[0])},\\ {tex(finestra_s[1])}]$. '
                    'Puoi scegliere tu l’intervallo qui sopra.')
    if not (es1 and es2):
        note.append('Alcuni punti sono stati trovati numericamente (valori approssimati).')

    comp = componenti(D, finestra, fn)

    def bordo_finestra(v):
        return ristretto and not intervallo and (abs(v - finestra[0]) < 1e-9 or abs(v - finestra[1]) < 1e-9)

    bordi = []
    for lo, hi, li, hi_inc in comp:
        for estremo, incluso in ((lo, li), (hi, hi_inc)):
            if estremo.is_finite:
                bordi.append((estremo, incluso))

    tutti_x = sorted({p['v'] for p in stazionari + zeri2 + non_der + non_der2}
                     | {a_float(b) for b, _ in bordi})

    def val_f(p):
        if p['e'] is not None:
            y = prova(lambda: semplifica(f.subs(x, p['e']), 3), 4)
            yv = a_float(y) if y is not None else None
            if y is not None and yv is not None:
                return y, yv
        return None, fn(p['v'])

    def scheda(p, tipo, classe, extra=None):
        y, yv = val_f(p)
        d = {'tipo': tipo, 'classe': classe, 'x': p['v'], 'y': yv,
             'x_tex': tex(p['e']) if p['e'] is not None else None,
             'y_tex': tex(y) if y is not None else None,
             'x_txt': fmt(p['v']), 'y_txt': fmt(yv), 'esatto': p['e'] is not None}
        if extra:
            d.update(extra)
        return d

    stazionari_v = {round(p['v'], 9) for p in stazionari}

    # --- punti di non derivabilità (angolosi, cuspidi, flessi verticali)
    speciali, tipo_nd = [], {}
    for p in non_der:
        c = p['v']
        if fn(c) is None:
            continue
        h = _passo(c, tutti_x)
        lati = {}
        for lato, t in (('-', c - h), ('+', c + h)):
            if fn(t) is None:
                lati[lato] = 'fuori'
            elif p['e'] is not None:
                lati[lato] = _limite(f1, p['e'], lato, 3)
            else:
                lati[lato] = None
        ls, rs = lati['-'], lati['+']
        def inf(v):
            return isinstance(v, sp.Basic) and v.is_infinite
        def fin(v):
            return isinstance(v, sp.Basic) and v.is_finite
        if ls == 'fuori' or rs == 'fuori':
            altro = rs if ls == 'fuori' else ls
            tipo = 'tangente verticale (bordo del dominio)' if inf(altro) else 'estremo del dominio'
            if not inf(altro):
                continue
        elif inf(ls) and inf(rs):
            tipo = 'cuspide' if ls != rs else 'flesso a tangente verticale'
        elif (fin(ls) or inf(ls)) and (fin(rs) or inf(rs)) and ls != rs:
            tipo = 'punto angoloso'
        else:
            tipo = 'punto di non derivabilità'
        tipo_nd[round(c, 9)] = tipo
        if tipo != 'flesso a tangente verticale':
            speciali.append(scheda(p, tipo, 'nd', {
                'sx_tex': None if ls == 'fuori' else _tex_lim(ls),
                'dx_tex': None if rs == 'fuori' else _tex_lim(rs)}))

    # --- massimi e minimi
    estremi = []
    candidati = {round(p['v'], 9): p for p in stazionari + non_der}
    for b, incluso in bordi:
        if incluso and not bordo_finestra(a_float(b)):
            candidati.setdefault(round(a_float(b), 9), punto(b, a_float(b)))
    for chiave in sorted(candidati):
        p = candidati[chiave]
        c = p['v']
        if fn(c) is None:
            continue
        h = _passo(c, tutti_x)
        sl, sr = _segno(f1n, c - h), _segno(f1n, c + h)
        stazionario = chiave in stazionari_v
        extra = {}
        if stazionario:
            v2 = prova(lambda: semplifica(f2.subs(x, p['e']), 3), 3) if p['e'] is not None else None
            if v2 is not None and a_float(v2) is not None:
                extra['f2_tex'] = tex(v2)
            elif f2n(c) is not None:
                extra['f2_tex'] = fmt(f2n(c))
        if sl is None and sr is None:
            continue
        if sl is None or sr is None:
            s = sr if sl is None else -sl
            if s:
                estremi.append(scheda(p, 'minimo relativo' if s == 1 else 'massimo relativo',
                                      'min' if s == 1 else 'max', {**extra, 'nota': 'estremo del dominio'}))
            continue
        nota = 'punto stazionario' if stazionario else tipo_nd.get(chiave, 'punto di non derivabilità')
        if sl > 0 and sr < 0:
            estremi.append(scheda(p, 'massimo relativo', 'max', {**extra, 'nota': nota}))
        elif sl < 0 and sr > 0:
            estremi.append(scheda(p, 'minimo relativo', 'min', {**extra, 'nota': nota}))

    # --- flessi
    flessi = []
    cand2 = {round(p['v'], 9): p for p in zeri2 + non_der2 + non_der}
    for chiave in sorted(cand2):
        p = cand2[chiave]
        c = p['v']
        if fn(c) is None or bordo_finestra(c):
            continue
        if tipo_nd.get(chiave) not in (None, 'flesso a tangente verticale'):
            continue            # angoloso / cuspide: non c'è una retta tangente
        h = _passo(c, tutti_x)
        sl, sr = _segno(f2n, c - h), _segno(f2n, c + h)
        if sl is None or sr is None or sl * sr >= 0:
            continue
        if chiave in stazionari_v:
            tipo = 'flesso a tangente orizzontale'
        elif chiave in tipo_nd:
            tipo = 'flesso a tangente verticale'
        else:
            tipo = 'flesso a tangente obliqua'
        extra = {'concavita': 'da ∪ a ∩' if sl > 0 else 'da ∩ a ∪', 'm': f1n(c)}
        if tipo == 'flesso a tangente obliqua':
            m = prova(lambda: semplifica(f1.subs(x, p['e']), 3), 3) if p['e'] is not None else None
            y, yv = val_f(p)
            if m is not None and y is not None and a_float(m) is not None:
                q = prova(lambda: semplifica(y - m * p['e'], 3), 3)
                if q is not None:
                    extra['tangente_tex'] = 'y = ' + tex(m * x + q)
            else:
                mv = f1n(c)
                if mv is not None and yv is not None:
                    extra['tangente_tex'] = f'y \\approx {fmt(mv)}\\,x {"-" if yv - mv * c < 0 else "+"} {fmt(abs(yv - mv * c))}'
        flessi.append(scheda(p, tipo, 'flex', extra))

    # --- punti stazionari: tutti gli zeri di f', con la loro natura
    natura = {round(e['x'], 9): e for e in estremi + flessi}
    lista_staz = []
    for p in stazionari:
        if fn(p['v']) is None or bordo_finestra(p['v']):
            continue
        e = natura.get(round(p['v'], 9))
        if e is None:
            tipo, classe = 'né massimo né minimo', 'staz'
        elif e['classe'] == 'flex':
            tipo, classe = 'flesso a tangente orizzontale', 'flex'
        else:
            tipo, classe = e['tipo'], e['classe']
        extra = {'f2_tex': e.get('f2_tex')} if e else {}
        lista_staz.append(scheda(p, tipo, classe, extra))

    # --- estremi assoluti nell'intervallo
    assoluti = None
    if intervallo and D is not None and D == sp.Interval(*intervallo):
        cand = [e for e in estremi]
        if cand:
            mx = max(cand, key=lambda q: q['y'])
            mn = min(cand, key=lambda q: q['y'])
            assoluti = {'max': {'x_txt': mx['x_txt'], 'x_tex': mx['x_tex'], 'y_tex': mx['y_tex'], 'y_txt': mx['y_txt']},
                        'min': {'x_txt': mn['x_txt'], 'x_tex': mn['x_tex'], 'y_tex': mn['y_tex'], 'y_txt': mn['y_txt']}}

    # --- tabelle di segno
    def tabella(g, punti_rottura, pos, neg):
        righe = []
        rott = sorted({round(p['v'], 12): p for p in punti_rottura}.values(), key=lambda q: q['v'])
        for lo, hi, _, _ in comp:
            lov = a_float(lo) if lo.is_finite else -math.inf
            hiv = a_float(hi) if hi.is_finite else math.inf
            pts = [(lo, lov)] + [((p['e'] if p['e'] is not None else sp.Float(p['v'], 6)), p['v'])
                                 for p in rott if lov + 1e-12 < p['v'] < hiv - 1e-12] + [(hi, hiv)]
            for (e0, v0), (e1, v1) in zip(pts, pts[1:]):
                if math.isinf(v0) and math.isinf(v1):
                    t = 0.0
                elif math.isinf(v0):
                    t = v1 - 1
                elif math.isinf(v1):
                    t = v0 + 1
                else:
                    t = (v0 + v1) / 2
                s = _segno(g, t)
                if s is None:
                    for frac in (0.25, 0.75, 0.1, 0.9):
                        if not (math.isinf(v0) or math.isinf(v1)):
                            s = _segno(g, v0 + (v1 - v0) * frac)
                        if s is not None:
                            break
                righe.append({
                    'da': None if math.isinf(v0) else v0, 'a': None if math.isinf(v1) else v1,
                    'da_tex': _tex_estremo(e0, v0), 'a_tex': _tex_estremo(e1, v1),
                    'int_tex': r'\left(%s,\ %s\right)' % (_tex_estremo(e0, v0), _tex_estremo(e1, v1)),
                    'segno': {1: '+', -1: '−', 0: '0', None: '?'}[s],
                    'comportamento': {1: pos, -1: neg, 0: 'costante', None: '?'}[s]})
        return righe

    monotonia = tabella(f1n, stazionari + non_der, 'crescente ↗', 'decrescente ↘')
    concavita = tabella(f2n, zeri2 + non_der2 + non_der, 'concava verso l’alto ∪', 'concava verso il basso ∩')

    # --- limiti agli estremi e asintoti
    limiti, asintoti = [], []
    for lo, hi, li, hi_inc in comp:
        for estremo, incluso, lato in ((lo, li, '+'), (hi, hi_inc, '-')):
            if incluso:
                continue
            if estremo.is_infinite:
                if ristretto:
                    continue
                L = _limite(f, estremo, lato if estremo.is_finite else '+', 6)
                limiti.append({'tex': r'\lim_{x \to %s} f(x) = %s' % (tex(estremo), _tex_lim(L))})
                if L is not None and L.is_finite:
                    asintoti.append({'tipo': 'orizzontale', 'tex': 'y = ' + tex(L), 'dove': 'x → ' + ('+∞' if estremo > 0 else '−∞'),
                                     'js': js(L + 0 * x), 'm': 0, 'q': a_float(L)})
                elif L is not None:
                    m = _limite(f / x, estremo, '+', 6)
                    if m is not None and m.is_finite and m != 0:
                        q = _limite(f - m * x, estremo, '+', 6)
                        if q is not None and q.is_finite:
                            asintoti.append({'tipo': 'obliquo', 'tex': 'y = ' + tex(m * x + q),
                                             'dove': 'x → ' + ('+∞' if estremo > 0 else '−∞'),
                                             'm': a_float(m), 'q': a_float(q)})
            else:
                L = _limite(f, estremo, lato, 4)
                limiti.append({'tex': r'\lim_{x \to %s^{%s}} f(x) = %s' % (tex(estremo), lato, _tex_lim(L))})
                if L is not None and L.is_infinite:
                    asintoti.append({'tipo': 'verticale', 'tex': 'x = ' + tex(estremo), 'dove': 'x → ' + _txt(estremo) + lato,
                                     'xv': a_float(estremo)})
    visti, asin_unici = set(), []
    for a_ in asintoti:
        k = (a_['tipo'], a_['tex'])
        if k in visti:
            for u in asin_unici:
                if (u['tipo'], u['tex']) == k:
                    u['dove'] += ', ' + a_['dove']
            continue
        visti.add(k)
        asin_unici.append(a_)

    return {
        'f_tex': tex(f), 'f1_tex': tex(f1), 'f2_tex': tex(f2),
        'f1_grezza_tex': tex(f1_grezza) if f1_grezza != f1 else None,
        'f2_grezza_tex': tex(f2_grezza) if f2_grezza != f2 else None,
        'f1_fatt_tex': _fattorizzata(f1), 'f2_fatt_tex': _fattorizzata(f2),
        'f_js': js(f), 'f1_js': js(f1), 'f2_js': js(f2),
        'dominio_tex': _tex_dominio(D_tutto, intervallo) if D_tutto is not None else None,
        'estremi': estremi, 'flessi': flessi, 'speciali': speciali, 'assoluti': assoluti,
        'stazionari': lista_staz,
        'monotonia': monotonia, 'concavita': concavita,
        'limiti': limiti, 'asintoti': asin_unici,
        'finestra': list(finestra), 'ristretto': ristretto, 'note': note,
        'intervallo': [float(intervallo[0]), float(intervallo[1])] if intervallo else None,
    }


def _par(e):
    return r'\left(%s\right)' % tex(e) if (e.is_Add or e.could_extract_minus_sign()) else tex(e)


def _txt(e):
    v = a_float(e)
    return fmt(v) if v is not None else str(e)


def _tex_estremo(e, v):
    if math.isinf(v):
        return r'+\infty' if v > 0 else r'-\infty'
    if isinstance(e, sp.Float):
        return fmt(v)
    return tex(e)


def _fattorizzata(e):
    r = prova(lambda: sp.factor(sp.together(e)), 4)
    if r is None or r == e or sp.count_ops(r) > sp.count_ops(e) + 6:
        return None
    return tex(pulisci(r))


def _tex_dominio(D, intervallo):
    if D == sp.S.Reals:
        return r'\mathbb{R}'
    s = tex(D)
    return s


# ---------------------------------------------------------------- verifica derivata

def verifica(testo_f, testo_tentativo, ordine):
    f = leggi(testo_f)
    u = leggi(testo_tentativo, 'derivata')
    d = pulisci(sp.diff(f, x))
    if int(ordine) == 2:
        d = pulisci(sp.diff(semplifica(d), x))
    diff_ = prova(lambda: sp.simplify(per_dominio(u - d)), 6)
    if diff_ is not None and diff_ == 0:
        return {'corretta': True, 'msg': 'Giusta: è equivalente alla derivata corretta.'}
    dn, un = numerica(d), numerica(u)
    rnd = random.Random(7)
    prove, errore = 0, None
    for _ in range(400):
        t = rnd.uniform(-8, 8)
        a_, b_ = dn(t), un(t)
        if a_ is None:
            continue
        prove += 1
        if b_ is None or abs(a_ - b_) > 1e-7 * (1 + abs(a_)):
            errore = (t, a_, b_)
            break
        if prove >= 25:
            break
    if errore is None and prove >= 5:
        return {'corretta': True, 'msg': 'Giusta: coincide con la derivata corretta in tutti i punti provati.'}
    if errore is None:
        return {'corretta': None, 'msg': 'Non riesco a confrontarla: prova a scriverla in un’altra forma.'}
    t, a_, b_ = errore
    return {'corretta': False,
            'msg': f'Non torna: in x = {fmt(t)} la derivata giusta vale {fmt(a_)}, la tua {fmt(b_)}.',
            'giusta_tex': tex(semplifica(d))}


def anteprima(testo):
    return {'tex': tex(leggi(testo))}
