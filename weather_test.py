import requests

city = "Lagos"
url = f"https://wttr.in/{city}?format=j1"

response = requests.get(url)
data = response.json()

temperature = data['current_condition'][0]['temp_C']
description = data['current_condition'][0]['weatherDesc'][0]['value']

print(f"Weather in {city}: {temperature}°C, {description}")