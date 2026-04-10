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

KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "laptop", "asus", "logitech", "samsung", "hp", "ps5", "grafica", "apple"]
MAX_PRICE = 1500

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

@app.route('/')
def health_check():
    return "OK", 200

def procurar_e_enviar():
    # Pausa aleatória inicial para não parecer um bot logo ao ligar
    time.sleep(random.randint(5, 15))
    log("🔎 Iniciando scan...")
    
    url = f"https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031&ref=nav_custrec_signin_{random.randint(1,999)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=30)
        
        if "captcha" in r.text.lower() or r.status_code != 200:
            log("⚠️ Bloqueio da Amazon. A tentar noutro ciclo...")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 Scan concluído: {len(itens)} produtos.")

        for item in itens:
            try:
                texto = item.get_text().lower()
                if any(k in texto for k in KEYWORDS):
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
                    time.sleep(3)
            except: continue
    except Exception as e:
        log(f"❌ Erro: {e}")

# --- INICIALIZAÇÃO SEGURA ---
fuso = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=fuso)
scheduler.add_job(procurar_e_enviar, 'interval', minutes=30) # Aumentado para 30min para evitar bans
scheduler.start()

# Inicia o primeiro scan numa thread "silenciosa"
def startup():
    time.sleep(60) # Dá 1 minuto para o Railway validar o Healthcheck
    procurar_e_enviar()

threading.Thread(target=startup, daemon=True).start()

if __name__ == "__main__":
    # Este bloco só corre localmente. No Railway, o Gunicorn usa o 'app' lá de cima.
    app.run(host='0.0.0.0', port=PORT)
