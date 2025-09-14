from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import a2s
import socket
import time

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

CACHE_TTL = 8.0  # segundos
_cache = {}

def to_dict(obj):
    """Convierte NamedTuple u objeto simple en dict."""
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    return vars(obj)

def tcp_check(ip, port, timeout=3.0):
    """
    Intenta abrir una conexión TCP al puerto especificado.
    Devuelve True si conecta, False en caso contrario.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def query_valheim(ip, query_port=2457, game_port=2456, timeout=5.0):
    """
    Intenta obtener información del servidor Valheim.
    1. Primero usando A2S en query_port.
    2. Si falla, prueba conexión TCP al game_port como fallback.
    """
    key = f"{ip}:{query_port}"
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached["ts"] < CACHE_TTL:
        return cached["res"]

    addr = (ip, int(query_port))
    result = {"ok": False, "status_reason": "unknown_error"}
    start = time.perf_counter()

    try:
        # Intento A2S
        info = a2s.info(addr, timeout=timeout)
        players = a2s.players(addr, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000.0
        result.update({
            "ok": True,
            "status_reason": "responded",
            "info": to_dict(info),
            "players": [to_dict(p) for p in players],
            "player_count": len(players),
            "server_name": getattr(info, "server_name", None),
            "response_ms": round(elapsed, 1),
        })
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        err_str = str(e).lower()
        # fallback TCP al puerto de juego
        if tcp_check(ip, game_port, timeout=3.0):
            result.update({
                "ok": True,
                "status_reason": "game_port_only",
                "error": str(e),
                "response_ms": round(elapsed, 1),
                "players": [],
            })
        else:
            result.update({
                "ok": False,
                "status_reason": "unreachable",
                "error": str(e),
                "response_ms": round(elapsed, 1),
            })

    _cache[key] = {"ts": now, "res": result}
    return result

@app.route("/api/status")
def status():
    ip = request.args.get("ip", "159.223.189.211")
    query_port = int(request.args.get("query_port", 2457))
    game_port = int(request.args.get("game_port", 2456))
    timeout = float(request.args.get("timeout", 5.0))

    res = query_valheim(ip, query_port, game_port, timeout)

    res["ip"] = ip
    res["query_port"] = query_port
    res["game_port"] = game_port
    res["guess_game_port_open"] = res["ok"]

    return jsonify(res)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
