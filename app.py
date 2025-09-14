from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import a2s
import socket
import time

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # allow all origins for API

# Cache TTL to avoid hammering the server
CACHE_TTL = 8.0  # seconds
_cache = {}

def to_dict(obj):
    """Convert NamedTuple or simple object to dict."""
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    return vars(obj)

def check_game_port(ip, port, timeout=2.0):
    """Check if the game port is open using raw TCP connection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return True
    except:
        return False
    finally:
        s.close()

def query_valheim(ip, query_port=2457, game_port=2456, timeout=5.0):
    """
    Query a Valheim server using A2S protocol.
    Returns a dict with ok, info, players, response_ms, status_reason, game_port_open
    """
    key = f"{ip}:{query_port}"
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached["ts"] < CACHE_TTL:
        return cached["res"]

    result = {"ok": False, "status_reason": "unknown_error", "game_port_open": False}
    start = time.perf_counter()
    addr = (ip, int(query_port))

    try:
        info = a2s.info(addr, timeout=timeout)
        players = a2s.players(addr, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000.0
        game_port_open = check_game_port(ip, game_port, timeout=2.0)

        result.update({
            "ok": True,
            "status_reason": "responded",
            "info": to_dict(info),
            "players": [to_dict(p) for p in players],
            "player_count": len(players),
            "server_name": getattr(info, "server_name", None),
            "response_ms": round(elapsed, 1),
            "game_port_open": game_port_open
        })
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        err_str = str(e).lower()
        if "timed out" in err_str:
            reason = "timeout"
        elif isinstance(e, (ConnectionRefusedError, OSError)) or "refused" in err_str:
            reason = "connection_refused"
        else:
            reason = "unknown_error"
        game_port_open = check_game_port(ip, game_port, timeout=2.0)

        result.update({
            "ok": False,
            "status_reason": reason,
            "error": str(e),
            "response_ms": round(elapsed, 1),
            "game_port_open": game_port_open
        })

    _cache[key] = {"ts": now, "res": result}
    return result

@app.route("/api/status")
def status():
    """
    Endpoint: /api/status?ip=159.223.189.211&query_port=2457&game_port=2456&timeout=5
    Returns JSON with server info.
    """
    ip = request.args.get("ip", "159.223.189.211")
    query_port = int(request.args.get("query_port", 2457))
    game_port = int(request.args.get("game_port", 2456))
    timeout = float(request.args.get("timeout", 5.0))

    res = query_valheim(ip, query_port, game_port, timeout)

    # heuristics: if A2S responds and game port is open, server is joinable
    res["ip"] = ip
    res["query_port"] = query_port
    res["game_port"] = game_port
    res["guess_game_port_open"] = res.get("game_port_open", False)
    res["status_message"] = (
        "Server is online and joinable." if res.get("ok") and res.get("game_port_open")
        else "Server is not responding or not joinable."
    )

    return jsonify(res)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    # Development mode. In production use gunicorn/uvicorn + reverse proxy.
    app.run(host="0.0.0.0", port=5000, debug=False)
