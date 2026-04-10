import os
import time
import threading
import requests
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

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

@app.route('/')
def health_check():
    return "Bot is running", 200

def procurar_e_enviar():
    log("🔎 Iniciando scan de ofertas...")
    url = "https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        itens = soup.find_all("div", {"data-component-type": "s-search-result"})
        log(f"📊 Diagnóstico: {len(itens)} produtos detetados.")

        # Lógica de envio simplificada para estabilidade
        for item in itens[:5]: # Testa apenas os 5 primeiros
            h2 = item.find("h2")
            if h2:
                titulo = h2.text.strip()[:50]
                if titulo not in enviados:
                    link = "https://www.amazon.es" + h2.find("a")["href"]
                    bot.send_message(chat_id=CHAT_ID, text=f"🔥 Oferta: {titulo}\n{link}")
                    enviados.add(titulo)
                    time.sleep(1)
    except Exception as e:
        log(f"❌ Erro: {e}")

# Inicia o agendador globalmente
scheduler = BackgroundScheduler()
scheduler.add_job(procurar_e_enviar, 'interval', minutes=20)
scheduler.start()

if __name__ == "__main__":
    # Execução local
    app.run(host='0.0.0.0', port=PORT)
