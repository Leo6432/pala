import os
import math
import random
import time
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
    {"id": "diamond",        "display_name": "Diamant",             "price": 2800},
    {"id": "iron_ingot",     "display_name": "Lingot de Fer",       "price": 45},
    {"id": "gold_ingot",     "display_name": "Lingot d'Or",         "price": 380},
    {"id": "emerald",        "display_name": "Emeraude",            "price": 120},
    {"id": "netherite_ingot","display_name": "Lingot de Netherite", "price": 85000},
    {"id": "redstone",       "display_name": "Redstone",            "price": 12},
    {"id": "lapis_lazuli",   "display_name": "Lapis Lazuli",        "price": 55},
    {"id": "coal",           "display_name": "Charbon",             "price": 8},
    {"id": "obsidian",       "display_name": "Obsidienne",          "price": 95},
    {"id": "blaze_rod",      "display_name": "Baton de Blaze",      "price": 220},
    {"id": "ender_pearl",    "display_name": "Perle de l'Ender",    "price": 175},
    {"id": "slimeball",      "display_name": "Boule de Slime",      "price": 68},
]
MOCK_HISTORIES = {item["id"]: _gen_history(item["price"]) for item in MOCK_MARKET}
MOCK_STATUS = {"online": True, "players": random.randint(800, 2400), "max_players": 3000}

# ── Paladium API ──────────────────────────────────────────────────────────────

BASE_URL = "https://api.paladium.games/v1"
_cache: dict = {}

def _get(url: str) -> dict | list | None:
    now = time.time()
    if url in _cache and now - _cache[url]["ts"] < 60:
        return _cache[url]["data"]
    try:
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        _cache[url] = {"data": data, "ts": now}
        return data
    except Exception:
        return None

# ── Analyzer ─────────────────────────────────────────────────────────────────

def _recommend(history: list[dict]) -> dict:
    if not history or len(history) < 3:
        return {"action": "attendre", "reason": "Pas assez de donnees", "confidence": 0,
                "current_price": 0, "avg_price": 0, "min_price": 0, "max_price": 0, "trend_pct": 0, "score": 0}
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

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def _data():
    if USE_MOCK:
        return MOCK_MARKET, MOCK_HISTORIES, MOCK_STATUS
    market = _get(f"{BASE_URL}/market/prices") or MOCK_MARKET
    status = _get(f"{BASE_URL}/status") or MOCK_STATUS
    histories = {item.get("id", ""): (_get(f"{BASE_URL}/market/history/{item.get('id','')}") or []) for item in market}
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
    return _get(f"{BASE_URL}/market/history/{item_id}") or []

@app.get("/api/status")
async def api_status():
    if USE_MOCK:
        return MOCK_STATUS
    return _get(f"{BASE_URL}/status") or MOCK_STATUS
