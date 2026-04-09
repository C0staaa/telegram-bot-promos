import os
import time
import pytz
import random
import requests
import threading
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIGURAÇÃO ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
app = Flask(__name__)
enviados = set()

KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "asus", "logitech", "samsung", "hp"]
MAX_PRICE = 1200

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- WEB SERVER (Saúde do Container) ---
@app.route('/')
def health_check():
    return "Bot is running!", 200

# --- MOTOR DE BUSCA ---
def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas...")
    url = "https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        if "captcha" in r.text.lower() or "robot check" in r.text.lower():
            log("⚠️ Amazon bloqueou o IP. A aguardar próximo ciclo...")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 Diagnóstico: {len(itens)} produtos detetados.")

        for item in itens:
            try:
                texto = item.get_text().lower()
                if not any(k in texto for k in KEYWORDS): continue
                
                preco_tag = item.find("span", class_="a-price-whole")
                if not preco_tag: continue
                
                preco = int(preco_tag.text.split(',')[0].replace(".", "").strip())
                if preco > MAX_PRICE: continue

                h2 = item.find("h2")
                titulo = h2.text.strip()[:80]
                if titulo in enviados: continue

                link = "https://www.amazon.es" + h2.find("a")["href"]
                img = item.find("img", class_="s-image")["src"]

                bot.send_photo(chat_id=CHAT_ID, photo=img, 
                             caption=f"🔥 *OFERTA*\n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [Link]({link})", 
                             parse_mode='Markdown')
                enviados.add(titulo)
                log(f"✅ Enviado: {titulo[:30]}")
                time.sleep(2)
            except: continue
    except Exception as e:
        log(f"❌ Erro no scan: {e}")

# --- INICIALIZAÇÃO ---
def start_bot_logic():
    # Dá tempo ao Flask para subir primeiro
    time.sleep(10)
    procurar_e_enviar()
    
    # Usa pytz corretamente para evitar o TypeError anterior
    tz = pytz.timezone('Europe/Lisbon')
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(procurar_e_enviar, "interval", minutes=20)
    scheduler.start()
    
    while True:
        time.sleep(60)
        log("💓 bot ativo")

if __name__ == "__main__":
    log("🚀 BOT V5.2 STARTUP")
    # Task em segundo plano
    threading.Thread(target=start_bot_logic, daemon=True).start()
    # Processo principal (obrigatório para o Railway não dar Stop)
    app.run(host='0.0.0.0', port=PORT)
