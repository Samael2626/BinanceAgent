"""
Binance Trading Bot - Stable Version 1.8.0
(c) 2026 - Satanael26/BinanceAgent
Architecture: FastAPI / React
"""
from fastapi import FastAPI, HTTPException, Body, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import secrets
from typing import Optional
from .bot_manager import BotManager
from .database import DatabaseManager
from .services.telegram_manager import TelegramManager
from .config import TELEGRAM_BOT_TOKEN
from contextlib import asynccontextmanager

# Initialize Bot Manager and Database
bot_manager = BotManager()
db = DatabaseManager()

# Initialize Telegram Manager
tg_manager = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN":
    try:
        tg_manager = TelegramManager(
            TELEGRAM_BOT_TOKEN, bot_manager=bot_manager)
        tg_manager.start_in_thread()
        print("✅ Telegram Bot interartivo iniciado.")
    except Exception as e:
        print(f"⚠️ Error al iniciar Telegram Bot: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Auto-initialize bots for active sessions
    print("\n🔄 Verificando sesiones activas para auto-inicio...")
    try:
        users = db.get_all_users()
        # Filter only users who have a session token (recently active)
        active_users = [u for u in users if u.get('session_token')]

        if not active_users:
            print("ℹ️ No hay sesiones activas para auto-iniciar.")
        else:
            print(f"📂 Encontradas {len(active_users)} sesiones activas.")
            for user in active_users:
                try:
                    bot = bot_manager.get_or_create_bot(
                        user['id'],
                        user['api_key'],
                        user['api_secret'],
                        user['is_testnet']
                    )
                    print(
                        f"✅ Bot auto-iniciado: {user['username']} ({'Testnet' if user['is_testnet'] else 'REAL'})")
                except Exception as e:
                    print(
                        f"⚠️ Error al auto-iniciar bot para {user['username']}: {e}")
    except Exception as e:
        print(f"❌ Error al consultar usuarios en el inicio: {e}")

    yield
    # Shutdown logic
    print("Shutting down: Disconnecting all active bots...")
    with bot_manager.lock:
        for user_id in list(bot_manager.bots.keys()):
            bot = bot_manager.bots.get(user_id)
            if bot:
                bot.disconnect()
    print("Shutdown complete.")

# Initialize App
app = FastAPI(title="Binance Trading Bot API",
              version="1.8.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== AUTHENTICATION MIDDLEWARE ==========

async def get_current_user(request: Request):
    """Extract user from session token"""
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(
            status_code=401, detail="No autorizado. Por favor inicia sesión.")

    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=401, detail="Sesión inválida. Por favor inicia sesión nuevamente.")

    return user


# ========== AUTHENTICATION ENDPOINTS ==========

@app.post("/api/auth/register")
def register(credentials: dict = Body(...)):
    """Register a new user with Binance API credentials"""
    username = credentials.get("username")
    api_key = credentials.get("api_key")
    api_secret = credentials.get("api_secret")
    is_testnet = credentials.get("is_testnet", True)

    if not all([username, api_key, api_secret]):
        raise HTTPException(
            status_code=400,
            detail="Faltan datos: username, api_key y api_secret son requeridos"
        )

    # Check if user already exists
    existing_user = db.get_user_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    try:
        # Create user in database
        user_id = db.create_user(username, api_key, api_secret, is_testnet)

        # Create bot instance and validate credentials
        bot = bot_manager.get_or_create_bot(
            user_id, api_key, api_secret, is_testnet)

        # Generate session token
        session_token = secrets.token_urlsafe(32)
        db.set_user_session(user_id, session_token)

        mode = "Testnet (Simulación)" if is_testnet else "⚠️ CUENTA REAL"

        return {
            "status": "success",
            "message": f"Usuario registrado y conectado a {mode}",
            "token": session_token,
            "user": {
                "id": user_id,
                "username": username,
                "is_testnet": is_testnet
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {str(e)}"
        )


@app.post("/api/auth/login")
def login(credentials: dict = Body(...)):
    """Login with username"""
    username = credentials.get("username")

    if not username:
        raise HTTPException(status_code=400, detail="Username requerido")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    try:
        # Initialize bot with stored credentials
        bot = bot_manager.get_or_create_bot(
            user['id'],
            user['api_key'],
            user['api_secret'],
            user['is_testnet']
        )

        # Generate new session token
        session_token = secrets.token_urlsafe(32)
        db.set_user_session(user['id'], session_token)

        mode = "Testnet (Simulación)" if user['is_testnet'] else "⚠️ CUENTA REAL"

        return {
            "status": "success",
            "message": f"Sesión iniciada en {mode}",
            "token": session_token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "is_testnet": user['is_testnet']
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al iniciar sesión: {str(e)}"
        )


@app.post("/api/auth/logout")
def logout(user: dict = Depends(get_current_user)):
    """Logout current user"""
    try:
        db.clear_user_session(user['id'])
        bot_manager.stop_bot(user['id'])
        return {"status": "success", "message": "Sesión cerrada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": user['id'],
        "username": user['username'],
        "is_testnet": user['is_testnet']
    }


# ========== BOT ENDPOINTS ==========

@app.get("/")
def read_root():
    return {"status": "online", "message": "Binance Trading Bot Backend v1.8.0 Stable - Multi-User"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/status")
def get_bot_status(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.get_status()


@app.get("/api/tickers")
def get_tickers(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.get_tickers()


@app.post("/api/start")
def start_bot(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.start()


@app.post("/api/stop")
def stop_bot(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.stop()


@app.post("/api/buy")
def manual_buy(payload: dict = Body(default=None), user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    custom_qty = payload.get("quantity") if payload else None
    return bot.manual_buy(custom_qty=custom_qty)


@app.post("/api/sell")
def manual_sell(payload: dict = Body(default=None), user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    custom_qty = payload.get("quantity") if payload else None
    return bot.manual_sell(custom_qty=custom_qty)


@app.get("/api/test-connection")
def test_connection(user: dict = Depends(get_current_user)):
    """Test Binance connection and return connection status"""
    bot = bot_manager.get_bot(user['id'])
    if not bot or not bot.client:
        return {
            "connected": False,
            "message": "No hay cliente inicializado. Por favor inicia sesión primero.",
            "mode": None
        }

    try:
        # Test connection by getting server time
        server_time = bot.client.client.get_server_time()

        # Get balances
        usdt_balance = bot.client.get_account_balance("USDT")
        btc_balance = bot.client.get_account_balance("BTC")

        mode = "Testnet (Simulación)" if bot.is_testnet else "⚠️ CUENTA REAL"

        return {
            "connected": True,
            "mode": mode,
            "is_testnet": bot.is_testnet,
            "server_time": server_time,
            "balances": {
                "USDT": usdt_balance,
                "BTC": btc_balance
            },
            "message": f"✅ Conectado exitosamente a Binance ({mode})"
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error de conexión: {str(e)}",
            "mode": "Testnet (Simulación)" if bot.is_testnet else "⚠️ CUENTA REAL"
        }


@app.get("/api/market/rsi-snapshot")
def get_rsi_snapshot(user: dict = Depends(get_current_user)):
    """
    Returns RSI for all active trading pairs.
    Response format:
    [
      { "symbol": "SOLUSDT", "rsi": 42.3 },
      { "symbol": "BTCUSDT", "rsi": 55.1 }
    ]
    """
    from .rsi_snapshot import calculate_rsi_snapshot, get_default_symbols
    from datetime import datetime

    bot = bot_manager.get_bot(user['id'])
    if not bot or not bot.client:
        raise HTTPException(status_code=404, detail="Bot no inicializado")

    try:
        # Use data_client for market data (supports real data in testnet mode)
        client = bot.data_client if hasattr(
            bot, 'data_client') and bot.data_client else bot.client

        # Get symbols to monitor (use default list for now)
        symbols = get_default_symbols()

        # Calculate RSI snapshot (Sync with bot's timeframe)
        snapshot = calculate_rsi_snapshot(
            symbols, client, timeframe=bot.timeframe)

        # Log update
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] RSI Snapshot actualizado: {len(snapshot)} símbolos")

        return snapshot
    except Exception as e:
        print(f"Error en RSI snapshot: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error calculando RSI: {str(e)}")


@app.post("/api/reset")
def reset_position(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.reset_position()


@app.post("/api/reset_pnl")
def reset_pnl(user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.reset_pnl()


@app.post("/api/settings")
def update_settings(settings: dict = Body(...), user: dict = Depends(get_current_user)):
    bot = bot_manager.get_bot(user['id'])
    if not bot:
        raise HTTPException(status_code=404, detail="Bot no inicializado")
    return bot.update_settings(settings)


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Iniciando Backend de Binance Bot...")
    print("📍 URL: http://127.0.0.1:8000")
    print("📝 Documentación: http://127.0.0.1:8000/docs\n")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
