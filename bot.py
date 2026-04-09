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

# Filtros
KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "asus", "logitech", "samsung", "hp"]
MAX_PRICE = 1200

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- WEB SERVER (Obrigatório para o Railway) ---
@app.route('/')
def health_check():
    return "Bot is active", 200

# --- MOTOR DE BUSCA ---
def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas...")
    # URL de pesquisa variada para evitar bloqueios constantes
    url = "https://www.amazon.es/s?k=ofertas+informatica&s=date-desc-rank"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9",
        "Referer": "https://www.google.com/"
    }

    try:
        # Adicionamos um parâmetro aleatório para a URL parecer sempre nova
        r = requests.get(url, headers=headers, params={"ref": random.randint(1,9999)}, timeout=25)
        
        if "captcha" in r.text.lower() or r.status_code != 200:
            log("⚠️ Bloqueio ou Captcha detetado.")
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
                             caption=f"🔥 *OFERTA AMAZON*\n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [Link]({link})", 
                             parse_mode='Markdown')
                enviados.add(titulo)
                log(f"✅ Enviado: {titulo[:30]}")
                time.sleep(2)
            except: continue
    except Exception as e:
        log(f"❌ Erro no scan: {e}")

if __name__ == "__main__":
    log("🚀 BOT V5.5 - MODO ATIVO")
    
    # 1. Agendador
    tz = pytz.timezone('Europe/Lisbon')
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(procurar_e_enviar, "interval", minutes=30)
    scheduler.start()
    
    # 2. Inicia o scan em segundo plano após 60s
    # Aumentamos o delay para o Railway estabilizar o domínio primeiro
    def delay_start():
        time.sleep(60)
        procurar_e_enviar()
    threading.Thread(target=delay_start, daemon=True).start()
    
    # 3. Flask com Keep-Alive
    # Usamos o threaded=True para o servidor não bloquear enquanto o bot pesquisa
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
