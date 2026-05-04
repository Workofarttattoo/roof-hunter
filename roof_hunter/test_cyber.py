from curl_cffi import requests

url = 'https://www.cyberbackgroundchecks.com/address/128-indiana-ave/wichita-falls/tx/76301'
response = requests.get(url, impersonate="chrome110")
print("Status:", response.status_code)
if response.status_code == 200:
    print("Length:", len(response.text))
    if "Cloudflare" in response.text:
        print("But it's Cloudflare")
    else:
        print("Bypassed!")
