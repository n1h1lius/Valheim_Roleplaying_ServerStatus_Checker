from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import a2s
import time

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

CACHE_TTL = 8.0  # seconds
_cache = {}

def query_valheim(ip, query_port=2457, timeout=5.0):
    key = f"{ip}:{query_port}"
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached["ts"] < CACHE_TTL:
        return cached["res"]

    addr = (ip, int(query_port))
    result = {"ok": False, "status_reason": "unknown_error"}
    start = time.perf_counter()
    try:
        info = a2s.info(addr, timeout=timeout)
        players = a2s.players(addr, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000.0

        result.update({
            "ok": True,
            "status_reason": "responded",
            "info": {
                "server_name": getattr(info, "server_name", None),
                "map_name": getattr(info, "map_name", None),
                "version": getattr(info, "version", None),
                "server_type": getattr(info, "server_type", None),
                "max_players": getattr(info, "max_players", None),
                "password_protected": getattr(info, "password_protected", None),
                "platform": getattr(info, "platform", None),
                "steam_id": getattr(info, "steam_id", None),
                "app_id": getattr(info, "app_id", None),
                "game_id": getattr(info, "game_id", None),
                "keywords": getattr(info, "keywords", None)
            },
            "players": [
                {"name": p.name, "duration": round(p.duration), "score": p.score}
                for p in players
            ],
            "player_count": len(players),
            "ping_ms": round(elapsed, 1),
            "query_port": query_port,
            "game_port": query_port - 1,
            "ip": ip
        })
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        err_str = str(e).lower()
        if "timed out" in err_str:
            reason = "timeout"
        elif "refused" in err_str:
            reason = "connection_refused"
        else:
            reason = "unknown_error"

        result.update({
            "ok": False,
            "status_reason": reason,
            "error": str(e),
            "ping_ms": round(elapsed, 1),
            "query_port": query_port,
            "game_port": query_port - 1,
            "ip": ip,
            "players": [],
            "player_count": 0
        })

    _cache[key] = {"ts": now, "res": result}
    return result

@app.route("/api/status")
def status():
    ip = request.args.get("ip", "159.223.189.211")
    query_port = int(request.args.get("query_port", 2457))
    timeout = float(request.args.get("timeout", 5.0))
    res = query_valheim(ip, query_port, timeout)
    return jsonify(res)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
