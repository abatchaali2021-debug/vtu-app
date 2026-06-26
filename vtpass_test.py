import requests

url = "https://sandbox.vtpass.com/api/balance"

api_key = "7f1cfa18e060f0258d1f0fc78f75917d"
public_key = "PK_258d51b91314ca85b68c3b34375482961d7ff05952f"

headers = {
    "api-key": api_key,
    "public-key": public_key
}

response = requests.get(url, headers=headers)
data = response.json()

print(data)