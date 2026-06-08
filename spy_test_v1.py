import requests

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"

url = "https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2025-06-01/2025-06-30"

response = requests.get(
    url,
    params={
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apiKey": API_KEY
    }
)

print("STATUS:", response.status_code)

data = response.json()

print(data.keys())

if "results" in data:
    print("Rows:", len(data["results"]))
else:
    print(data)