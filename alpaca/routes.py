from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/status")
async def get_status():
    return {"status": "ok"}

@router.get("/trade/{symbol}")
async def get_trade(symbol: str):
    # Example: Replace with real trading logic
    if symbol.upper() not in ["AAPL", "GOOG", "TSLA"]:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return {"symbol": symbol.upper(), "price": 123.45}