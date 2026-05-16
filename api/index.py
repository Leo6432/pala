import os
import math
import random
import time
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://api.paladium.games/v1"
API_KEY = os.getenv("PALADIUM_API_KEY", "")
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true" or not API_KEY

# ── Mock data ────────────────────────────────────────────────────────────────

def _gen_history(base: float, days: int = 30, vol: float = 0.15) -> list[dict]:
    history, price = [], base
    now = datetime.utcnow()
    for i in range(days):
        date = now - timedelta(days=days - i)
        price = max(1, price + random.gauss(0, vol * base) + math.sin(i / 7 * math.pi) * base * 0.05)
        history.append({"date": date.strftime("%Y-%m-%d"), "price": round(price, 2), "volume": random.randint(5, 200)})
    return history

MOCK_MARKET = [
    {"id": "diamond",         "display_name": "Diamant",             "price": 2800},
    {"id": "iron_ingot",      "display_name": "Lingot de Fer",       "price": 45},
    {"id": "gold_ingot",      "display_name": "Lingot d'Or",         "price": 380},
    {"id": "emerald",         "display_name": "Emeraude",            "price": 120},
    {"id": "netherite_ingot", "display_name": "Lingot de Netherite", "price": 85000},
    {"id": "redstone",        "display_name": "Redstone",            "price": 12},
    {"id": "lapis_lazuli",    "display_name": "Lapis Lazuli",        "price": 55},
    {"id": "coal",            "display_name": "Charbon",             "price": 8},
    {"id": "obsidian",        "display_name": "Obsidienne",          "price": 95},
    {"id": "blaze_rod",       "display_name": "Baton de Blaze",      "price": 220},
    {"id": "ender_pearl",     "display_name": "Perle de l'Ender",    "price": 175},
    {"id": "slimeball",       "display_name": "Boule de Slime",      "price": 68},
]
MOCK_HISTORIES = {item["id"]: _gen_history(item["price"]) for item in MOCK_MARKET}
MOCK_STATUS = {"online": True, "players": random.randint(800, 2400), "max_players": 3000}

# ── Paladium API ──────────────────────────────────────────────────────────────

_cache: dict = {}

