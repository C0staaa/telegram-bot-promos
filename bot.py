import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz

# 🔐 ENV
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("Variáveis TOKEN ou CHAT_ID em falta!")

bot = Bot(token=TOKEN)

# 🔎 FILTROS (Mudei para keywords mais genéricas para o teste disparar)
KEYWORDS = ["pc", "gaming", "ssd", "teclado", "rato", "monitor", "iphone", "portatil", "asus", "hp", "logitech", "samsung"]
MAX_PRICE = 1000 
enviados = set()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# 🧪 URL DE PESQUISA (Mais estável que a página de ofertas principal)
# Este link já filtra por produtos com "Desconto" (Ofertas)
URL_SCAN = "https://www.amazon.es/s?k=informatica+gaming&rh=p_n_specials_match%3A21622307031"

def procurar_promocoes():
    # Headers mais "humanos" para evitar o bloqueio
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/"
    }

    try:
        r = requests.get(URL_SCAN, headers=headers, timeout=20)
        if "api-services-support@amazon.com" in r.text or r.status_code == 503:
            log("⚠️ Amazon bloqueou (Bot Detection/Captcha)")
            return []
    except Exception as e:
        log(f"❌ Erro: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    
    # Seletores de produtos em páginas de pesquisa (são mais estáveis)
    itens = soup.find_all("div", {"data-component-type": "s-search-result"})
    
    log(f"📊 Diagnóstico: Detetei {len(itens)} produtos na pesquisa.")

    promos = []

    for item in itens:
        texto = item.get_text().lower()

        # 1. Filtro de Keywords
        if not any(k in texto for k in KEYWORDS):
            continue

        try:
            # 2. Captura de Preço (Seletor clássico de pesquisa)
            preco_inteiro = item.find("span", class_="a-price-whole")
            if not preco_inteiro: continue
            
            preco_str = preco_inteiro.text.replace(".", "").replace(",", "").strip()
            preco = int(''.join(filter(str.isdigit, preco_str)))

            if preco > MAX_PRICE or preco == 0:
                continue

            # 3. Título e Link
            h2 = item.find("h2")
            titulo = h2.text.strip()[:90]
            link = "https://www.amazon.es" + h2.find("a")["href"]

            # 4. Imagem
            img = item.find("img", class_="s-image")
            img_url = img["src"] if img else None

            promos.append((titulo, preco, img_url, link))
        except:
            continue

    return promos

def enviar_promocoes():
    try:
        log("🔎 A iniciar scan de pesquisa...")
        promos = procurar_promocoes()

        if not promos:
            log("ℹ️ Nada encontrado.")
            return

        for titulo, preco, img_url, link in promos:
            if titulo in enviados:
                continue

            msg = (
                f"🔥 *OFERTA ENCONTRADA*\n\n"
                f"📦 {titulo}\n"
                f"💰 *Preço: {preco}€*\n\n"
                f"🔗 [VER NA AMAZON]({link})"
            )

            try:
                if img_url:
                    bot.send_photo(chat_id=CHAT_ID, photo=img_url, caption=msg, parse_mode='Markdown')
                else:
                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                
                enviados.add(titulo)
                log(f"✅ Enviado: {titulo[:30]}...")
                time.sleep(2)
            except Exception as e:
                log(f"❌ Erro Telegram: {e}")

    except Exception as e:
        log(f"❌ Erro geral: {e}")

# Scheduler
tz = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(enviar_promocoes, "interval", minutes=5)

def main():
    log("🚀 BOT REINICIADO (MODO PESQUISA)")
    enviar_promocoes() 
    scheduler.start()
    try:
        while True:
            time.sleep(60)
            log("💓 bot ativo")
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
