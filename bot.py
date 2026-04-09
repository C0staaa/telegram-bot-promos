import requests
from bs4 import BeautifulSoup
from telegram import Bot
import time
import os

# 🔐 Variáveis do Railway
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

# 🔎 filtros
KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android"]
MAX_PRICE = 50

# evitar repetição
enviados = set()


def procurar_promocoes():
    url = "https://www.amazon.es/gp/goldbox"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print("Erro request:", e)
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
        print("Sem promos novas")
        return

    for titulo, preco in promos:
        if titulo in enviados:
            continue

        mensagem = f"🔥 PROMOÇÃO DETETADA\n\n🛒 {titulo}\n💸 {preco}€"

        try:
            bot.send_message(chat_id=CHAT_ID, text=mensagem)
            print("Enviado:", titulo)

            enviados.add(titulo)

        except Exception as e:
            print("Erro ao enviar mensagem:", e)


print("🤖 Bot iniciado com sucesso!")

# 🔁 LOOP ETERNO (CRÍTICO PARA RAILWAY)
while True:
    try:
        print("🔎 A procurar promoções...")
        enviar_promocoes()

    except Exception as e:
        print("Erro geral:", e)

    # evita crash e abuso de requests
    time.sleep(900)  # 30 minutos
