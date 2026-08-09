import os
import json
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

HISTORIAL_FILE = "autos_vistos.json"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def guardar_historial(historial):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=4)

def enviar_alerta_telegram(mensaje):
    # Usaremos "Secrets" de GitHub para mantener tus claves seguras
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not TOKEN or not CHAT_ID:
        print(f"[MODO LOG] {mensaje}")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error al enviar Telegram: {e}")

def revisar_ofertas():
    print(f"\n--- Revisión automática en NeoAuto: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    autos_vistos = cargar_historial()
    nuevos_hallazgos = 0
    url_busqueda = "https://neoauto.com/auto/comprar"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url_busqueda, timeout=60000)
            page.wait_for_selector(".c-results-item", timeout=15000)
            items = page.query_selector_all(".c-results-item")
            print(f"Vehículos encontrados en la página: {len(items)}")

            for item in items:
                titulo_elem = item.query_selector(".c-results-item__title")
                precio_elem = item.query_selector(".c-results-item__price")
                link_elem = item.query_selector("a.c-results-item__anchor")

                titulo = titulo_elem.inner_text().strip() if titulo_elem else "Sin título"
                precio = precio_elem.inner_text().strip() if precio_elem else "Sin precio"
                link = link_elem.get_attribute("href") if link_elem else ""
                
                if link and not link.startswith("http"):
                    link = f"https://neoauto.com{link}"

                identificador = link if link else titulo

                if identificador not in autos_vistos:
                    nuevos_hallazgos += 1
                    mensaje = f"🚨 *¡Nuevo Auto Detectado!*\n\n🚗 *Vehículo:* {titulo}\n💰 *Precio:* {precio}\n🔗 [Ver en NeoAuto]({link})"
                    enviar_alerta_telegram(mensaje)
                    autos_vistos.append(identificador)

            guardar_historial(autos_vistos)
            print(f"Revisión finalizada. Nuevas ofertas notificadas: {nuevos_hallazgos}")

        except Exception as e:
            print(f"Error durante el scraping: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    revisar_ofertas()
