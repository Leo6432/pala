"""
Données de démonstration utilisées quand l'API Paladium n'est pas accessible.
Simule des historiques de prix réalistes avec variations aléatoires.
"""
import random
import math
from datetime import datetime, timedelta


def _generate_price_history(base: float, days: int = 30, volatility: float = 0.15) -> list[dict]:
    history = []
    price = base
    now = datetime.utcnow()
    for i in range(days):
        date = now - timedelta(days=days - i)
        noise = random.gauss(0, volatility * base)
        # Add a slight sinusoidal cycle to simulate market patterns
        cycle = math.sin(i / 7 * math.pi) * base * 0.05
        price = max(1, price + noise + cycle)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(price, 2),
            "volume": random.randint(5, 200),
        })
    return history


MOCK_MARKET = [
    {"id": "diamond", "display_name": "Diamant", "price": 2800},
    {"id": "iron_ingot", "display_name": "Lingot de Fer", "price": 45},
    {"id": "gold_ingot", "display_name": "Lingot d'Or", "price": 380},
    {"id": "emerald", "display_name": "Émeraude", "price": 120},
    {"id": "netherite_ingot", "display_name": "Lingot de Netherite", "price": 85000},
    {"id": "redstone", "display_name": "Redstone", "price": 12},
    {"id": "lapis_lazuli", "display_name": "Lapis Lazuli", "price": 55},
    {"id": "coal", "display_name": "Charbon", "price": 8},
    {"id": "obsidian", "display_name": "Obsidienne", "price": 95},
    {"id": "blaze_rod", "display_name": "Bâton de Blaze", "price": 220},
    {"id": "ender_pearl", "display_name": "Perle de l'Ender", "price": 175},
    {"id": "slimeball", "display_name": "Boule de Slime", "price": 68},
]

MOCK_HISTORIES = {
    item["id"]: _generate_price_history(item["price"])
    for item in MOCK_MARKET
}

MOCK_STATUS = {
    "online": True,
    "players": random.randint(800, 2400),
    "max_players": 3000,
    "version": "1.20.x",
}
