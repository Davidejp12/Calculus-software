# Calculus software

Studio di funzione completo che gira in locale, pensato per prepararsi alle verifiche di analisi.

Scrivi una funzione (es. `x^3 - 3x`, `ln(x)/x`, `|x^2 - 4|`, `sen(x) + cos(x)`) e ottieni, passo per passo:

1. dominio e limiti agli estremi
2. derivata prima (con controllo della derivata calcolata a mano)
3. punti stazionari, con la loro natura
4. schema dei segni di f′, crescenza, massimi e minimi
5. derivata seconda
6. schema dei segni di f″, concavità e flessi (con tangente inflessionale)
7. asintoti verticali, orizzontali e obliqui

Il grafico interattivo mostra f, f′, f″ e i punti notevoli. I risultati sono esatti (√3, e, π/2…) grazie a [SymPy](https://www.sympy.org).

## Avvio

Serve Python 3.

```sh
python3 -m venv .venv
.venv/bin/pip install sympy
.venv/bin/python server.py
```

Si apre http://localhost:8810. Su macOS basta un doppio clic su `avvia.command`.

Funziona senza internet: KaTeX e il font sono inclusi in `static/vendor`.

## Come si scrivono le funzioni

| Scrivi | Significa |
|---|---|
| `3x^2 - 2x` | potenze con `^`, il `*` si può omettere |
| `e^(-x)`, `ln(x)` | esponenziale e logaritmo naturale |
| `sen(x)`, `cos(x)`, `tg(x)`, `arctg(x)` | goniometriche |
| `sqrt(x)`, `cbrt(x)`, `x^(2/3)` | radici (le radici di indice dispari valgono anche per x < 0) |
| `\|x - 1\|` | valore assoluto |

## Licenze di terze parti

- [KaTeX](https://katex.org) — MIT
- [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/) — SIL Open Font License
