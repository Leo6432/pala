from typing import Optional


def compute_recommendation(history: list[dict]) -> dict:
    """
    Analyzes price history to give a buy/sell/wait recommendation.
    Expects history items with keys: {"date": str, "price": float, "volume": int}
    """
    if not history or len(history) < 3:
        return {"action": "wait", "reason": "Pas assez de données", "confidence": 0}

    prices = [h["price"] for h in history if "price" in h]
    if not prices:
        return {"action": "wait", "reason": "Données invalides", "confidence": 0}

    current = prices[-1]
    avg = sum(prices) / len(prices)
    min_p = min(prices)
    max_p = max(prices)
    spread = max_p - min_p if max_p != min_p else 1

    # Simple moving average (last 5 vs last 20)
    short = prices[-5:] if len(prices) >= 5 else prices
    long_ = prices[-20:] if len(prices) >= 20 else prices
    sma_short = sum(short) / len(short)
    sma_long = sum(long_) / len(long_)

    # Trend: positive = rising, negative = falling
    trend = (sma_short - sma_long) / sma_long * 100

    # Position relative to range
    position = (current - min_p) / spread  # 0 = at min, 1 = at max

    # Score: buy if price is low + trend reversing up, sell if high + trend still up
    score = 0
    reasons = []

    if position < 0.25:
        score += 2
        reasons.append(f"Prix bas (dans le bas 25% de la fourchette {min_p:.0f}–{max_p:.0f})")
    elif position > 0.75:
        score -= 2
        reasons.append(f"Prix élevé (dans le haut 25% de la fourchette)")

    if trend < -5:
        score += 1
        reasons.append(f"Tendance baissière ({trend:.1f}%) → rebond possible")
    elif trend > 5:
        score -= 1
        reasons.append(f"Tendance haussière ({trend:.1f}%) → risque de surpayer")

    if current < avg * 0.9:
        score += 1
        reasons.append(f"Prix actuel {current:.0f} sous la moyenne ({avg:.0f})")
    elif current > avg * 1.1:
        score -= 1
        reasons.append(f"Prix actuel {current:.0f} au-dessus de la moyenne ({avg:.0f})")

    confidence = min(abs(score) / 4 * 100, 100)

    if score >= 2:
        action = "acheter"
    elif score <= -2:
        action = "vendre"
    else:
        action = "attendre"

    return {
        "action": action,
        "reason": " | ".join(reasons) if reasons else "Prix dans la normale",
        "confidence": round(confidence),
        "current_price": current,
        "avg_price": round(avg, 2),
        "min_price": min_p,
        "max_price": max_p,
        "trend_pct": round(trend, 2),
        "score": score,
    }


def analyze_all_items(market: list[dict], histories: dict[str, list[dict]]) -> list[dict]:
    results = []
    for item in market:
        item_id = item.get("id") or item.get("name", "")
        history = histories.get(item_id, [])
        rec = compute_recommendation(history)
        results.append({
            "id": item_id,
            "name": item.get("display_name") or item.get("name", item_id),
            "current_price": item.get("price") or (rec.get("current_price") or 0),
            **rec,
        })
    # Sort by score descending (best buys first)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
