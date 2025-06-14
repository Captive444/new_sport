# scraper/team_scraper.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import time

class TeamScraper:
    def __init__(self, driver):
        self.driver = driver

    def find_team_url(self, team_name):
        """Найти URL команды по названию."""
        try:
            self.driver.get("https://www.transfermarkt.com")
            time.sleep(2)  # Ожидание загрузки страницы

            # Принять куки, если появилось окно
            try:
                cookie_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
                )
                cookie_btn.click()
                time.sleep(1)
            except:
                pass

            # Поиск команды
            search_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//input[@name="query"]'))
            )
            search_input.clear()
            search_input.send_keys(team_name)
            search_input.submit()
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//table[@class="items"]//td[@class="hauptlink"]/a'))
            )
            
            first_result = self.driver.find_element(By.XPATH, '//table[@class="items"]//td[@class="hauptlink"]/a')
            team_url = first_result.get_attribute('href')
            found_name = first_result.text.strip()
            
            logging.info(f"Найдена команда: {found_name} ({team_url})")
            
            return team_name, team_url  # Возвращаем исходное название команды, а не найденное
        except Exception as e:
            logging.error(f"Ошибка при поиске команды '{team_name}': {e}")
            return None, None

