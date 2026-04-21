import asyncio
import logging
import os
import pytz
import requests
from time import sleep
from datetime import time, datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# --- 1. CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
GROUP_ID = None
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 2. BASE DE DATOS EN MEMORIA ---
blacklist = {}

# --- 3. FUNCIONES DE CÁLCULO ---
def parse_term(term: str) -> tuple[str, float]:
    term = term.strip().lower().replace(',', '')
    if not term: raise ValueError("Término vacío")
    if len(term) < 2 or term[-1] not in 'pgr':
        raise ValueError("Cada término debe terminar en p, g o r")
    clase = term[-1]
    pre = term[:-1]
    sufijo = pre[-1] if len(pre) > 0 and pre[-1] in 'km' else ''
    num_str = pre[:-1] if sufijo else pre
    num = float(num_str)
    mult = 1000 if sufijo == 'k' else 1000000 if sufijo == 'm' else 1
    return clase, num * mult

def parse_totals(expr: str) -> tuple[float, float, float]:
    p = g = r = 0.0
    for term in expr.split('+'):
        if not term.strip(): continue
        clase, val = parse_term(term)
        if clase == 'p': p += val
        elif clase == 'g': g += val
        elif clase == 'r': r += val
    return p, g, r

def format_number(num: float) -> str:
    num = abs(num)
    if num >= 1000000:
        s = f"{num/1000000:.1f}"
        return (s[:-2] if s.endswith('.0') else s) + 'm'
    if num >= 1000:
        s = f"{num/1000:.1f}"
        return (s[:-2] if s.endswith('.0') else s) + 'k'
    s = f"{num:.1f}"
    return s[:-2] if s.endswith('.0') else s

def parse_number(s: str) -> float:
    s = s.strip().lower().replace(',', '')
    suffix = s[-1] if s[-1] in 'km' else ''
    num = float(s[:-1] if suffix else s)
    mult = 1000 if suffix == 'k' else 1000000 if suffix == 'm' else 1
    return num * mult

