# main.py
import logging
from utils.logger import setup_logger
from database import Database
from scraper.base_scraper import BaseScraper
from scraper.team_scraper import TeamScraper
from scraper.player_scraper import PlayerScraper
# 22


def main_parser():
    """Основная функция парсинга."""
    setup_logger()

    team_name = input("Введите название команды для парсинга: ").strip()
    if not team_name:
        logging.error("Не указано название команды")
        return

    # Инициализация базы данных и веб-драйвера
    db = Database()
    scraper = BaseScraper()
    
    try:
        team_scraper = TeamScraper(scraper.driver)
        input_team_name, team_url = team_scraper.find_team_url(team_name)
        if not team_url:
            return

        # Сохранение команды в БД
        team_id = db.save_team(team_name, team_url)
        if not team_id:
            return

        # Парсинг игроков
        player_scraper = PlayerScraper(scraper.driver)
        player_urls = player_scraper.find_all_urls(team_url)
        logging.info(f"Найдено игроков: {len(player_urls)} для команды {team_name}")

        # Сохранение игроков
        for url in player_urls:
            db.save_player(team_id, url)
            
    finally:
        scraper.close_driver()
        db.close()
        logging.info("Парсинг завершен")

if __name__ == '__main__':
    main_parser()

