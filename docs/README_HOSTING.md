# 🚀 Guía de Despliegue en OpenBot.Host

Esta guía te ayudará a subir tu **eBot** a OpenBot.Host usando el plan "Discord Bot" (que soporta Python).

## 1. Preparación de Archivos
Debes subir el contenido de la carpeta `backend/` a tu servidor. Asegúrate de incluir:
- Todos los archivos `.py`
- El archivo `requirements.txt` (actualizado)
- El archivo `.env` (donde pondrás tus credenciales)

## 2. Configuración en el Panel (OpenBot.Host)
1. **Startup Command:** El comando para iniciar el bot suele ser:
   ```bash
   python -m backend.main
   ```
   *Nota: Si el panel te pide un archivo de inicio, selecciona `backend/main.py`.*

2. **Variables de Entorno:**
   Puedes configurar las variables directamente en el archivo `.env` o en la sección **Variables** del panel:
   - `API_KEY`: Tu API Key de Binance.
   - `API_SECRET`: Tu API Secret de Binance.
   - `TELEGRAM_BOT_TOKEN`: El token de tu bot de Telegram.
   - `TRADING_MODE`: `testnet` o `live`.

## 3. Seguridad Crítica 🛡️
> [!IMPORTANT]
> **Restricción de IP:** Una vez que el bot esté corriendo, mira la consola del servidor para ver su dirección IP (o pídela al soporte). Ve a tu panel de Binance y **restringe el acceso de tu API Key a esa IP específica**. Esto evita que si alguien hackea el hosting, no pueda retirar tus fondos.

## 4. Preguntas Frecuentes
- **¿Cómo veo si funciona?** Revisa la pestaña **Console**. Deberías ver el mensaje: `✅ Binance Client fully initialized`.
- **¿Y el Dashboard Web?** Los planes de bots suelen no permitir tráfico web entrante fácilmente. Te recomiendo manejar el bot principalmente a través de **Telegram**, que está 100% integrado y es más ligero para servidores gratuitos.

---
*Configurado por Antigravity para Binance Agent Pro v1.8.2*
