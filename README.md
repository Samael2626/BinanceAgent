# Binance Trading Bot [v1.8.0 Stable]

Un bot de trading autónomo para Binance desarrollado con **Python (FastAPI)** y **React (Vite)**.

## 🚀 Características
- **Backend Robusto**: FastAPI + Pandas para análisis de datos.
- **Frontend Moderno**: Interfaz React con modo oscuro.
- **Modo Simulado (Paper Trading)**: Opera sin arriesgar dinero real por defecto.
- **Conexión Segura**: Manejo de claves API mediante variables de entorno.

## 🛠️ Requisitos Previos
- Python 3.12+
- Node.js & npm

## ⚙️ Instalación

1.  **Backend**:
    ```powershell
    # Desde la carpeta raíz
    pip install -r backend/requirements.txt
    ```

2.  **Frontend**:
    ```powershell
    cd frontend
    npm install
    ```

3.  **Configuración**:
    - Ve a la carpeta `backend`.
    - Renombra el archivo `.env.example` a `.env`.
    - Abre `.env` y coloca tus claves de Binance (API KEY y SECRET).
    - *Nota*: Por defecto el `TRADING_MODE` es `PAPER` (Simulado).

## ▶️ Cómo Ejecutar

Necesitarás dos terminales abiertas al mismo tiempo.

### Terminal 1: Backend (Servidor)
Asegúrate de estar en la carpeta raíz (`Binance`):
```powershell
.venv\Scripts\python -m uvicorn backend.main:app --reload
```
*El servidor iniciará en http://127.0.0.1:8000*

### Terminal 2: Frontend (Interfaz)
Desde la carpeta `frontend`:
```powershell
cd frontend
npm run dev
```
*La web abrirá en http://localhost:5173*

## 📈 Uso del Bot
1. Abre http://localhost:5173 en tu navegador.
2. Verás el estado "connected" si el backend está corriendo.
3. Usa el botón **Start Bot** para iniciar la lógica de trading.
4. Usa **Stop Bot** para detener las operaciones.

## 📑 Documentación Detallada 💎
Para una comprensión más profunda de las funcionalidades críticas, consulta las siguientes guías:

- [🎯 Estrategia Multi-Indicador (Precisión)](file:///c:/Users/HOME/OneDrive/Escritorio/Trabajo/Binance/docs/ESTRATEGIA_PRECISION.md): Explicación técnica de la lógica RSI + MACD + EMA.
- [🛡️ Gestión de Stop Loss](file:///c:/Users/HOME/OneDrive/Escritorio/Trabajo/Binance/docs/EXPLICACION_STOP_LOSS.md): Cómo funciona la protección de capital del bot.
- [📘 Guía del Usuario](file:///c:/Users/HOME/OneDrive/Escritorio/Trabajo/Binance/docs/GUIA_USUARIO.md): Manual general de uso e instalación.

---

## 📱 Notificaciones y Alertas de Telegram
El bot incluye un sistema avanzado de notificaciones para mantenerte informado en tiempo real.

### 1. Configuración de Seguridad
- **Bot Token**: Por seguridad, el token del bot se configura únicamente en el archivo `.env` del backend (`TELEGRAM_BOT_TOKEN`). No se expone en la interfaz ni se guarda en la base de datos pública.
- **Múltiples Destinatarios**: Puedes añadir varios Chat IDs desde el panel frontal para que el bot notifique a diferentes personas o grupos simultáneamente.

### 2. Tipos de Alertas
- **Ejecuciones de Trade**: Notificaciones inmediatas de compras, ventas, Stop Loss y Take Profit.
- **Alertas de Señales**: Recibe avisos de posibles oportunidades de compra/venta basadas en tus indicadores, incluso si el bot tiene el trading automático detenido.
- **Interruptor Maestro**: Puedes activar o desactivar todas las notificaciones de Telegram con un solo clic desde el panel, sin borrar tu configuración.

## ⚙️ Configuración de Trading Segura
Hemos añadido controles para que el bot sea más preciso y se adapte a tu perfil de riesgo.

### 🕒 Intervalos de Tiempo (Velas)
Ahora puedes elegir la temporalidad de las velas que el bot analiza:
- **1 Minuto**: Operaciones muy frecuentes. Mayor riesgo por "ruido" del mercado.
- **5 o 15 Minutos**: **Recomendado para compras seguras**. Señales mucho más estables y fiables.
- **1 Hora**: Especial para detectar tendencias a largo plazo.
- **🚫 Desactivado**: Detiene la ejecución de estrategias basadas en velas, permitiendo solo el monitoreo manual o por precio.

### 🎯 Parámetros de Seguridad Sugeridos
Para una operativa segura con la estrategia **Multi-Indicador**:
- **RSI de Compra**: Entre 25 y 30.
- **RSI de Venta**: Entre 70 y 75.
- **Intervalo**: 5 minutos o superior.
- **Stop Loss**: Configurado siempre para proteger ante caídas inesperadas.
