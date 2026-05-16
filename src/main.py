from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

from paladium_api import get_market_prices, get_item_history, get_server_status
from analyzer import analyze_all_items, compute_recommendation
from mock_data import MOCK_MARKET, MOCK_HISTORIES, MOCK_STATUS

app = FastAPI(title="Paladium Market Dashboard")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
