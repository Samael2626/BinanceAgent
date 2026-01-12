
import os
path = r'c:\Users\HOME\OneDrive\Escritorio\Trabajo\Binance\backend\bot_logic.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'loop_heartbeat.txt' not in content:
    content = content.replace('print("Market Monitor Loop Started")',
                              'print("Market Monitor Loop Started"); open("loop_heartbeat.txt", "w").write(str(time.time()))')
    content = content.replace('time.sleep(3)  # Respect API limits',
                              'time.sleep(3); open("loop_heartbeat.txt", "w").write(str(time.time()))')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Heartbeat added")
