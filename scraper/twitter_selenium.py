import os
import uuid
from datetime import datetime
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent


# for testing purpose only
DEFAULT_TWITTER_EMAIL = "anonymous798205"
DEFAULT_TWITTER_PASSWORD = "abcd@123"
DEFAULT_MONGO_URI = "mongodb://localhost:27017/"

TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", DEFAULT_TWITTER_EMAIL)
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", DEFAULT_TWITTER_PASSWORD)
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)

PROXY_URL = "fr.proxymesh.com:31280"

class TwitterScraper:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client['twitter_trends']
        self.collection = self.db['trending_topics']

    def setup_driver(self):
        try:
            user_agent = UserAgent().random
        except:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={user_agent}')

        return webdriver.Chrome(options=chrome_options)

    def login_to_twitter(self, driver):
        try:
            driver.get('https://twitter.com/login')
            wait = WebDriverWait(driver, 20)
            
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "text")))
            email_field.send_keys(TWITTER_EMAIL)
            driver.find_element(By.XPATH, "//span[text()='Next']").click()
            
            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.send_keys(TWITTER_PASSWORD)
            driver.find_element(By.XPATH, "//span[text()='Log in']").click()
          
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']")))
        except TimeoutException as e:
            raise Exception(f"Login failed: {str(e)}")

    def extract_trend_info(self, trend_element):
        try:
            spans = trend_element.find_elements(By.CSS_SELECTOR, "span")
            
            category = "Trending" 
            title = ""
            posts_count = ""
            
            texts = [span.text for span in spans if span.text.strip()]
            
            for i, text in enumerate(texts):
                if '·' in text:
                    category = text.replace(' · ', ', ')
                elif 'posts' in text.lower() or 'k' in text.lower():
                    posts_count = text
                else:
                    title = text

            return {
                'category': category,
                'title': title,
                'posts_count': posts_count
            }
        except Exception as e:
            print(f"Error extracting trend info: {str(e)}")
            return {
                'category': 'N/A',
                'title': 'N/A',
                'posts_count': 'N/A'
            }

    def get_trending_topics(self, driver):
        try:
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='trend']")))
            
            trends = driver.find_elements(By.CSS_SELECTOR, "[data-testid='trend']")
            trend_details = []
            
            for trend in trends[:5]: 
                trend_info = self.extract_trend_info(trend)
                trend_details.append(trend_info)
    
            return trend_details
        except TimeoutException as e:
            raise Exception(f"Failed to fetch trending topics: {str(e)}")

    def get_ip_address(self, driver):
        driver.get("https://api.ipify.org?format=json")
        return driver.find_element(By.TAG_NAME, "body").text

    def store_in_mongodb(self, unique_id, trends, ip_address):
        document = {
            '_id': unique_id,
            'trends': [
                {
                    'category': trend['category'],
                    'title': trend['title'],
                    'posts_count': trend['posts_count']
                }
                for trend in trends[:5]
            ],
            'date_time': datetime.now(),
            'ip_address': ip_address
        }
        self.collection.insert_one(document)
        return document

    def scrape_twitter(self):
        driver = None
        try:
            driver = self.setup_driver()
            self.login_to_twitter(driver)
            trends = self.get_trending_topics(driver)
            ip_address = self.get_ip_address(driver)
            unique_id = str(uuid.uuid4())
            result = self.store_in_mongodb(unique_id, trends, ip_address)
            return result
        except Exception as e:
            raise Exception(f"Scraping failed: {str(e)}")
        finally:
            if driver:
                driver.quit()

if __name__ == "__main__":
    scraper = TwitterScraper()
    try:
        result = scraper.scrape_twitter()
        print("Scraping Successful!")
        print("\nTrending Topics:")
        for i, trend in enumerate(result['trends'], 1):
            print(f"\nTrend {i}:")
            print(f"Category: {trend['category']}")
            print(f"Title: {trend['title']}")
            print(f"Posts: {trend['posts_count']}")
    except Exception as e:
        print(f"Error: {str(e)}")