import requests
API_KEY = "db404127b0d540e61df29639d780181f3bd0670c15fbf8333ab3dcaea08b80dd"
ENRICH_URL = "https://api.peopledatalabs.com/v5/person/enrich"
params = {"api_key": API_KEY, "first_name": "Mike", "last_name": "Alvarado", "locality": "Wichita Falls", "region": "TX"}
response = requests.get(ENRICH_URL, params=params)
print(response.json())
