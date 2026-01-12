"""
Script para probar envío de notificaciones de Telegram
"""
from backend.telegram_notifier import TelegramNotifier
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


def test_telegram():
    print("🧪 Testing Telegram Notifications...")

    TOKEN = "8450780054:AAGaupsdedMyfNCX90fzpqDcCNKuTbTOLhA"
    CHAT_ID = "8074460988"

    notifier = TelegramNotifier(TOKEN, CHAT_ID, enabled=True)

    print(f"Token: {TOKEN[:20]}...")
    print(f"Chat ID: {CHAT_ID}")
    print(f"Enabled: True")

    # Enviar mensaje de prueba
    msg = "🧪 *TEST MESSAGE*\nSi recibes esto, Telegram está funcionando correctamente.\nBot de trading activo."

    print("\n📤 Enviando mensaje de prueba...")
    success = notifier.send_message(msg)

    if success:
        print("✅ Mensaje enviado exitosamente")
    else:
        print("❌ Error al enviar mensaje")
        print("Revisa:")
        print("1. El token del bot es correcto")
        print("2. El chat_id es correcto")
        print("3. Has iniciado una conversación con el bot en Telegram")
        print("4. El bot no está bloqueado")


if __name__ == "__main__":
    test_telegram()
