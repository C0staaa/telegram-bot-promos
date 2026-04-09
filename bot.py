import requests
from bs4 import BeautifulSoup
from telegram import Bot
import time
import os
import random
from datetime import datetime

# 🔐 Variáveis do Railway
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

# 🔎 filtros
KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android"]
MAX_PRICE = 50

# evitar repetição
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
            log(f"Erro HTTP: {r.status_code}")
            return []

    except Exception as e:
        log(f"Erro request: {e}")
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
    promos = procurar_promocoes()

    if not promos:
        log("Sem promos novas")
        return

    for titulo, preco in promos:
        if titulo in enviados:
            continue

        mensagem = f"🔥 PROMOÇÃO DETETADA\n\n🛒 {titulo}\n💸 {preco}€"

        try:
            bot.send_message(chat_id=CHAT_ID, text=mensagem)
            log(f"Enviado: {titulo}")
            enviados.add(titulo)

        except Exception as e:
            log(f"Erro ao enviar mensagem: {e}")


def main():
    log("Bot iniciado com sucesso!")

    fail_count = 0

    while True:
        try:
            log("A procurar promoções...")
            enviar_promocoes()
            fail_count = 0

        except Exception as e:
            fail_count += 1
            log(f"Erro geral ({fail_count}): {e}")

            if fail_count >= 5:
                log("Muitos erros seguidos, aguardando mais tempo...")

        sleep_time = random.randint(240, 600)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
