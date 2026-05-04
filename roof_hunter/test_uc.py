import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup

def main():
    options = uc.ChromeOptions()
    options.headless = True
    # headless might still get detected, let's just try headless=True first
    driver = uc.Chrome(options=options)
    
    url = "https://www.truepeoplesearch.com/resultaddress?streetaddress=128%20Indiana%20Ave&citystatezip=Wichita%20Falls,%20TX%2076301"
    driver.get(url)
    time.sleep(5)
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string if soup.title else "No title"
    print("Title:", title)
    
    if "Cloudflare" in html or "verify you are human" in html.lower():
        print("Blocked by Cloudflare")
    else:
        phones = set()
        for a in soup.find_all('a', href=True):
            if a['href'].startswith('tel:'):
                phones.add(a.text.strip())
        print("Phones:", phones)
        
    driver.quit()

if __name__ == '__main__':
    main()