# --- 4. RECORDATORIOS ---
async def enviar_recompensa_3am(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_ID: await context.bot.send_message(chat_id=GROUP_ID, text="🎁 <b>¡HORA DE RECOMPENSA!</b> 🎁\n\nSon las 3:00 AM. Ya puedes reclamar tu <b>Recompensa Diaria</b>. 🚀", parse_mode='HTML')

async def enviar_adivinanza_12pm(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_ID: await context.bot.send_message(chat_id=GROUP_ID, text="🎁 <b>¡Adivinanza Disponible!</b> 🎁\n\nSon las 12:00 PM. <b>Adivinanza Disponible</b>. 🚀", parse_mode='HTML')

async def enviar_misiones_8pm(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_ID: await context.bot.send_message(chat_id=GROUP_ID, text="⚔️ <b>¡MISIONES DIARIAS ACTIVAS!</b> ⚔️\n\nSon las 8:00 PM. Hora de completar las misiones 🔥", parse_mode='HTML')

async def enviar_mercado(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_ID: await context.bot.send_message(chat_id=GROUP_ID, text="🛒 <b>¡ACTUALIZACIÓN DE MERCADO!</b> 🛒\n\nEl Mercado se acaba de Actualizar. ¡Obten nuevas tropas y recursos! 🚀", parse_mode='HTML')

# --- 5. COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_ID
    if update.effective_chat.type in ('group', 'supergroup'): GROUP_ID = update.effective_chat.id
    await update.message.reply_text("⚔️ <b>Fomo Fighters Calc</b> ⚔️\n\n• <code>/cal</code> 21.2mp+2.4kg\n• <code>/camp</code> 750k", parse_mode='HTML')

async def calcular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_ID
    if update.effective_chat.type in ('group', 'supergroup'): GROUP_ID = update.effective_chat.id
    try:
        if not context.args: return
        p, g, r = parse_totals("".join(context.args))
        atk, dfn = (p*4 + g*8 + r*6), (p*8 + g*4 + r*6)
        await update.message.reply_text(f"🚀 <b>Poder ATAQUE:</b> {format_number(atk)}\n🛡️ <b>Poder DEFENSA:</b> {format_number(dfn)}", parse_mode='HTML')
    except Exception as e: await update.message.reply_text(f"❌ Error: {str(e)}")

async def camp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_ID
    if update.effective_chat.type in ('group', 'supergroup'): GROUP_ID = update.effective_chat.id
    try:
        poder = parse_number(context.args[0])
        await update.message.reply_text(f"⚔️ <b>Poder Campamentos:</b> {format_number(poder/750)}", parse_mode='HTML')
    except: pass

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != "Jinx_97": return
    if not context.args: return
    target = context.args[0].lower()
    now = datetime.now()
    if target not in blacklist:
        blacklist[target] = {'username': target, 'strikes': 1, 'fecha': now}
        await update.message.reply_text(f"⚠️ <b>STRIKE 1</b> para {target}.", parse_mode='HTML')
    else:
        blacklist[target]['strikes'] += 1
        await update.message.reply_text(f"🚫 <b>EXPULSIÓN</b> para {target}.", parse_mode='HTML')

async def bl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not blacklist: return await update.message.reply_text("✅ Lista vacía")
    mensaje = "📝 <b>LISTA DE STRIKES:</b>\n\n"
    for k, v in blacklist.items():
        mensaje += f"• {v['username']} - {v['strikes']} Strike(s)\n"
    await update.message.reply_text(mensaje, parse_mode='HTML')

async def manejador_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_ID
    if update.effective_chat.type in ('group', 'supergroup'): GROUP_ID = update.effective_chat.id
    text = update.message.text.lower() if update.message.text else ""
    if "pro" in text:
        await update.message.reply_text("FomoBot es Prosísimo, alguien sabe donde va dormir hoy?😏", reply_to_message_id=update.message.message_id)

# --- 6. DIAGNÓSTICO DE RED ---
async def test_conexion():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.telegram.org")
            logger.info(f"✅ Conexión a Telegram OK: {r.status_code}")
            return True
    except Exception as e:
        logger.error(f"❌ No se puede llegar a api.telegram.org: {e}")
        return False

# --- 7. LÓGICA PRINCIPAL ASYNC ---
async def run_bot():
    alcanzable = await test_conexion()
    if not alcanzable:
        raise ConnectionError("api.telegram.org no es alcanzable desde este servidor")

    request = HTTPXRequest(
        connect_timeout=120,
        read_timeout=120,
        write_timeout=120,
        pool_timeout=120,
    )

    app = (Application.builder()
           .token(TOKEN)
           .request(request)
           .build())

    zona_cuba = pytz.timezone('America/Havana')
    app.job_queue.run_daily(enviar_recompensa_3am, time=time(3, 0, tzinfo=zona_cuba))
    app.job_queue.run_daily(enviar_adivinanza_12pm, time=time(12, 0, tzinfo=zona_cuba))
    app.job_queue.run_daily(enviar_misiones_8pm, time=time(20, 0, tzinfo=zona_cuba))
    for h in [2, 5, 8, 11, 14, 17, 20, 23]:
        app.job_queue.run_daily(enviar_mercado, time=time(h, 0, tzinfo=zona_cuba))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calcular", calcular))
    app.add_handler(CommandHandler("cal", calcular))
    app.add_handler(CommandHandler("camp", camp))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("bl", bl))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejador_mensajes))

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

# --- 8. MAIN ---
def main():
    while True:
        try:
            logger.info("Iniciando aplicación...")
            asyncio.run(run_bot())
        except ConnectionError as e:
            logger.error(f"🚫 Red bloqueada: {e}. Esperando 60s...")
            sleep(60)
        except Exception as e:
            logger.error(f"Fallo en el bot: {e}. Reintentando en 15s...")
            sleep(15)

if __name__ == '__main__':
    main()
