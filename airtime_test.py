import requests
import datetime

url = "https://sandbox.vtpass.com/api/pay"

api_key = "7f1cfa18e060f0258d1f0fc78f75917d"
secret_key = "SK_898d9e1bf7d87caddda7ee14ddc1e368db9207740b2"

# Generate unique request ID
request_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

headers = {
    "api-key": api_key,
    "secret-key": secret_key
}

data = {
    "request_id": request_id,
    "serviceID": "mtn",
    "amount": 100,
    "phone": "08011111111"
}
response = requests.post(url, headers=headers, json=data)
result = response.json()

print(result)