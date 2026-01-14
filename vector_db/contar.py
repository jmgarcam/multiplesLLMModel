import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5010/news/{source}?date={date}&shour=00&sminute=0&ehour=23&eminute=00"

# Fuentes a consultar
sources = ["El_Pais", "El_Mundo", "ABC", "El_Correo", "La_Vanguardia", "La_Verdad"]

# Fecha de inicio y fin
start_date = datetime(2025, 9, 26)
end_date = datetime(2025, 10, 25)

current = start_date

# Acumulador total por fuente
totals = {source: 0 for source in sources}

while current <= end_date:
    formatted_date = current.strftime("%d-%m-%Y")

    for source in sources:
        url = BASE_URL.format(source=source, date=formatted_date)
        print(f"Consultando: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            total_items = data.get("total_items", 0)
            totals[source] += total_items

            print(f"  {source} {formatted_date}: total_items={total_items}")

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar {source} {formatted_date}: {e}")

    current += timedelta(days=1)

print("\n=== RESULTADOS FINALES ===")
for source in sources:
    print(f"{source}: {totals[source]} total_items")
