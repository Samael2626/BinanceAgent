"""
Script de diagnóstico y prueba de Telegram
Verifica que el chat_id se guarde correctamente y envía un mensaje de prueba
"""
from backend.telegram_notifier import TelegramNotifier
from backend.database import DatabaseManager
import sys
import os
import logging

# Configure logging immediately
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to path
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


def test_telegram_full():
    print("=" * 60)
    print("🧪 TELEGRAM DIAGNOSTIC & TEST")
    print("=" * 60)

    # Configuration
    TOKEN = "8450780054:AAGaupsdedMyfNCX90fzpqDcCNKuTbTOLhA"
    CHAT_ID = "8074460988"
    USER_ID = 1

    # Step 1: Check database
    print("\n1️⃣ Checking database...")
    db = DatabaseManager()

    # Save the chat_id
    db.save_setting("tg_chat_id", CHAT_ID, user_id=USER_ID)
    db.save_setting("telegram_enabled", "True", user_id=USER_ID)

    # Read it back
    saved_chat_id = db.get_setting("tg_chat_id", "", user_id=USER_ID)
    saved_enabled = db.get_setting(
        "telegram_enabled", "False", user_id=USER_ID)

    print(f"   Saved chat_id: {saved_chat_id}")
    print(f"   Saved enabled: {saved_enabled}")
    print(f"   ✅ Database OK" if saved_chat_id ==
          CHAT_ID else f"   ❌ Database mismatch!")

    # Step 2: Test Telegram sending
    print("\n2️⃣ Testing Telegram API...")
    notifier = TelegramNotifier(TOKEN, CHAT_ID, enabled=True)

    test_message = f"""🧪 *PRUEBA DE TELEGRAM*

✅ Bot configurado correctamente
📱 Chat ID: {CHAT_ID}
🤖 Sistema de notificaciones activo

Si recibes este mensaje, todo está funcionando perfectamente."""

    print(f"   Token: {TOKEN[:20]}...")
    print(f"   Chat ID: {CHAT_ID}")
    print(f"   Enviando mensaje de prueba...")

    success = notifier.send_message(test_message)

    if success:
        print("   ✅ Mensaje enviado exitosamente!")
        print("\n" + "=" * 60)
        print("✅ TELEGRAM FUNCIONANDO CORRECTAMENTE")
        print("=" * 60)
    else:
        print("   ❌ Error al enviar mensaje")
        print("\n🔍 TROUBLESHOOTING:")
        print("   1. Verifica que hayas iniciado chat con el bot en Telegram")
        print("   2. Busca al bot y envíale /start")
        print("   3. Asegúrate que el Chat ID sea correcto")
        print("   4. Verifica que el bot no esté bloqueado")
        print("\n📝 Para obtener tu Chat ID:")
        print("   Envía un mensaje al bot y luego visita:")
        print(f"   https://api.telegram.org/bot{TOKEN}/getUpdates")


if __name__ == "__main__":
    test_telegram_full()
