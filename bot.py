import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz  # Necessário para corrigir o erro de timezone

# 🔐 ENV
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("TOKEN ou CHAT_ID em falta no ambiente")

bot = Bot(token=TOKEN)

# 🔎 filtros
KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android"]
MAX_PRICE = 50

# evitar repetição
enviados = set()

# headers anti-bot básico
HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"},
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_headers():
    return random.choice(HEADERS_LIST)

# 🔎 SCRAPING
def procurar_promocoes():
    url = "https://www.amazon.es/gp/goldbox"

    try:
        r = requests.get(url, headers=get_headers(), timeout=15)
        if r.status_code != 200:
            log(f"HTTP {r.status_code}")
            return []
    except Exception as e:
        log(f"Request error: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    produtos = soup.find_all("div", {"data-deal-id": True})

    promos = []

    for p in produtos:
        texto = p.get_text().lower()

        if not any(k in texto for k in KEYWORDS):
            continue

        preco_tag = p.find("span", class_="a-price-whole")

        try:
            # Limpeza do preço para lidar com formatos europeus (ponto/vírgula)
            preco_str = preco_tag.text.replace(".", "").replace(",", "").strip()
            preco = int(preco_str)
        except:
            continue

        if preco > MAX_PRICE:
            continue

        # 🖼 imagem
        img_tag = p.find("img")
        img_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None

        # 🔗 link
        link_tag = p.find("a", href=True)
        link = "https://www.amazon.es" + link_tag["href"] if link_tag else "https://www.amazon.es/gp/goldbox"

        titulo = texto[:80].strip()
        promos.append((titulo, preco, img_url, link))

    return promos

# 📤 ENVIAR
def enviar_promocoes():
    try:
        log("🔎 A procurar promoções...")
        promos = procurar_promocoes()

        if not promos:
            log("Sem promos novas ou critérios não atingidos")
            return

        for titulo, preco, img_url, link in promos:
            if titulo in enviados:
                continue

            mensagem = (
                f"🔥 **PROMOÇÃO DETETADA**\n\n"
                f"🛒 {titulo.capitalize()}\n"
                f"💸 **{preco}€**\n\n"
                f"🔗 [Ver na Amazon]({link})"
            )

            try:
                if img_url:
                    bot.send_photo(
                        chat_id=CHAT_ID,
                        photo=img_url,
                        caption=mensagem,
                        parse_mode='Markdown'
                    )
                else:
                    bot.send_message(
                        chat_id=CHAT_ID,
                        text=mensagem,
                        parse_mode='Markdown'
                    )
                
                enviados.add(titulo)
                log(f"Enviado: {titulo}")
                time.sleep(2) # Pequeno delay para evitar spam/block do Telegram
                
            except Exception as e:
                log(f"Erro ao enviar para Telegram: {e}")

    except Exception as e:
        log(f"Erro na execução geral: {e}")

# 🔁 Configuração do Scheduler
# Definimos o fuso horário explicitamente para evitar o erro do pytz
tz = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(enviar_promocoes, "interval", minutes=5)

def main():
    log("🚀 Bot 24/7 iniciado")
    
    # Primeira execução manual ao ligar
    enviar_promocoes() 

    scheduler.start()

    try:
        # Loop para manter o Railway/Servidor ativo
        while True:
            time.sleep(60)
            log("💓 bot ativo")
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
