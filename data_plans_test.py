import requests

api_key = "7f1cfa18e060f0258d1f0fc78f75917d"
public_key = "PK_258d51b91314ca85b68c3b34375482961d7ff05952f"

headers = {
    "api-key": api_key,
    "public-key": public_key
}

url = "https://sandbox.vtpass.com/api/service-variations?serviceID=mtn-data"

response = requests.get(url, headers=headers)
data = response.json()

for item in data['content']['varations']:
    print(item['variation_code'], '-', item['name'], '-', item['variation_amount'])