def _get(path: str, ttl: int = 60) -> dict | list | None:
    now = time.time()
    if path in _cache and now - _cache[path]["ts"] < ttl:
        return _cache[path]["data"]
    try:
        r = httpx.get(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        _cache[path] = {"data": data, "ts": now}
        return data
    except Exception as e:
        print(f"[API] {path} → {e}")
        return None

def get_status():
    return _get("/status", ttl=30)

def get_market_items():
    # Returns list of market items
    return _get("/paladium/shop/market/items", ttl=60)

def get_market_categories():
    return _get("/paladium/shop/market/categories", ttl=300)

def get_item_detail(item_id: str):
    return _get(f"/paladium/shop/market/items/{item_id}", ttl=60)

def get_item_history(item_id: str):
    return _get(f"/paladium/shop/market/items/{item_id}/history", ttl=120)

# ── Normalise API responses ───────────────────────────────────────────────────

def _normalise_market(raw: list | dict | None) -> list[dict]:
    """Convert the Paladium market response to [{id, display_name, price}]."""
    if not raw:
        return []
    items = raw if isinstance(raw, list) else raw.get("items") or raw.get("data") or []
    result = []
    for item in items:
        iid = item.get("id") or item.get("item") or item.get("name") or ""
        name = item.get("displayName") or item.get("display_name") or item.get("name") or iid
        price = item.get("price") or item.get("lastPrice") or item.get("currentPrice") or 0
        if iid:
            result.append({"id": iid, "display_name": name, "price": float(price)})
    return result

def _normalise_history(raw: list | dict | None) -> list[dict]:
    """Convert the Paladium history response to [{date, price, volume}]."""
    if not raw:
        return []
    entries = raw if isinstance(raw, list) else raw.get("history") or raw.get("data") or []
    result = []
    for e in entries:
        ts = e.get("timestamp") or e.get("date") or e.get("time") or ""
        price = e.get("price") or e.get("averagePrice") or e.get("value") or 0
        vol = e.get("volume") or e.get("quantity") or 0
        if ts and price:
            # Convert unix timestamp to date string if needed
            if isinstance(ts, (int, float)):
                ts = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            result.append({"date": str(ts)[:10], "price": float(price), "volume": int(vol)})
    return result

def _normalise_status(raw: dict | None) -> dict:
    if not raw:
        return {"online": False, "players": 0, "max_players": 3000}
    # The status response has nested server info
    java = raw.get("java") or {}
    global_ = java.get("global") or {}
    online = raw.get("online") if "online" in raw else True
    players = global_.get("players") or raw.get("players") or 0
    max_p = global_.get("maxPlayers") or raw.get("maxPlayers") or raw.get("max_players") or 3000
    return {"online": online, "players": players, "max_players": max_p}

# ── Analyzer ─────────────────────────────────────────────────────────────────

def _recommend(history: list[dict]) -> dict:
    if not history or len(history) < 3:
        return {"action": "attendre", "reason": "Pas assez de donnees", "confidence": 0,
                "current_price": 0, "avg_price": 0, "min_price": 0, "max_price": 0,
                "trend_pct": 0, "score": 0}
    prices = [h["price"] for h in history if "price" in h]
    current, avg = prices[-1], sum(prices) / len(prices)
    min_p, max_p = min(prices), max(prices)
    spread = max_p - min_p or 1
    short = prices[-5:] if len(prices) >= 5 else prices
    long_ = prices[-20:] if len(prices) >= 20 else prices
    trend = (sum(short) / len(short) - sum(long_) / len(long_)) / (sum(long_) / len(long_)) * 100
    position = (current - min_p) / spread
    score, reasons = 0, []
    if position < 0.25:
        score += 2; reasons.append(f"Prix bas (fourchette {min_p:.0f}-{max_p:.0f})")
    elif position > 0.75:
        score -= 2; reasons.append("Prix eleve dans la fourchette")
    if trend < -5:
        score += 1; reasons.append(f"Tendance baissiere ({trend:.1f}%) rebond possible")
    elif trend > 5:
        score -= 1; reasons.append(f"Tendance haussiere ({trend:.1f}%) risque de surpayer")
    if current < avg * 0.9:
        score += 1; reasons.append(f"Sous la moyenne ({avg:.0f})")
    elif current > avg * 1.1:
        score -= 1; reasons.append(f"Au-dessus de la moyenne ({avg:.0f})")
    action = "acheter" if score >= 2 else "vendre" if score <= -2 else "attendre"
    return {"action": action, "reason": " | ".join(reasons) or "Prix normal",
            "confidence": min(round(abs(score) / 4 * 100), 100),
            "current_price": current, "avg_price": round(avg, 2),
            "min_price": min_p, "max_price": max_p, "trend_pct": round(trend, 2), "score": score}

def _analyze(market, histories):
    results = []
    for item in market:
        iid = item.get("id") or item.get("name", "")
        rec = _recommend(histories.get(iid, []))
        results.append({"id": iid, "name": item.get("display_name") or iid,
                        "current_price": item.get("price") or rec["current_price"], **rec})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI()

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _data():
    if USE_MOCK:
        return MOCK_MARKET, MOCK_HISTORIES, MOCK_STATUS

    raw_market = get_market_items()
    market = _normalise_market(raw_market) or MOCK_MARKET

    raw_status = get_status()
    status = _normalise_status(raw_status)

    histories = {}
    for item in market:
        iid = item["id"]
        raw_h = get_item_history(iid)
        histories[iid] = _normalise_history(raw_h)

    return market, histories, status


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    market, histories, status = _data()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "items": _analyze(market, histories),
        "status": status, "use_mock": USE_MOCK,
    })

@app.get("/api/items")
async def api_items():
    market, histories, _ = _data()
    return _analyze(market, histories)

@app.get("/api/item/{item_id}/history")
async def api_history(item_id: str):
    if USE_MOCK:
        return MOCK_HISTORIES.get(item_id, [])
    return _normalise_history(get_item_history(item_id))

@app.get("/api/status")
async def api_status():
    if USE_MOCK:
        return MOCK_STATUS
    return _normalise_status(get_status())
