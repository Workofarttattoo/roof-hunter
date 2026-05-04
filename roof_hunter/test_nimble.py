import requests

API_KEY = "nWbVJzkIknO4Z9TSHNSNO2HZwVmmP9"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

url = "https://app.nimble.com/api/v1/contact"
payload = {
    "record_type": "person",
    "fields": {
        "first name": [{"value": "Evan", "modifier": ""}],
        "last name": [{"value": "Harmon", "modifier": ""}],
        "address": [{
            "value": {"street": "128 Indiana Ave", "city": "Wichita Falls", "state": "TX", "zip": "76301"},
            "modifier": "home"
        }]
    }
}
response = requests.post(url, headers=headers, json=payload)
print("Create Contact Status:", response.status_code)
if response.status_code == 200:
    contact_id = response.json().get('id')
    print("Created Contact:", contact_id)
    # Check if it enriched phone
    get_res = requests.get(f"https://app.nimble.com/api/v1/contact/{contact_id}", headers=headers)
    print("Contact Data:", get_res.json())
else:
    print(response.text)
