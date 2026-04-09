import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# 🔐 VARIÁVEIS DE AMBIENTE
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# O Railway injeta a variável PORT automaticamente. Se não houver, usa 8080.
PORT = int(os.getenv("PORT", 8080))

if not TOKEN or not CHAT_ID:
    raise Exception("ERRO: TOKEN ou CHAT_ID não configurados no Railway!")

bot = Bot(token=TOKEN)

# 🔎 CONFIGURAÇÕES DE FILTRO
KEYWORDS = ["pc", "gaming", "ssd", "monitor", "iphone", "portatil", "asus", "logitech", "samsung", "hp", "oferta", "desconto"]
MAX_PRICE = 1200
enviados = set()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- 🌍 PARTE 1: SERVIDOR DE HEALTHCHECK (Para o Railway não dar STOP) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        return # Silenciar logs do servidor web para não sujar o painel

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    log(f"🌍 Servidor Healthcheck ativo na porta {PORT}")
    server.serve_forever()

# --- 🔎 PARTE 2: MOTOR DE SCRAPING (Modo Pesquisa) ---
def procurar_promocoes():
    # URL de pesquisa filtrada por informática + ofertas
    url = "https://www.amazon.es/s?k=informatica&rh=p_n_specials_match%3A21622307031"
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    try:
        # Tenta primeiro a home para gerar cookies básicos
        session.get("https://www.amazon.es", headers=headers, timeout=10)
        time.sleep(random.uniform(1, 3))
        
        r = session.get(url, headers=headers, timeout=20)
        
        if "captcha" in r.text.lower() or r.status_code == 503:
            log("⚠️ Amazon bloqueou com Captcha. O IP do servidor pode estar marcado.")
            return []
            
    except Exception as e:
        log(f"❌ Erro na requisição: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    # Procure pelos containers de resultados de pesquisa
    itens = soup.find_all("div", {"data-component-type": "s-search-result"})
    
    log(f"📊 Diagnóstico: Detetei {len(itens)} itens na página.")

    promos = []
    for item in itens:
        try:
            texto = item.get_text().lower()
            if not any(k in texto for k in KEYWORDS): continue

            preco_tag = item.find("span", class_="a-price-whole")
            if not preco_tag: continue
            
            # Limpa o preço (pega a parte antes da vírgula)
            preco_raw = preco_tag.text.split(',')[0].replace(".", "").strip()
            preco = int(''.join(filter(str.isdigit, preco_raw)))
            
            if preco > MAX_PRICE or preco < 5: continue

            h2 = item.find("h2")
            if not h2: continue
            
            titulo = h2.text.strip()[:90]
            link_tag = h2.find("a")
            if not link_tag: continue
            link = "https://www.amazon.es" + link_tag["href"]
            
            img_tag = item.find("img", class_="s-image")
            img_url = img_tag["src"] if img_tag else None

            promos.append((titulo, preco, img_url, link))
        except:
            continue
    return promos

def enviar_promocoes():
    log("🔎 Iniciando scan de 5 minutos...")
    promos = procurar_promocoes()
    
    if not promos:
        log("ℹ️ Nada encontrado neste ciclo.")
        return

    for titulo, preco, img, link in promos:
        if titulo in enviados: continue
        
        try:
            msg = (
                f"🔥 *OFERTA ENCONTRADA*\n\n"
                f"📦 {titulo}\n"
                f"💰 *Preço: {preco}€*\n\n"
                f"🔗 [ABRIR NA AMAZON]({link})"
            )
            
            if img:
                bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg, parse_mode='Markdown')
            else:
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
            
            enviados.add(titulo)
            log(f"✅ Enviado: {titulo[:30]}...")
            time.sleep(3)
        except Exception as e:
            log(f"❌ Erro ao enviar para o Telegram: {e}")

# --- 🚀 EXECUÇÃO ---

# Inicia o servidor de Healthcheck numa thread separada (importante!)
threading.Thread(target=run_server, daemon=True).start()

# Configura o Scheduler
tz = pytz.timezone('Europe/Lisbon')
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(enviar_promocoes, "interval", minutes=5)

def main():
    log("🚀 BOT ONLINE (V3 - Anti-Stop)")
    
    # Primeira execução manual
    enviar_promocoes()
    
    scheduler.start()

    # Loop principal infinito
    while True:
        time.sleep(60)
        log("💓 bot ativo")

if __name__ == "__main__":
    main()
