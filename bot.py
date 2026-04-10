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

# --- FILTROS EXPANDIDOS ---
# Adiciona aqui tudo o que queres que o bot detete
KEYWORDS = [
    "pc", "gaming", "ssd", "monitor", "iphone", "portatil", "laptop",
    "asus", "logitech", "samsung", "hp", "lenovo", "msi", "rtx", "gtx",
    "teclado", "mouse", "rato", "auscultadores", "headset", "ps5", "xbox",
    "nintendo", "switch", "disco", "ram", "ryzen", "intel", "grafica",
    "tablet", "ipad", "smartwatch", "apple", "xiaomi", "oferta", "desconto"
]
MAX_PRICE = 1500 # Aumentei um pouco para apanhar portáteis melhores

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

@app.route('/')
def health_check():
    return "Bot V5.9 Ativo com Filtros Expandidos!", 200

def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas (Filtro Expandido)...")
    url = f"https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031&ref={random.randint(1,999)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9"
    }

    try:
        r = requests.get(url, headers=headers, timeout=25)
        if "captcha" in r.text.lower() or r.status_code != 200:
            log("⚠️ Bloqueio temporário da Amazon.")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 {len(itens)} produtos analisados.")

        for item in itens:
            try:
                texto_item = item.get_text().lower()
                
                # Verifica se alguma palavra-chave está no texto do produto
                if any(k in texto_item for k in KEYWORDS):
                    preco_tag = item.find("span", class_="a-price-whole")
                    if not preco_tag: continue
                    
                    preco = int(preco_tag.text.split(',')[0].replace(".", "").strip())
                    if preco > MAX_PRICE: continue

                    h2 = item.find("h2")
                    titulo = h2.text.strip()[:80]
                    if titulo in enviados: continue

                    link = "https://www.amazon.es" + h2.find("a")["href"]
                    img_tag = item.find("img", class_="s-image")
                    img_url = img_tag["src"] if img_tag else None

                    msg = f"🔥 *NOVA OFERTA DETETADA*\n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [VER NA AMAZON]({link})"
                    
                    if img_url:
                        bot.send_photo(chat_id=CHAT_ID, photo=img_url, caption=msg, parse_mode='Markdown')
                    else:
                        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                    
                    enviados.add(titulo)
                    log(f"✅ Enviado: {titulo[:30]}...")
                    time.sleep(2)
            except: continue
    except Exception as e:
        log(f"❌ Erro: {e}")

if __name__ == "__main__":
    log("🚀 BOT V5.9 STARTUP")
    fuso_lisboa = pytz.timezone('Europe/Lisbon')
    
    scheduler = BackgroundScheduler(timezone=fuso_lisboa)
    scheduler.add_job(procurar_e_enviar, "interval", minutes=20)
    scheduler.start()
    
    def startup_thread():
        time.sleep(30)
        procurar_e_enviar()
        
    threading.Thread(target=startup_thread, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, threaded=True)
