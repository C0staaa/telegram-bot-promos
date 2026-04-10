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

# Filtros de Pesquisa
KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "asus", "logitech", "samsung", "hp"]
MAX_PRICE = 1200

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- WEB SERVER (Para o Railway manter o bot vivo) ---
@app.route('/')
def health_check():
    return "Bot V5.8 está Online!", 200

# --- LÓGICA DE SCRAPING ---
def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas...")
    # URL com parâmetro aleatório para tentar evitar o bloqueio da Amazon
    url = f"https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031&ref={random.randint(1,999)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9",
        "Referer": "https://www.google.com/"
    }

    try:
        r = requests.get(url, headers=headers, timeout=25)
        
        # Verifica se fomos bloqueados (Captcha)
        if "captcha" in r.text.lower() or r.status_code != 200:
            log("⚠️ Amazon bloqueou o acesso (Captcha ou IP).")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 Diagnóstico: {len(itens)} produtos detetados.")

        for item in itens:
            try:
                texto_completo = item.get_text().lower()
                
                # 1. Filtro de Palavras-Chave
                if not any(k in texto_completo for k in KEYWORDS):
                    continue
                
                # 2. Extração de Preço
                preco_tag = item.find("span", class_="a-price-whole")
                if not preco_tag:
                    continue
                
                preco_texto = preco_tag.text.split(',')[0].replace(".", "").strip()
                preco = int(preco_texto)
                
                # 3. Filtro de Preço Máximo
                if preco > MAX_PRICE:
                    continue

                # 4. Título e Link
                h2 = item.find("h2")
                titulo = h2.text.strip()[:80]
                
                if titulo in enviados:
                    continue

                link = "https://www.amazon.es" + h2.find("a")["href"]
                img_tag = item.find("img", class_="s-image")
                img_url = img_tag["src"] if img_tag else None

                # 5. Envio para o Telegram
                msg = f"🔥 *OFERTA ENCONTRADA*\n\n📦 {titulo}\n💰 *{preco}€*\n\n🔗 [VER NA AMAZON]({link})"
                
                if img_url:
                    bot.send_photo(chat_id=CHAT_ID, photo=img_url, caption=msg, parse_mode='Markdown')
                else:
                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                
                enviados.add(titulo)
                log(f"✅ Enviado: {titulo[:30]}...")
                time.sleep(2) # Pausa entre envios
                
            except Exception as e:
                continue

    except Exception as e:
        log(f"❌ Erro crítico no scan: {e}")

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    log("🚀 BOT V5.8 STARTUP (CORREÇÃO TIMEZONE)")
    
    # Configuração do Fuso Horário corrigida para o APScheduler
    fuso_lisboa = pytz.timezone('Europe/Lisbon')
    
    # 1. Iniciar Agendador
    scheduler = BackgroundScheduler(timezone=fuso_lisboa)
    scheduler.add_job(procurar_e_enviar, "interval", minutes=20)
    scheduler.start()
    
    # 2. Execução inicial em thread separada (espera 30s para o Flask subir)
    def inicio_atrasado():
        time.sleep(30)
        procurar_e_enviar()
        
    threading.Thread(target=inicio_atrasado, daemon=True).start()
    
    # 3. Flask como processo principal para o Railway não desligar
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
