from strategies.rsi_rebound import RSIReboundStrategy
import sys
import os

# Ensure we can import from strategies
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


def test_profit_step_logic():
    print("🧪 INICIANDO TEST DE LÓGICA DE PASOS (STEPS) 🧪\n")

    strategy = RSIReboundStrategy()

    # 1. ESCENARIO: Subida sin tocar RSI de venta (62.5)
    # Entrada en 100, Máximo en 105 (Ganancia 5%)
    # Trail %: 1.0
    # RSI: 55 (No debería disparar por Glide estándar)

    settings = {
        'sell_rsi': 62.5,
        'rsi_trailing_pct': 1.0,
        'stop_loss_pct': 3.2,
        'take_profit_pct': 0.0,  # TP deshabilitado como tiene el usuario
        'trailing_enabled': False  # Trail manual apagado
    }

    indicators = {'rsi': 55.0}  # BAJO el umbral de 62.5

    # Simulación de subida
    state_ascending = {
        'entry_price': 100.0,
        'current_price': 104.5,
        'highest_price': 105.0,
        'accumulated_qty': 1.0
    }

    print("--- CASO 1: Subiendo (Precio 104.5, Pico 105.0, RSI 55) ---")
    print("Esperado: Ver mensaje '🧗 STEPS' y NO vender (Holding)")
    # check_standard_exits should return False (holding) but print the STEPS log
    is_exit_1 = strategy.check_standard_exits(
        indicators, settings, state_ascending)
    print(f"Resultado Venta: {is_exit_1}")

    print("\n--- CASO 2: Caída desde el pico (Precio 103.5, Pico 105.0) ---")
    # 105 * (1 - 0.01) = 103.95. Precio 103.5 es MENOR que 103.95 -> Debe vender.
    state_dropping = {
        'entry_price': 100.0,
        'current_price': 103.5,
        'highest_price': 105.0,
        'accumulated_qty': 1.0
    }
    print("Esperado: VENDER por 'Profit Step Trail'")
    is_exit_2 = strategy.check_standard_exits(
        indicators, settings, state_dropping)
    print(f"Resultado Venta: {is_exit_2}")

    if not is_exit_1 and is_exit_2:
        print("\n✅ PRUEBA EXITOSA: La lógica de Pasos protege la ganancia sin el RSI.")
    else:
        print("\n❌ PRUEBA FALLIDA: Revisar lógica en base_strategy.py")


if __name__ == "__main__":
    test_profit_step_logic()
