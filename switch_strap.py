import requests
from bs4 import BeautifulSoup
import sqlite3
from dotenv import load_dotenv
import datetime
import os

load_dotenv()

DISCORD_URL = os.getenv("DISCORD_URL")




links = [
    'https://www.amazon.pl/Nintendo-10015151-Switch-2/dp/B0F2J4SYJ2/ref=sr_1_5?sr=8-5',
    'https://www.amazon.pl/Nintendo-Konsola-Switch-Wielokolorowy-OLED/dp/B098BYN3X3/ref=sr_1_6?sr=8-6',
    'https://www.amazon.pl/Sony-PlayStation-Console-Split-Bundle/dp/B08HKDSVV2/ref=sr_1_4?__mk_pl_PL=%C3%85M%C3%85%C5%BD%C3%95%C3%91&sr=8-4',
    'https://www.amazon.pl/LEGO-Konstrukcyjny-Doroslych-Astronomii-31212/dp/B0CWH1RMBZ?ref_=ast_sto_dp'
]
headers = {
    "User-Agent": "...",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
    "Accept": "text/html",
    "Connection": "keep-alive"
}
def read_price():
    products = []
    for link in links:
        response = requests.get(link, headers=headers)


        soup = BeautifulSoup(response.text, "html.parser")
        productTitle = soup.find("span",id="productTitle")
        title = productTitle.text.strip() if productTitle  else "brak tytułu"
        price_whole = soup.find("span",class_="a-price-whole")
        price_fraction = soup.find("span", class_="a-price-fraction")
        if price_whole:
            price = price_whole.text.replace("\xa0", "").replace(",", ".")
            if price_fraction:
                price = float(f"{price}{price_fraction.text.strip()}")
        else:
            price = None
        products.append([link,title,price])
    return products
def get_last_price(cursor,link):
    cursor.execute("""
    SELECT price
    FROM amazon
    WHERE link = ?
    ORDER BY date DESC
    LIMIT 1
    """,(link,))
    row = cursor.fetchone()
    if row is None:
        return None
    return float(row[0])

def compare_prices(data):
    alerts = []

    with sqlite3.connect("data/database.db") as conn:
        cursor = conn.cursor()
        for link, title, price in data:
            old_price = get_last_price(cursor, link)
            if old_price is None:
                continue
            if old_price > 0:
                drop = (old_price - price) / old_price

                if drop >= 0.15:
                    alerts.append([link,title,price,old_price,drop])
    return alerts


def send_alert(alerts):

    if not alerts:
        return
    message = "\n\n".join(
        f" {title}\n"
        f"{old:.2f} → {new:.2f} (-{drop * 100:.1f}%)\n"
        f"{link}"
        for link, title, new, old, drop in alerts
    )

    if len(message) > 1900:
        message = message[:1900] + "..."
    print(message)

    response = requests.post(DISCORD_URL, json={"content": message})

    if response.status_code == 204:
        print("Wiadomość wysłana!")
    else:
        print(f"Błąd: {response.status_code} - {response.text}")

def save(data):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect("data/database.db") as conn:
        cursor = conn.cursor()
        for link,title,price in data:
            cursor.execute("""
            INSERT INTO amazon VALUES (?,?,?,?)
            """,(link,title,price,date))
        conn.commit()


data = read_price()

alerts = compare_prices(data)

send_alert(alerts)

save(data)