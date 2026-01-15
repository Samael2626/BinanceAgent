from strategies.rsi_rebound import RSIReboundStrategy
import sys
import os

# Ensure backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def run_test():
    print("🧪 Iniciando Simulación de RSI Glide (Surf)...")
    strategy = RSIReboundStrategy()

    # Settings (RSI limit 70, Trailing deviation 0.8%)
    settings = {
        "sell_rsi": 70,
        "rsi_trailing_pct": 0.8,
        "stop_loss_pct": 3.0,
        "enable_atr_tp": False,
        "take_profit_pct": 10.0  # High so it doesnt interfere
    }

    # Base State
    state = {
        "entry_price": 100.0,
        "accumulated_qty": 1.0,
        "highest_price": 0.0
    }

    # CASE 1: Normal Holding (RSI Low, Price Stable)
    indicators = {"rsi": 50, "atr": 1.0}
    state["current_price"] = 101.0
    state["highest_price"] = 101.0
    print(f"\n🔹 Caso 1: Normal (RSI 50 < 70)")
    should_sell = strategy.check_sell_signal(indicators, settings, state)
    print(
        f"   Resultado: {'VENDER' if should_sell else 'HOLD'} (Esperado: HOLD)")

    # CASE 2: Pump Started (RSI High, but Price is at High) -> SHOULD GLIDE
    indicators = {"rsi": 85}  # WAY overbought
    state["current_price"] = 105.0
    state["highest_price"] = 105.0  # We are at the top
    print(f"\n🔹 Caso 2: PUMP Detectado (RSI 85 > 70, Precio en Máximo)")
    should_sell = strategy.check_sell_signal(indicators, settings, state)
    print(
        f"   Resultado: {'VENDER' if should_sell else 'GLIDE/HOLD'} (Esperado: GLIDE/HOLD)")

    # CASE 3: Small Dip (RSI High, Price drops 0.5%) -> SHOULD HOLD (Tolerance is 0.8%)
    state["current_price"] = 104.5  # Drop from 105
    print(f"\n🔹 Caso 3: Pequeña Corrección (RSI 85, Bajó 0.5%)")
    should_sell = strategy.check_sell_signal(indicators, settings, state)
    print(
        f"   Resultado: {'VENDER' if should_sell else 'GLIDE/HOLD'} (Esperado: GLIDE/HOLD)")

    # CASE 4: Crash (RSI High, Price drops 1.0%) -> SHOULD SELL
    state["current_price"] = 103.9  # Drop > 0.8% from 105
    print(f"\n🔹 Caso 4: Caída Confirmada (RSI 85, Bajó > 0.8%)")
    should_sell = strategy.check_sell_signal(indicators, settings, state)
    print(
        f"   Resultado: {'VENDER' if should_sell else 'GLIDE/HOLD'} (Esperado: VENDER)")


if __name__ == "__main__":
    run_test()
