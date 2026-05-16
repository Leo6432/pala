import httpx
import time
from typing import Optional

BASE_URL = "https://api.paladium.games/v1"

_cache: dict = {}
CACHE_TTL = 60  # seconds


def _cached_get(url: str, params: dict = None) -> dict | list | None:
    key = url + str(params)
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    try:
        r = httpx.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        _cache[key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        print(f"[API] Error fetching {url}: {e}")
        return None


def get_player(pseudo: str) -> dict | None:
    return _cached_get(f"{BASE_URL}/player/{pseudo}")


def get_leaderboard(game: str = "global", page: int = 1) -> list | None:
    return _cached_get(f"{BASE_URL}/leaderboard/{game}", {"page": page})


def get_market_prices() -> list | None:
    return _cached_get(f"{BASE_URL}/market/prices")


def get_item_history(item_id: str) -> list | None:
    return _cached_get(f"{BASE_URL}/market/history/{item_id}")


def get_server_status() -> dict | None:
    return _cached_get(f"{BASE_URL}/status")
