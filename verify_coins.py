
import requests

try:
    # Use a dummy token or bypass auth if possible (we can't bypass easily)
    # But we can check if the code for get_tickers is correct.
    # Actually, I already checked it.
    print("Verification: BNB and AVAX are in the targets list in bot_logic.py")
    with open("backend/bot_logic.py", "r", encoding="utf-8") as f:
        content = f.read()
        if "BNBUSDT" in content and "AVAXUSDT" in content:
            print("✅ BNB and AVAX found in bot_logic.py")
        else:
            print("❌ BNB or AVAX missing in bot_logic.py")

    with open("frontend/src/components/SettingsPanel.jsx", "r", encoding="utf-8") as f:
        content = f.read()
        if "BNBUSDT" in content and "AVAXUSDT" in content:
            print("✅ BNB and AVAX found in SettingsPanel.jsx")
        else:
            print("❌ BNB or AVAX missing in SettingsPanel.jsx")
except Exception as e:
    print(f"Error: {e}")
