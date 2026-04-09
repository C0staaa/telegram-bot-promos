import requests
from bs4 import BeautifulSoup
from telegram import Bot
import time
import os

# 🔐 vem do Render (NUNCA escrevas aqui)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

# 🔎 filtros (podes alterar depois)
KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android"]
MAX_PRICE = 50

# evita repetir mensagens
enviados = set()


def procurar_promocoes():
    url = "https://www.amazon.es/gp/goldbox"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    produtos = soup.find_all("div", {"data-deal-id": True})

    promos = []

    for p in produtos:
        texto = p.get_text().lower()

        # filtro por palavras
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


def enviar():
    promos = procurar_promocoes()

    if not promos:
        print("Sem promos novas")
        return

    for titulo, preco in promos:
        if titulo in enviados:
            continue

        mensagem = f"🔥 PROMOÇÃO DETETADA\n\n🛒 {titulo}\n💸 {preco}€"

        bot.send_message(chat_id=CHAT_ID, text=mensagem)

        enviados.add(titulo)
        print("Enviado:", titulo)


# 🔁 loop 30 minutos
while True:
    try:
        enviar()
    except Exception as e:
        print("Erro:", e)

    time.sleep(1800)