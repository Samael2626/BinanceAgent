# BinanceAgent

Bot de trading autónomo para Binance con backend en **Python + FastAPI** y frontend en **React + Vite**.

## 🚀 Qué hace
- Gestión de operaciones de trading en modo simulación.
- Monitoriza indicadores técnicos y señales automáticas.
- Interfaz web para controlar el bot en tiempo real.
- Notificaciones por Telegram.

## 🧩 Arquitectura
- `backend/`: API REST y lógica de trading.
- `frontend/`: Interfaz web React.
- `docs/`: Documentación adicional.

## 📌 Requisitos
- Windows, macOS o Linux
- Python 3.12+
- Node.js 18+
- Git

## 🔧 Instalación
```powershell
cd BinanceAgent
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd frontend
npm install
```

## ⚙️ Configuración
1. Copia el archivo de ejemplo:
   ```powershell
   copy backend\.env.example backend\.env
   ```
2. Abre `backend\.env` y configura:
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
   - `TELEGRAM_BOT_TOKEN` (si usas notificaciones)
   - `TELEGRAM_CHAT_ID`
   - `TRADING_MODE=PAPER`

## ▶️ Ejecución
### Backend
```powershell
cd BinanceAgent
.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

### Frontend
```powershell
cd BinanceAgent\frontend
npm run dev
```

## 📁 Estructura clave
- `backend/main.py`: entrada del servidor FastAPI.
- `backend/bot_logic.py`: lógica central del trading.
- `backend/telegram_notifier.py`: alertas por Telegram.
- `frontend/`: aplicación de usuario.

## 🧪 Validación
- Comprueba que el backend arranca en `http://127.0.0.1:8000`.
- Comprueba que el frontend arranca en `http://localhost:5173`.

## ⚠️ Notas importantes
- Nunca subas tus claves a Git.
- Usa `PAPER` para pruebas antes de operar con dinero real.
- Si cambias variables en `.env`, reinicia el backend.

## 📚 Recursos
- `backend/requirements.txt`
- `frontend/package.json`
- `CHANGELOG.md`
- `GUIA_GIT.md`

## 📄 Licencia
Este proyecto está bajo licencia MIT.
