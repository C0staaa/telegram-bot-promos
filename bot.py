import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# 🔐 ENV
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("TOKEN ou CHAT_ID em falta")

bot = Bot(token=TOKEN)

KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android"]
MAX_PRICE = 50

enviados = set()

HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_headers():
    return random.choice(HEADERS_LIST)


def procurar_promocoes():
    url = "https://www.amazon.es/gp/goldbox"

    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
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
            preco = int(preco_tag.text.replace(".", "").strip())
        except:
            continue

        if preco > MAX_PRICE:
            continue

        promos.append((texto[:80], preco))

    return promos


def enviar_promocoes():
    try:
        log("A procurar promoções...")

        promos = procurar_promocoes()

        if not promos:
            log("Sem promos novas")
            return

        for titulo, preco in promos:
            if titulo in enviados:
                continue

            mensagem = f"🔥 PROMOÇÃO\n\n🛒 {titulo}\n💸 {preco}€"

            bot.send_message(chat_id=CHAT_ID, text=mensagem)

            enviados.add(titulo)
            log(f"Enviado: {titulo}")

    except Exception as e:
        log(f"Erro na execução: {e}")


# 🔁 Scheduler (em vez de while True)
scheduler = BackgroundScheduler()
scheduler.add_job(enviar_promocoes, 'interval', minutes=5)

def main():
    log("🚀 Bot 24/7 iniciado com scheduler")

    enviar_promocoes()  # run inicial

    scheduler.start()

    # mantém processo vivo
    while True:
        pass


if __name__ == "__main__":
    main()
