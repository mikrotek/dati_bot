import requests
from random import choice

def get_free_proxies():
    url = "https://www.proxy-list.download/api/v1/get?type=http"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            proxies = response.text.split("\r\n")
            return [proxy for proxy in proxies if proxy]  # Rimuove eventuali stringhe vuote
    except Exception as e:
        print("❌ Errore nel recupero proxy:", e)
        return []

def test_proxy(proxy):
    """Testa se il proxy è funzionante"""
    url = "http://httpbin.org/ip"  # Sito che restituisce il tuo IP
    try:
        response = requests.get(url, proxies={"http": f"http://{proxy}", "https": f"https://{proxy}"}, timeout=5)
        if response.status_code == 200:
            print(f"✅ Proxy funzionante: {proxy}")
            return True
    except:
        print(f"❌ Proxy non valido: {proxy}")
    return False

# Ottenere e testare i proxy
proxy_list = get_free_proxies()
valid_proxies = [proxy for proxy in proxy_list if test_proxy(proxy)]
print("🔍 Proxy validi trovati:", valid_proxies)
