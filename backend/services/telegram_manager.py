import asyncio
import logging
import threading
import traceback
from typing import Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from ..database import DatabaseManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramManager:
    def __init__(self, token: str, bot_manager=None):
        self.token = token
        self.bot_manager = bot_manager
        self.db = DatabaseManager()
        self.app = None
        self.loop = None
        self.thread = None
        self._stop_event = threading.Event()

    def _get_active_bot(self):
        """Busca el primer bot activo en el BotManager"""
        if not self.bot_manager:
            return None

        # Primero intentamos con ID 1 (habitual)
        bot = self.bot_manager.get_bot(1)
        if bot:
            return bot

        # Si no, buscamos cualquier bot en el diccionario
        with self.bot_manager.lock:
            if self.bot_manager.bots:
                # Tomamos el primero disponible
                return next(iter(self.bot_manager.bots.values()))
        return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mando /start - Panel Principal"""
        text = (
            "🤖 *Binance Agent Pro – Control Center*\n\n"
            "_Bienvenido al panel de control profesional._\n"
            "Selecciona una opción del menú:"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "📊 RSI Monitor", callback_data="rsi_menu"),
                InlineKeyboardButton(
                    "📈 Tendencia RT", callback_data="trend_rt"),
            ],
            [
                InlineKeyboardButton(
                    "⚡ Operaciones", callback_data="operations"),
                InlineKeyboardButton(
                    "💼 Mi Portafolio", callback_data="portfolio"),
            ],
            [
                InlineKeyboardButton(
                    "🧠 Estrategias", callback_data="active_strategies"),
                InlineKeyboardButton(
                    "⚙️ Alertas", callback_data="alerts_config"),
            ],
            [
                InlineKeyboardButton("🖼 Gráficos", callback_data="graph_menu"),
                InlineKeyboardButton("❓ Ayuda", callback_data="help_menu"),
            ],
            [
                InlineKeyboardButton("⏸ Pausar", callback_data="pause_bot"),
                InlineKeyboardButton(
                    "▶️ Reanudar", callback_data="resume_bot"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja clics en botones"""
        query = update.callback_query
        try:
            try:
                await query.answer()
            except Exception:
                pass

            # Buscamos bot activo dinámicamente
            bot = self._get_active_bot()

            if query.data == "rsi_menu":
                await self.show_rsi_menu(query)
            elif query.data.startswith("rsi_detail_"):
                symbol = query.data.replace("rsi_detail_", "")
                await self.show_coin_detail(query, bot, symbol)
            elif query.data == "back_to_main":
                await self.start(update, context)
            elif query.data == "rsi_monitor":
                await self.show_rsi_snapshot(query, bot)
            elif query.data == "trend_rt":
                await self.show_trend_rt(query, bot)
            elif query.data == "alerts_config":
                await self.show_alerts_config(query)
            elif query.data == "operations":
                await self.show_operations_menu(query)
            elif query.data == "graph_menu":
                await self.show_graph_menu(query)
            elif query.data.startswith("graph_"):
                symbol = query.data.replace("graph_", "")
                await self.show_graph_detail(query, bot, symbol)
            elif query.data == "help_menu" or query.data == "commands_list":
                await self.show_commands(query)
            elif query.data == "portfolio":
                await self.show_portfolio(query, bot)
            elif query.data == "pause_bot":
                if bot:
                    bot.stop()
                    await query.edit_message_text("🛑 *Bot Detenido*", parse_mode="Markdown")
                    await asyncio.sleep(2)
                    await self.start(update, context)
            elif query.data == "resume_bot":
                if bot:
                    bot.start()
                    await query.edit_message_text("🚀 *Bot Reanudado*", parse_mode="Markdown")
                    await asyncio.sleep(2)
                    await self.start(update, context)
            elif query.data == "active_strategies":
                await self.show_strategy(query, bot)
            elif query.data == "op_buy":
                await self.show_quick_buy_panel(update, context, query)
            elif query.data == "op_sell":
                await self.show_quick_sell_panel(update, context, query)
            elif query.data.startswith("buy_amt_adj_"):
                diff = float(query.data.replace("buy_amt_adj_", ""))
                amt = context.user_data.get("buy_amt", 20.0) + diff
                context.user_data["buy_amt"] = max(10.0, amt)  # Min 10 USDT
                await self.show_quick_buy_panel(update, context, query)
            elif query.data == "buy_amt_max":
                if bot:
                    context.user_data["buy_amt"] = bot.balance * \
                        0.98  # 98% for safety
                    await self.show_quick_buy_panel(update, context, query)
            elif query.data == "buy_amt_confirm":
                amt = context.user_data.get("buy_amt", 20.0)
                if bot:
                    logger.info(f"Executing manual buy: {amt} USDT")
                    res = bot.manual_buy(custom_qty=amt, is_quote=True)
                    logger.info(f"Manual buy response: {res}")
                    await query.edit_message_text(f"{'✅' if res['status'] == 'success' else '❌'} {res['message']}")
                    await asyncio.sleep(2)
                    await self.start(update, context)
            elif query.data.startswith("sell_pct_"):
                pct_str = query.data.replace("sell_pct_", "")
                if pct_str == "confirm":
                    pct = context.user_data.get("sell_pct", 100)
                    if bot:
                        qty = bot.crypto_balance * (pct / 100)
                        logger.info(
                            f"Executing manual sell: {qty} units ({pct}%)")
                        res = bot.manual_sell(custom_qty=qty)
                        logger.info(f"Manual sell response: {res}")
                        await query.edit_message_text(f"{'✅' if res['status'] == 'success' else '❌'} {res['message']}")
                        await asyncio.sleep(2)
                        await self.start(update, context)
                else:
                    context.user_data["sell_pct"] = int(pct_str)
                    await self.show_quick_sell_panel(update, context, query)
            elif query.data == "help_menu" or query.data == "commands_list":
                await self.show_commands(query)
            else:
                logger.warning(f"Callback data no manejada: {query.data}")

        except Exception as e:
            logger.error(f"Error en button_handler: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                await query.edit_message_text(f"❌ Error interno: {str(e)}")
            except Exception:
                pass

    async def show_rsi_menu(self, query):
        """Muestra menú de monedas para RSI"""
        from ..rsi_snapshot import get_default_symbols
        symbols = get_default_symbols()

        keyboard = []
        row = []
        for sym in symbols:
            clean_name = sym.replace("USDT", "")
            row.append(InlineKeyboardButton(
                clean_name, callback_data=f"rsi_detail_{sym}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Opción RSI Global
        keyboard.append([InlineKeyboardButton(
            "🌏 RSI Global", callback_data="rsi_monitor")])
        keyboard.append([InlineKeyboardButton(
            "🔙 Volver", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📡 *Monitoreo Automático*\n\n_Selecciona la moneda para ver detalles en tiempo real._",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def show_coin_detail(self, query, bot, symbol):
        """Muestra detalle profesional de una moneda"""
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        from ..rsi_snapshot import calculate_rsi
        client = bot.data_client if hasattr(
            bot, 'data_client') and bot.data_client else bot.client

        try:
            df = client.get_historical_klines(symbol, bot.timeframe, limit=100)
            rsi = calculate_rsi(df)
            price = float(client.client.get_symbol_ticker(
                symbol=symbol)['price'])

            zone = "Neutral"
            emoji = "⚪"
            if rsi < 35:
                zone, emoji = "Sobreventa", "🟢"
            elif rsi > 65:
                zone, emoji = "Sobrecompra", "🔴"

            trend = "Lateral"
            if rsi > 55:
                trend = "Alcista"
            elif rsi < 45:
                trend = "Bajista"

            text = (
                f"📊 *RSI ACTUAL – {symbol}* ({bot.timeframe})\n\n"
                f"*Precio:* ${price:,.2f} USDT\n"
                f"*RSI:* {rsi:.1f}\n"
                f"Zona: {emoji} {zone}\n"
                f"Tendencia: {trend}\n"
                f"Velocidad: +0.0\n\n"
                f"⏱ _Última actualización: hace 0 segundos_"
            )

            keyboard = [[InlineKeyboardButton(
                "🔙 Volver al Menú", callback_data="rsi_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"❌ Error obteniendo datos para {symbol}: {e}")

    async def show_rsi_snapshot(self, query, bot):
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        from ..rsi_snapshot import calculate_rsi_snapshot, get_default_symbols
        symbols = get_default_symbols()
        client = bot.data_client if hasattr(
            bot, 'data_client') and bot.data_client else bot.client
        snapshot = calculate_rsi_snapshot(
            symbols, client, timeframe=bot.timeframe)

        text = "📊 *MONITOREO AUTOMÁTICO - RSI*\n\n"
        for item in snapshot:
            symbol = item['symbol']
            rsi = item['rsi']
            zone = "Neutral"
            emoji = "⚪"
            if rsi < 35:
                zone, emoji = "SOBREVENTA", "🟢"
            elif rsi > 65:
                zone, emoji = "SOBRECOMPRA", "🔴"

            text += f"📈 *{symbol}*\n"
            text += f"💰 RSI (15m): {rsi:.1f}\n"
            text += f"Zona: {emoji} {zone}\n"
            text += f"⏱ Hace 0 segundos\n\n"

        await query.edit_message_text(text, parse_mode="Markdown")

    async def show_portfolio(self, query, bot):
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        try:
            # Obtener balances de Binance
            account = bot.client.client.get_account()
            balances = account.get('balances', [])

            text = "💰 *ESTADO DEL PORTAFOLIO*\n\n"
            total_usdt = 0
            found_assets = []

            for balance in balances:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked

                if total > 0:
                    asset = balance['asset']
                    if asset == 'USDT':
                        total_usdt += total
                        found_assets.append(f"💵 *USDT:* {total:,.2f}")
                    else:
                        # Intentar obtener precio en USDT
                        try:
                            if asset.startswith('LD'):  # Binance Earn
                                clean_asset = asset[2:]
                                ticker = bot.client.client.get_symbol_ticker(
                                    symbol=f"{clean_asset}USDT")
                            else:
                                ticker = bot.client.client.get_symbol_ticker(
                                    symbol=f"{asset}USDT")

                            price = float(ticker['price'])
                            value_usdt = total * price
                            total_usdt += value_usdt
                            found_assets.append(
                                f"🔸 *{asset}:* {total:.6f} (~{value_usdt:,.2f} $)")
                        except:
                            found_assets.append(f"🔸 *{asset}:* {total:.6f}")

            if not found_assets:
                text += "No se encontraron activos con balance positivo."
            else:
                text += "\n".join(found_assets)
                text += f"\n\nTotal Estimado: *{total_usdt:,.2f} USDT*"

            keyboard = [[InlineKeyboardButton(
                "🔙 Volver", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"❌ Error al obtener portafolio: {str(e)}")

    async def show_operations_menu(self, query):
        text = (
            "⚡ *PANEL DE OPERACIONES*\n\n"
            "Selecciona una acción rápida o usa los comandos manuales."
        )
        keyboard = [
            [
                InlineKeyboardButton("🟢 COMPRAR (Market)",
                                     callback_data="op_buy"),
                InlineKeyboardButton("🔴 VENDER (Market)",
                                     callback_data="op_sell"),
            ],
            [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def show_trend_rt(self, query, bot):
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        from ..rsi_snapshot import get_default_symbols, calculate_rsi
        symbols = get_default_symbols()[:5]  # Top 5
        client = bot.data_client if hasattr(
            bot, 'data_client') and bot.data_client else bot.client

        text = "📈 *TENDENCIA EN TIEMPO REAL*\n\n"

        bullish = 0
        bearish = 0

        for sym in symbols:
            try:
                df = client.get_historical_klines(sym, "15m", limit=50)
                rsi = calculate_rsi(df)
                price = float(client.client.get_symbol_ticker(
                    symbol=sym)['price'])

                status = "Neutral ⚪"
                if rsi > 55:
                    status = "Alcista 🟢"
                    bullish += 1
                elif rsi < 45:
                    status = "Bajista 🔴"
                    bearish += 1

                text += f"*{sym}:* ${price:,.2f} | {status}\n"
            except:
                continue

        sentiment = "NEUTRAL"
        if bullish > bearish:
            sentiment = "ALCISTA 🚀"
        elif bearish > bullish:
            sentiment = "BAJISTA ⚠️"

        text += f"\nSentimiento Global: *{sentiment}*"

        keyboard = [[InlineKeyboardButton(
            "🔙 Volver", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def show_alerts_config(self, query):
        text = (
            "⚙️ *CONFIGURACIÓN DE ALERTAS*\n\n"
            "🔔 *Alertas Activas:* Ninguna\n\n"
            "_Próximamente podrá configurar alertas de RSI y Precio directamente desde aquí._"
        )
        keyboard = [[InlineKeyboardButton(
            "🔙 Volver", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def show_graph_menu(self, query):
        from ..rsi_snapshot import get_default_symbols
        symbols = get_default_symbols()

        text = (
            "🖼 *ANÁLISIS GRÁFICO*\n\n"
            "Selecciona una moneda para ver el enlace al gráfico o usa `/graph <par>`.\n"
        )

        keyboard = []
        row = []
        for sym in symbols:
            clean_name = sym.replace("USDT", "")
            row.append(InlineKeyboardButton(
                clean_name, callback_data=f"graph_{sym}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(
            "🔙 Volver", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def show_graph_detail(self, query, bot, symbol):
        """Genera y envía el gráfico de una moneda específica"""
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        await query.edit_message_text(f"⏳ Generando gráfico para {symbol}...")

        try:
            from ..utils.chart_generator import generate_chart
            client = bot.data_client if hasattr(
                bot, 'data_client') and bot.data_client else bot.client
            klines = client.client.get_historical_klines(
                symbol, bot.timeframe, limit=100)

            chart_buf = generate_chart(symbol, klines)

            if chart_buf:
                await query.message.reply_photo(
                    photo=chart_buf,
                    caption=f"📈 *Gráfico: {symbol}* ({bot.timeframe})",
                    parse_mode="Markdown"
                )
                # Volvemos al menú de gráficos después de enviar la foto
                await self.show_graph_menu(query)
            else:
                await query.edit_message_text(f"❌ No se pudo generar el gráfico para {symbol}.")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_commands_msg(update)

    async def show_commands_msg(self, update):
        text = (
            "🛠 *AYUDA Y COMANDOS*\n\n"
            "/start - Panel principal\n"
            "/rsi <coin> - Ver RSI actual\n"
            "/buy <monto> - Comprar USDT\n"
            "/sell <cantidad> - Vender activo\n"
            "/wallet - Ver balance detallado\n"
            "/graph <par> - Ver gráfico rápido\n"
            "/pause - Pausar trading\n"
            "/resume - Reanudar trading\n"
            "/help - Esta ayuda\n\n"
            "💡 _Tip: Puedes escribir solo la moneda, ej: /rsi SOL_"
        )
        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown")

    async def show_commands(self, query):
        # Adaptador rápido
        await self.show_commands_msg(update=Update(0, callback_query=query))

    async def show_strategy(self, query, bot):
        if not bot:
            await query.edit_message_text("❌ Bot no inicializado")
            return

        settings = bot.get_settings()
        text = (
            "🧠 *ESTRATEGIA ACTIVA*\n\n"
            f"Modo: {settings.get('active_strategy')}\n"
            f"RSI Compra: {settings.get('buy_rsi')}\n"
            f"RSI Venta: {settings.get('sell_rsi')}\n"
            f"DCA: {settings.get('max_dca_orders')}\n"
            f"SL: {settings.get('stop_loss_pct')}%\n"
            f"TP: {settings.get('take_profit_pct')}%\n"
            f"Timeframe: {settings.get('timeframe')}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /buy <qty>"""
        bot = self._get_active_bot()
        if not bot:
            await update.message.reply_text("❌ Bot no activo")
            return

        args = context.args
        if not args:
            await self.show_quick_buy_panel(update, context)
            return

        try:
            qty = float(args[0])
            # En telegram asumimos USDT por defecto
            res = bot.manual_buy(custom_qty=qty, is_quote=True)
            await update.message.reply_text(f"{'✅' if res['status'] == 'success' else '❌'} {res['message']}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def show_quick_buy_panel(self, update, context, query=None):
        bot = self._get_active_bot()
        if not bot:
            return

        amt = context.user_data.get("buy_amt", 20.0)
        text = (
            f"🛒 *COMPRA MANUAL – {bot.symbol}*\n\n"
            f"💰 *Saldo:* {bot.balance:,.2f} USDT\n"
            f"💵 *Monto a comprar:* `{amt:,.1f} USDT`\n\n"
            f"_Ajusta el monto con los botones o confirma para ejecutar._"
        )
        keyboard = [
            [
                InlineKeyboardButton("-20", callback_data="buy_amt_adj_-20"),
                InlineKeyboardButton("-5", callback_data="buy_amt_adj_-5"),
                InlineKeyboardButton("+5", callback_data="buy_amt_adj_5"),
                InlineKeyboardButton("+20", callback_data="buy_amt_adj_20"),
            ],
            [InlineKeyboardButton("💰 COMPRAR TODO (MAX)",
                                  callback_data="buy_amt_max")],
            [
                InlineKeyboardButton("✅ CONFIRMAR COMPRA",
                                     callback_data="buy_amt_confirm"),
                InlineKeyboardButton(
                    "❌ CANCELAR", callback_data="back_to_main"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /sell <qty>"""
        bot = self._get_active_bot()
        if not bot:
            await update.message.reply_text("❌ Bot no activo")
            return

        args = context.args
        if not args:
            await self.show_quick_sell_panel(update, context)
            return

        qty = float(args[0]) if args else None
        try:
            res = bot.manual_sell(custom_qty=qty)
            await update.message.reply_text(f"{'✅' if res['status'] == 'success' else '❌'} {res['message']}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def show_quick_sell_panel(self, update, context, query=None):
        bot = self._get_active_bot()
        if not bot:
            return

        pct = context.user_data.get("sell_pct", 100)
        asset = bot.symbol.replace("USDT", "")
        qty_to_sell = bot.crypto_balance * (pct / 100)
        value_usd = qty_to_sell * bot.current_price

        text = (
            f"💰 *VENTA MANUAL – {bot.symbol}*\n\n"
            f"📦 *Balance:* {bot.crypto_balance:,.6f} {asset}\n"
            f"🔴 *Vender:* `{qty_to_sell:,.6f} {asset}`\n"
            f"💵 *Valor est.:* `${value_usd:,.2f} USDT`\n\n"
            f"_Selecciona el porcentaje o confirma la venta._"
        )
        keyboard = [
            [
                InlineKeyboardButton("25%", callback_data="sell_pct_25"),
                InlineKeyboardButton("50%", callback_data="sell_pct_50"),
                InlineKeyboardButton("75%", callback_data="sell_pct_75"),
                InlineKeyboardButton("100%", callback_data="sell_pct_100"),
            ],
            [InlineKeyboardButton(
                "🔴 VENDER TODO", callback_data="sell_pct_100")],
            [
                InlineKeyboardButton("✅ CONFIRMAR VENTA",
                                     callback_data="sell_pct_confirm"),
                InlineKeyboardButton(
                    "❌ CANCELAR", callback_data="back_to_main"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    async def graph_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /graph <symbol>"""
        bot = self._get_active_bot()
        if not bot:
            await update.message.reply_text("❌ Bot no activo")
            return

        args = context.args
        if not args:
            await update.message.reply_text("Uso: /graph <par> (ej: /graph BTCUSDT)")
            return

        symbol = args[0].upper()
        if not symbol.endswith("USDT") and "USD" not in symbol:
            symbol += "USDT"

        msg = await update.message.reply_text(f"⏳ Generando gráfico para {symbol}...")

        try:
            from ..utils.chart_generator import generate_chart
            client = bot.data_client if hasattr(
                bot, 'data_client') and bot.data_client else bot.client
            klines = client.client.get_historical_klines(
                symbol, bot.timeframe, limit=100)

            chart_buf = generate_chart(symbol, klines)

            if chart_buf:
                await update.message.reply_photo(
                    photo=chart_buf,
                    caption=f"📈 *Gráfico: {symbol}* ({bot.timeframe})",
                    parse_mode="Markdown"
                )
                await msg.delete()
            else:
                await msg.edit_text(f"❌ No se pudo generar el gráfico para {symbol}.")
        except Exception as e:
            await msg.edit_text(f"❌ Error: {str(e)}")

    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /wallet"""
        bot = self._get_active_bot()
        if not bot:
            await update.message.reply_text("❌ Bot no activo")
            return

        text = await self._get_portfolio_text(bot)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _get_portfolio_text(self, bot):
        try:
            account = bot.client.client.get_account()
            balances = account.get('balances', [])
            text = "💰 *ESTADO DEL PORTAFOLIO*\n\n"
            total_usdt = 0
            for b in balances:
                free = float(b['free'])
                locked = float(b['locked'])
                total = free + locked
                if total > 0.000001:
                    asset = b['asset']
                    try:
                        price = 1.0 if asset == 'USDT' else float(
                            bot.client.client.get_symbol_ticker(symbol=f"{asset}USDT")['price'])
                        val = total * price
                        total_usdt += val
                        text += f"🔸 *{asset}:* {total:.6f} (~{val:,.2f} $)\n"
                    except:
                        text += f"🔸 *{asset}:* {total:.6f}\n"
            text += f"\nTotal: *{total_usdt:,.2f} USDT*"
            return text
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def stop(self):
        self._stop_event.set()
        if self.app:
            # self.app.stop() # Esto es asíncrono, mejor dejar que el hilo muera
            pass

    async def rsi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /rsi profesional"""
        args = context.args
        bot = self._get_active_bot()

        if not args:
            # Si no hay argumentos, mostrar el menú de monedas
            from ..rsi_snapshot import get_default_symbols
            symbols = get_default_symbols()
            keyboard = []
            row = []
            for sym in symbols:
                clean_name = sym.replace("USDT", "")
                row.append(InlineKeyboardButton(
                    clean_name, callback_data=f"rsi_detail_{sym}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📡 *Panel RSI - Selecciona una moneda:*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        # Si hay argumento (ej: /rsi SOL), mostrar detalle directo
        symbol = args[0].upper()
        if not symbol.endswith("USDT") and "USD" not in symbol:
            symbol += "USDT"

        await self.show_coin_detail_direct(update, bot, symbol)

    async def show_coin_detail_direct(self, update, bot, symbol):
        """Versión para mensajes directos sin modo edición callback"""
        if not bot or not bot.client:
            await update.message.reply_text("❌ Bot no inicializado")
            return

        from ..rsi_snapshot import calculate_rsi
        client = bot.data_client if hasattr(
            bot, 'data_client') and bot.data_client else bot.client

        try:
            df = client.get_historical_klines(symbol, bot.timeframe, limit=100)
            rsi = calculate_rsi(df)
            price = float(client.client.get_symbol_ticker(
                symbol=symbol)['price'])

            text = (
                f"📊 *RSI ACTUAL – {symbol}* ({bot.timeframe})\n\n"
                f"*Precio:* ${price:,.2f} USDT\n"
                f"*RSI:* {rsi:.1f}\n"
                f"Zona: ⚪ Neutral\n"
                f"Tendencia: Lateral\n\n"
                f"⏱ _Última actualización: hace 0 segundos_"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(f"❌ Moneda {symbol} no encontrada o error de datos.")

    def run(self):
        """Inicia el bot en un hilo separado o loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("rsi", self.rsi_command))
        self.app.add_handler(CommandHandler("buy", self.buy_command))
        self.app.add_handler(CommandHandler("sell", self.sell_command))
        self.app.add_handler(CommandHandler("graph", self.graph_command))
        self.app.add_handler(CommandHandler("grafh", self.graph_command))
        self.app.add_handler(CommandHandler("grafico", self.graph_command))
        self.app.add_handler(CommandHandler("wallet", self.wallet_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        logger.info("🚀 Telegram Manager iniciado e hilos listos.")
        self.app.run_polling()

    def start_in_thread(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
