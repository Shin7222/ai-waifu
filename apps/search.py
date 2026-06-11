import webbrowser

def run():
    print("--- Web Search App ---")
    query = input("Apa yang ingin Anda cari di Google? ")
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    print(f"Membuka {url} di browser...")
