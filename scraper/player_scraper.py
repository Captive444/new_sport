# scraper/player_scraper.py
# scraper/player_scraper.py
# scraper/player_scraper.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

class PlayerScraper:
    def __init__(self, driver):
        self.driver = driver

    def find_all_urls(self, url):
        """Найти все URL игроков на странице команды."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'items'))
            )
            
            player_links = self.driver.find_elements(
                By.XPATH, '//table[contains(@class, "items")]//a[contains(@href, "/profil/spieler/")]'
            )
            
            return [
                f"https://www.transfermarkt.world/-/leistungsdaten/spieler/{link.get_attribute('href').split('/')[-1]}/plus/1#gesamt"
                for link in player_links if link.get_attribute('href')
            ]
        except Exception as e:
            logging.error(f"Ошибка парсинга {url}: {str(e)}")
            return []



