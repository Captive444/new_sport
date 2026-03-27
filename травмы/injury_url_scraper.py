# scraper/injury_url_scraper.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import time

class InjuryUrlScraper:
    def __init__(self, driver):
        self.driver = driver

    def find_all_injury_urls(self, team_url):
        """Найти все URL страниц травм игроков команды."""
        try:
            self.driver.get(team_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'items'))
            )
            
            # Находим все ссылки на игроков
            player_links = self.driver.find_elements(
                By.XPATH, '//table[contains(@class, "items")]//a[contains(@href, "/profil/spieler/")]'
            )
            
            injury_urls = []
            for link in player_links:
                href = link.get_attribute('href')
                if href:
                    # Извлекаем ID игрока из URL профиля
                    player_id = href.split('/')[-1]
                    # Формируем URL страницы травм
                    injury_url = f"https://www.transfermarkt.world/-/verletzungen/spieler/{player_id}/plus/1"
                    injury_urls.append(injury_url)
                    
            logging.info(f"Найдено {len(injury_urls)} URL для парсинга травм")
            return injury_urls
            
        except Exception as e:
            logging.error(f"Ошибка парсинга URL травм {team_url}: {str(e)}")
            return []