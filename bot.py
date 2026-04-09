import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz

# 🔐 CONFIGURAÇÕES DE AMBIENTE (RAILWAY)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise Exception("ERRO: TOKEN ou CHAT_ID não configurados nas variáveis de ambiente!")

bot = Bot(token=TOKEN)

# 🔎 FILTROS DE PROCURA
# Adicionei "oferta" e "desconto" para forçar a detecção em testes
KEYWORDS = ["pc", "gaming", "teclado", "rato", "ssd", "monitor", "iphone", "android", "portatil", "oferta", "desconto"]
MAX_PRICE = 1000 

# Evitar duplicados na mesma sessão
enviados = set()

# Headers para simular um navegador real e evitar bloqueios
HEADERS_LIST = [
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
]

def log(msg):
    # flush=True garante que o log aparece na hora no painel do Railway
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def get_headers():
    return random.choice(HEADERS_LIST)

# 🔎 MOTOR DE SCRAPING
def procurar_promocoes():
    url = "https://www.amazon.es/gp/goldbox"

    try:
        r = requests.get(url, headers=get_headers(), timeout=20)
        if r.status_code != 200:
            log(f"⚠️ Erro HTTP {r.status_code} ao aceder à Amazon")
            return []
    except Exception as e:
        log(f"❌ Falha de conexão: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    
    # --- TESTE DE DIAGNÓSTICO ---
    # A Amazon muda os IDs e Classes constantemente. Tentamos os mais comuns de 2024/2026.
    produtos = soup.find_all("div", {"data-testid": "grid-desktop-wheel"}) 
    if not produtos:
        produtos = soup.find_all("div", {"data-deal-id": True})
    if not produtos:
        produtos = soup.find_all("div", class_="a-section") # Fallback genérico

    log(f"📊 Diagnóstico: Detetei {len(produtos)} blocos de conteúdo na página.")
    # ----------------------------

    promos = []

    for p in produtos:
        texto = p.get_text().lower()

        # Verifica se o produto interessa
        if not any(k in texto for k in KEYWORDS):
            continue

        # Tentativa de capturar preço em diferentes formatos
        preco_tag = p.find("span", class_="a-price-whole")
        if not preco_tag:
            preco_tag = p.find("span", class_="a-offscreen")

        try:
            # Limpa caracteres não numéricos
            preco_raw = preco_tag.text.replace(".", "").replace(",", "").replace("€", "").strip()
            preco = int(''.join(filter(str.isdigit, preco_raw)))
        except:
            continue

        if preco > MAX_PRICE or preco == 0:
            continue

        # Captura de Imagem
        img_tag = p.find("img")
        img_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None

        # Captura de Link
        link_tag = p.find("a", href=True)
        if link_tag:
            href = link_tag["href"]
            link = href if href.startswith("http") else "https://www.amazon.es" + href
        else:
            link = "https://www.amazon.es/gp/goldbox"

        titulo = texto[:85].strip().replace("\n", " ")
        promos.append((titulo, preco, img_url, link))

    return promos

# 📤 FUNÇÃO DE ENVIO TELEGRAM
def enviar_promocoes():
    try:
        log("🔎 Iniciando scan de ofertas...")
        promos = procurar_promocoes()

        if not promos:
            log("ℹ️ Scan terminado: Nenhuma oferta válida encontrada para os filtros atuais.")
            return

        for titulo, preco, img_url, link in promos:
            if titulo in enviados:
                continue

            # Formatação da mensagem (Markdown)
            mensagem = (
                f"🔥 *PROMOÇÃO DETETADA NA AMAZON*\n\n"
                f"📦 *{titulo.upper()}*\n"
                f"💰 *Preço:* {preco}€\n\n"
                f"🔗 [CLIQUE AQUI PARA VER A OFERTA]({link})"
            )

            try:
                if img_url and img_url.startswith("http"):
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
                log(f"✅ Notificação enviada: {titulo[:30]}...")
                time.sleep(3) # Pausa técnica para evitar spam-block
                
            except Exception as e:
                log(f"❌ Erro ao disparar Telegram: {e}")

    except Exception as e:
        log(f"❌ Erro crítico no loop: {e}")

# 🔁 SCHEDULER (Configurado para Lisboa)
tz = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(enviar_promocoes, "interval", minutes=5)

def main():
    log("🚀 BOT ONLINE NO RAILWAY")
    
    # Execução imediata ao ligar para não esperar 5 minutos pelo primeiro teste
    enviar_promocoes() 

    scheduler.start()

    try:
        while True:
            time.sleep(60)
            log("💓 bot ativo")
    except (KeyboardInterrupt, SystemExit):
        log("🛑 Encerrando bot...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
