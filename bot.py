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

KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "laptop", "asus", "logitech", "samsung", "hp", "ps5", "grafica", "apple", "rtx"]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

@app.route('/')
def health_check():
    return "OK", 200

def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas...")
    
    # Lista de User-Agents para variar a identidade
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]

    url = f"https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031&ref=v62_{random.randint(1,999)}"
    
    headers = {
        "User-Agent": random.choice(ua_list),
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8",
        "Referer": "https://www.google.pt/"
    }

    try:
        # Usamos timeout maior e uma sessão fresca
        with requests.Session() as s:
            r = s.get(url, headers=headers, timeout=30)
            
        if "captcha" in r.text.lower() or r.status_code != 200:
            log(f"⚠️ Amazon bloqueou (Status: {r.status_code}). A tentar no próximo ciclo...")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 Scan concluído: {len(itens)} produtos encontrados.")

        for item in itens[:10]: # Analisa os 10 primeiros para evitar lentidão
            try:
                h2 = item.find("h2")
                if not h2: continue
                
                titulo = h2.text.strip()
                if titulo in enviados: continue

                preco_tag = item.find("span", class_="a-price-whole")
                if not preco_tag: continue
                
                link = "https://www.amazon.es" + h2.find("a")["href"]
                msg = f"🔥 *OFERTA*\n\n📦 {titulo[:100]}...\n💰 *{preco_tag.text}€*\n\n🔗 [Link]({link})"
                
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                enviados.add(titulo)
                time.sleep(5) # Pausa maior entre mensagens
            except: continue
            
    except Exception as e:
        log(f"❌ Erro: {e}")

# --- AGENDADOR ---
fuso = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=fuso)
scheduler.add_job(procurar_e_enviar, 'interval', minutes=30)
scheduler.start()

# Espera 2 minutos antes do primeiro scan para o IP "arrefecer"
def startup_delayed():
    time.sleep(120)
    procurar_e_enviar()

threading.Thread(target=startup_delayed, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
