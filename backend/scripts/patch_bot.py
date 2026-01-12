
import os

path = r'c:\Users\HOME\OneDrive\Escritorio\Trabajo\Binance\backend\bot_logic.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Take Profit notification (the one inside 4b. Take Profit Management)
# We look for the "TAKE PROFIT" string first to find the block
blocks = content.split('if trade:')
new_blocks = []
for i, block in enumerate(blocks):
    if i == 0:
        new_blocks.append(block)
        continue

    # Check if this block is inside Take Profit Management
    # The previous block should contain "4b. Take Profit Management"
    if '4b. Take Profit Management' in blocks[i-1] and 'TAKE PROFIT' in blocks[i-1]:
        # This is the TP block
        if '⚠️ *STOP LOSS EJECUTADO*' in block:
            block = block.replace('⚠️ *STOP LOSS EJECUTADO*',
                                  '💰 *TAKE PROFIT EJECUTADO*')
            block = block.replace('Resultado:', 'Ganancia:')
            # Also fix the PnL calculation by moving it before entry_price reset
            # This is harder with split, let's do a regex or simple replace
            block = block.replace(
                'self.entry_price = 0.0', 'pnl_done = self.current_price - self.entry_price\n                            self.entry_price = 0.0')
            block = block.replace(
                'round(self.current_price - self.entry_price, 2)', 'round(pnl_done, 2)')

    # Check other blocks (SL, RSI, Multi)
    if '4. Risk Management' in blocks[i-1] and 'STOP LOSS' in blocks[i-1]:
        # SL block
        block = block.replace(
            'self.entry_price = 0.0', 'pnl_done = self.current_price - self.entry_price\n                            self.entry_price = 0.0')
        block = block.replace(
            'round(self.current_price - self.entry_price, 2)', 'round(pnl_done, 2)')

    if 'type": "SELL"' in blocks[i-1] and 'RSI > self.sell_rsi' in blocks[i-1]:
        # RSI Sell block
        block = block.replace(
            'self.entry_price = 0.0', 'pnl_done = self.current_price - self.entry_price\n                                self.entry_price = 0.0')
        block = block.replace('round(pnl, 2)', 'round(pnl_done, 2)')

    if 'type": "SELL (Multi)"' in blocks[i-1]:
        # Multi Sell block
        block = block.replace(
            'self.entry_price = 0.0', 'pnl_done = self.current_price - self.entry_price\n                                self.entry_price = 0.0')
        block = block.replace('round(pnl, 2)', 'round(pnl_done, 2)')
        block = block.replace('VENTA EJECUTADA (RSI)',
                              'VENTA EJECUTADA (Multi)')

    if 'type": "BUY (Multi)"' in blocks[i-1]:
        # Multi Buy block
        block = block.replace('COMPRA EJECUTADA (RSI)',
                              'COMPRA EJECUTADA (Multi)')

    new_blocks.append(block)

new_content = 'if trade:'.join(new_blocks)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("bot_logic.py patched successfully")
