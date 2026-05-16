import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from paladium_api import get_market_prices, get_item_history, get_server_status
from analyzer import analyze_all_items
from mock_data import MOCK_MARKET, MOCK_HISTORIES, MOCK_STATUS

app = FastAPI(title="Paladium Market Dashboard")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
templates = Jinja2Templates(directory=TEMPLATES_DIR)

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"


def _get_market_data():
    if USE_MOCK:
        return MOCK_MARKET, MOCK_HISTORIES, MOCK_STATUS
    market = get_market_prices() or MOCK_MARKET
    status = get_server_status() or MOCK_STATUS
    histories = {}
    for item in market:
        item_id = item.get("id") or item.get("name", "")
        histories[item_id] = get_item_history(item_id) or []
    return market, histories, status


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    market, histories, status = _get_market_data()
    analysis = analyze_all_items(market, histories)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "items": analysis,
        "status": status,
        "use_mock": USE_MOCK,
    })


@app.get("/api/items")
async def api_items():
    market, histories, status = _get_market_data()
    return analyze_all_items(market, histories)


@app.get("/api/item/{item_id}/history")
async def api_item_history(item_id: str):
    if USE_MOCK:
        return MOCK_HISTORIES.get(item_id, [])
    return get_item_history(item_id) or []


@app.get("/api/status")
async def api_status():
    if USE_MOCK:
        return MOCK_STATUS
    return get_server_status() or MOCK_STATUS
