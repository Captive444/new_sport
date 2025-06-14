# scraper/base_scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

class BaseScraper:
    def __init__(self):
        self.driver = self.init_driver()

    def init_driver(self):
        """Инициализация веб-драйвера."""
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver

    def close_driver(self):
        """Закрыть драйвер."""
        self.driver.quit()


