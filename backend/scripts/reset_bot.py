import requests
import sys


def reset_position():
    print("⏳ Reseteando POSICIÓN (Accumulated Qty)...")
    try:
        resp = requests.post("http://localhost:8000/api/reset")
        if resp.status_code == 200:
            print("✅ Posición borrada (el bot piensa que tiene 0 monedas).")
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")


def reset_pnl():
    print("⏳ Reseteando PnL (Historial de ganancias)...")
    try:
        resp = requests.post("http://localhost:8000/api/reset_pnl")
        if resp.status_code == 200:
            print("✅ PnL y Historial borrados (Ganancia = 0).")
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")


def main():
    print("\n⚠️  MENÚ DE RESETEO DEL BOT ⚠️")
    print("1. Resetear SOLO Posición (Si vendiste manual y quieres que el bot sepa)")
    print("2. Resetear SOLO PnL (Borrar historial de ganancias)")
    print("3. Resetear TODO (Modo Fábrica)")
    print("4. Cancelar")

    choice = input("\nElige una opción (1-4): ")

    if choice == "1":
        reset_position()
    elif choice == "2":
        reset_pnl()
    elif choice == "3":
        reset_position()
        reset_pnl()
    elif choice == "4":
        print("Operación cancelada.")
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    main()
