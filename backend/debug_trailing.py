"""
Script para diagnosticar por qué el trailing stop no vende
"""
import sys


class TrailingDiagnostic:
    def __init__(self):
        self.example_scenarios = []

    def test_scenario(self, name, entry_price, highest_price, current_price, rsi, trail_pct=0.8):
        """Simula la lógica del trailing stop"""
        print(f"\n{'='*60}")
        print(f"ESCENARIO: {name}")
        print(f"{'='*60}")

        # Valores
        print(f"\n📊 Datos:")
        print(f"  Entry Price:    ${entry_price:.2f}")
        print(f"  Highest Price:  ${highest_price:.2f}")
        print(f"  Current Price:  ${current_price:.2f}")
        print(f"  RSI:            {rsi:.1f}")
        print(f"  Trail %:        {trail_pct}%")

        # Cálculos
        profit_step_reached = (highest_price > entry_price)
        trail_price = highest_price * (1 - trail_pct / 100)
        should_sell = current_price < trail_price

        profit_pct = ((current_price / entry_price) - 1) * \
            100 if entry_price > 0 else 0
        drop_from_high = ((current_price / highest_price) -
                          1) * 100 if highest_price > 0 else 0

        print(f"\n🧮 Cálculos:")
        print(f"  Profit actual:        {profit_pct:+.2f}%")
        print(f"  Caída desde máximo:   {drop_from_high:.2f}%")
        print(f"  Trail Price:          ${trail_price:.2f}")
        print(f"  Profit Step Reached:  {profit_step_reached}")

        print(f"\n🎯 Decisión:")
        if not profit_step_reached:
            print(
                f"  ❌ TRAILING INACTIVO - highest_price ({highest_price:.2f}) NO > entry ({entry_price:.2f})")
            print(f"  → No se puede vender con trailing porque nunca superó el entry")
        elif should_sell:
            print(f"  ✅ VENDER AHORA")
            print(
                f"  → Precio actual (${current_price:.2f}) < Trail (${trail_price:.2f})")
        else:
            distance_to_trail = ((current_price / trail_price) - 1) * 100
            print(f"  🟡 MANTENER (Trailing activo)")
            print(
                f"  → Precio actual (${current_price:.2f}) > Trail (${trail_price:.2f})")
            print(f"  → Distancia al trail: +{distance_to_trail:.2f}%")
            print(
                f"  → Necesita caer {distance_to_trail:.2f}% más para vender")


def main():
    diag = TrailingDiagnostic()

    print("\n🔍 DIAGNÓSTICO DE TRAILING STOP")
    print("="*60)

    # Escenario 1: Caso normal - debería vender
    diag.test_scenario(
        "Trailing debe vender",
        entry_price=930.00,
        highest_price=940.00,  # Subió +1.08%
        current_price=932.00,  # Cayó desde el máximo
        rsi=45.0,
        trail_pct=0.8
    )

    # Escenario 2: Trailing muy pequeño - no vende
    diag.test_scenario(
        "Caída insuficiente para trail 0.8%",
        entry_price=930.00,
        highest_price=940.00,
        current_price=938.00,  # Solo cayó 0.21% desde máximo
        rsi=45.0,
        trail_pct=0.8
    )

    # Escenario 3: Highest_price no actualizado
    diag.test_scenario(
        "Highest_price desactualizado",
        entry_price=930.00,
        highest_price=930.00,  # ❌ No se actualizó!
        current_price=925.00,  # Ahora está cayendo
        rsi=45.0,
        trail_pct=0.8
    )

    # Escenario 4: Trail más agresivo (0.5%)
    diag.test_scenario(
        "Trail 0.5% (más sensible)",
        entry_price=930.00,
        highest_price=940.00,
        current_price=938.00,
        rsi=45.0,
        trail_pct=0.5  # Más agresivo
    )

    # Escenario 5: Caso real del usuario
    print("\n" + "="*60)
    print("📸 ESCENARIO REAL (según screenshot)")
    print("="*60)

    diag.test_scenario(
        "Tu caso (BNB a $931.72)",
        entry_price=931.72,
        highest_price=937.11,  # Precio actual visible
        current_price=937.11,
        rsi=36.0,
        trail_pct=0.8
    )

    print("\n" + "="*60)
    print("📝 RECOMENDACIONES:")
    print("="*60)
    print("""
1. Si el trail NO vende cuando debería:
   → Verificar que 'highest_price' se actualice correctamente
   → Revisar logs de consola para ver mensajes de trailing
   
2. Si vende demasiado rápido:
   → Aumentar 'rsi_trailing_pct' (ej: 1.0%, 1.5%)
   
3. Si vende muy tarde:
   → Reducir 'rsi_trailing_pct' (ej: 0.5%, 0.3%)
   
4. Trail óptimo recomendado:
   → Volatilidad alta (BTC, BNB): 0.8% - 1.2%
   → Volatilidad media (ETH): 0.5% - 0.8%
   → Scalping: 0.3% - 0.5%
    """)


if __name__ == "__main__":
    main()
