"""Server locale: http://localhost:8810 — pagine in static/, calcoli in analisi.py."""
import json
import math
import multiprocessing as mp
import os
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import analisi

PORTA = int(os.environ.get('PORTA', 8810))
CARTELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
TEMPO_MAX = 40

AZIONI = {
    'studio': lambda d: analisi.studio(d.get('f', ''), d.get('a', ''), d.get('b', '')),
    'verifica': lambda d: analisi.verifica(d.get('f', ''), d.get('tentativo', ''), d.get('ordine', 1)),
    'anteprima': lambda d: analisi.anteprima(d.get('f', '')),
}


def _pulito(v):
    """JSON valido per il browser: niente NaN/inf."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: _pulito(w) for k, w in v.items()}
    if isinstance(v, (list, tuple)):
        return [_pulito(w) for w in v]
    return v


def _esegui(azione, dati, coda):
    try:
        coda.put({'ok': True, 'dati': _pulito(AZIONI[azione](dati))})
    except analisi.ErroreInput as e:
        coda.put({'ok': False, 'errore': str(e)})
    except Exception as e:
        coda.put({'ok': False, 'errore': f'Errore di calcolo ({type(e).__name__}). Prova a riscrivere la funzione.'})


def calcola(azione, dati):
    """Ogni calcolo gira in un processo separato, così un conto infinito non blocca nulla."""
    ctx = mp.get_context('fork')
    coda = ctx.Queue()
    p = ctx.Process(target=_esegui, args=(azione, dati, coda), daemon=True)
    p.start()
    try:
        return coda.get(timeout=TEMPO_MAX)
    except Exception:
        return {'ok': False, 'errore': 'Il calcolo ci mette troppo. Prova a semplificare la funzione '
                                       'o a scegliere un intervallo.'}
    finally:
        if p.is_alive():
            p.kill()
        p.join(1)


class Gestore(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=CARTELLA, **kw)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_POST(self):
        azione = self.path.strip('/').removeprefix('api/')
        if azione not in AZIONI:
            self.send_error(404)
            return
        try:
            n = int(self.headers.get('Content-Length', 0))
            dati = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            dati = {}
        risposta = json.dumps(calcola(azione, dati), default=str).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(risposta)))
        self.end_headers()
        self.wfile.write(risposta)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', PORTA), Gestore)
    url = f'http://localhost:{PORTA}'
    print(f'Analisi pronto su {url}  (chiudi con ctrl+C)')
    if '--no-browser' not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
