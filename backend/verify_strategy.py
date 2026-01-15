import sys
import os

# Ensure backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from strategies.rsi_rebound import RSIReboundStrategy
    print("✅ Successfully imported RSIReboundStrategy")

    strategy = RSIReboundStrategy()
    print("✅ Successfully instantiated RSIReboundStrategy")
    print("Methods present:", dir(strategy))

except TypeError as e:
    print(f"❌ TypeError (Abstract Class?): {e}")
except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
