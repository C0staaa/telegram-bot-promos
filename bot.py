import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
import threading
import time
import pytz

# --- CONFIGURAÇÃO ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Filtros
KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "teclado", "rato"]
MAX_PRICE = 1200
enviados = set()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- WEB SERVER (Mantém o Railway ligado) ---
@app.route('/')
def home():
    return "Bot Online", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- MOTOR DE BUSCA ---
def procurar_promocoes():
    # Usando uma URL de pesquisa orgânica que é menos vigiada que a de ofertas
    url = f"https://www.amazon.es/s?k=ofertas+tecnologia&s=date-desc-rank"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/"
    }

    try:
        # Tentativa de bypass simples via parâmetros aleatórios
        r = requests.get(url, headers=headers, params={"ref": random.randint(1,1000)}, timeout=20)
        
        if r.status_code != 200 or "captcha" in r.text.lower():
            log("⚠️ Bloqueio detetado. Amazon pediu Captcha.")
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
            except:
                continue
        return promos
    except Exception as e:
        log(f"❌ Erro: {e}")
        return []

def job():
    log("🔎 Scan iniciado...")
    promos = procurar_promocoes()
    for titulo, preco, img, link in promos:
        if titulo in enviados: continue
        try:
            msg = f"🔥 *OFERTA AMAZON*\n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [Ver na Amazon]({link})"
            bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg, parse_mode='Markdown')
            enviados.add(titulo)
            log(f"✅ Enviado: {titulo[:30]}")
            time.sleep(2)
        except: continue

# --- INICIALIZAÇÃO CORRIGIDA ---
if __name__ == "__main__":
    # 1. Iniciamos o Agendador
    tz = pytz.timezone('Europe/Lisbon')
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(job_verificacao, "interval", minutes=20)
    scheduler.start()
    
    log("🚀 BOT V5 STARTUP")
    
    # 2. Criamos uma tarefa para o Bot não travar o servidor
    threading.Thread(target=job_verificacao, daemon=True).start()
    
    # 3. O Flask corre no processo PRINCIPAL (Importante para o Railway)
    # O Railway precisa que este processo nunca feche
    app.run(host='0.0.0.0', port=PORT)
