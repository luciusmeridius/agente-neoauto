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
        # Lanzamos con user-agent simulando un navegador real para evitar bloqueos
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print(access_msg := f"Navegando a {url_busqueda}...")
            page.goto(url_busqueda, timeout=60000, wait_until="domcontentloaded")
            
            # Damos tiempo a que renderice el contenido dinámico
            page.wait_for_timeout(5000)
            
            # Buscamos contenedores genéricos de anuncios en la lista de resultados
            # Probamos múltiples selectores comunes en portales de clasificados
            items = []
            selectors = [".c-results-item", "div.tec-car-card", "article", ".item-resultado"]
            
            for sel in selectors:
                items = page.query_selector_all(sel)
                if len(items) > 0:
                    print(f"¡Elementos encontrados usando el selector: '{sel}'! Total: {len(items)}")
                    break
            
            if len(items) == 0:
                print("No se encontraron elementos con los selectores habituales. Guardando captura para análisis...")
                page.screenshot(path="error_neoauto.png")
                return

            for item in items[:10]: # Revisamos los primeros 10
                try:
                    # Intentamos capturar título, precio y enlace con selectores flexibles
                    titulo_elem = item.query_selector("h2, h3, .c-results-item__title, a")
                    precio_elem = item.query_selector(".price, .c-results-item__price, span[class*='price']")
                    link_elem = item.query_selector("a")

                    titulo = titulo_elem.inner_text().strip() if titulo_elem else "Sin título"
                    precio = precio_elem.inner_text().strip() if precio_elem else "Consultar precio"
                    link = link_elem.get_attribute("href") if link_elem else ""
                    
                    if link and not link.startswith("http"):
                        link = f"https://neoauto.com{link}"

                    identificador = link if link else titulo

                    if identificador not in autos_vistos and len(titulo) > 3:
                        nuevos_hallazgos += 1
                        mensaje = f"🚨 *¡Nuevo Auto Detectado!*\n\n🚗 *Vehículo:* {titulo}\n💰 *Precio:* {precio}\n🔗 [Ver en NeoAuto]({link})"
                        enviar_alerta_telegram(mensaje)
                        autos_vistos.append(identificador)
                except Exception as inner_e:
                    continue

            guardar_historial(autos_vistos)
            print(f"Revisión finalizada. Nuevas ofertas notificadas: {nuevos_hallazgos}")

        except Exception as e:
            print(f"Error durante el scraping: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    revisar_ofertas()
