import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# 🔐 ENV
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)

# 🔎 FILTROS
KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "asus", "logitech", "samsung"]
MAX_PRICE = 1200
enviados = set()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# 🌍 HEALTHCHECK (Railway Safe)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active")
    def log_message(self, format, *args): return

def run_server():
    HTTPServer(('0.0.0.0', PORT), HealthCheckHandler).serve_forever()

# 🔎 SCRAPING V4 (ANTI-CAPTCHA)
def procurar_promocoes():
    # URL de pesquisa mais "discreta"
    url = "https://www.amazon.es/s?k=ofertas+informatica"
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]

    session = requests.Session()
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Referer": "https://www.google.es/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        # 1. Visita a Home primeiro (gera cookies)
        session.get("https://www.amazon.es", headers=headers, timeout=15)
        time.sleep(random.uniform(2, 5))
        
        # 2. Faz a pesquisa real
        r = session.get(url, headers=headers, timeout=20)
        
        if "captcha" in r.text.lower() or "robot check" in r.text.lower():
            log("⚠️ Bloqueio por Captcha (IP Railway marcado).")
            return []
            
    except Exception as e:
        log(f"❌ Erro: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    itens = soup.find_all("div", {"data-component-type": "s-search-result"})
    log(f"📊 Diagnóstico: {len(itens)} itens detetados.")

    promos = []
    for item in itens:
        try:
            texto = item.get_text().lower()
            if not any(k in texto for k in KEYWORDS): continue

            preco_tag = item.find("span", class_="a-price-whole")
            if not preco_tag: continue
            
            preco = int(''.join(filter(str.isdigit, preco_tag.text.split(',')[0])))
            if preco > MAX_PRICE or preco < 10: continue

            h2 = item.find("h2")
            titulo = h2.text.strip()[:85]
            link = "https://www.amazon.es" + h2.find("a")["href"]
            img = item.find("img", class_="s-image")["src"]

            promos.append((titulo, preco, img, link))
        except: continue
    return promos

def enviar_promocoes():
    log("🔎 Scan iniciado...")
    promos = procurar_promocoes()
    if not promos: return

    for titulo, preco, img, link in promos:
        if titulo in enviados: continue
        try:
            msg = f"🔥 *OFERTA* \n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [Ver na Amazon]({link})"
            bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg, parse_mode='Markdown')
            enviados.add(titulo)
            log(f"✅ Enviado: {titulo[:30]}")
            time.sleep(3)
        except Exception as e: log(f"❌ Erro Telegram: {e}")

threading.Thread(target=run_server, daemon=True).start()

tz = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(enviar_promocoes, "interval", minutes=15) # Aumentei para 15 min para evitar bloqueio

def main():
    log("🚀 BOT ONLINE (V4)")
    enviar_promocoes()
    scheduler.start()
    while True: time.sleep(60)

if __name__ == "__main__":
    main()
