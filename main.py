import json
import logging
from database import Database
from utils.logger import setup_logger
from scrapy.crawler import CrawlerProcess
from scraper.transfermarkt_spider import TransfermarktSpider
from scraper.base_scraper import BaseScraper
from scraper.team_scraper import TeamScraper
from scraper.player_scraper import PlayerScraper

def get_player_urls_from_db(team_name):
    """Получает URL игроков команды из базы данных"""
    db = Database()
    try:
        with db.conn.cursor() as cursor:
            # Получаем team_id по названию команды
            cursor.execute(
                "SELECT team_id FROM Teams WHERE team_name = %s",
                (team_name,)
            )
            team = cursor.fetchone()
            
            if not team:
                logging.error(f"Команда '{team_name}' не найдена в базе данных")
                return None
            
            # Получаем URL игроков этой команды
            cursor.execute(
                """SELECT player_id, transfermarkt_url 
                FROM Players 
                WHERE team_id = %s AND transfermarkt_url IS NOT NULL""",
                (team[0],)
            )
            result = cursor.fetchall()
            
            if not result:
                logging.error(f"Не найдено игроков для команды '{team_name}'")
                return None
            
            # Преобразуем результат в список URL
            urls = [url for (player_id, url) in result]
            logging.info(f"Найдено {len(urls)} игроков для команды {team_name}")
            return urls
            
    except Exception as e:
        logging.error(f"Ошибка получения URL игроков из БД: {str(e)}")
        return None
    finally:
        db.close()

def save_urls_to_json(urls, filename='output.json'):
    """Сохраняет список URL в JSON файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(urls, f, ensure_ascii=False, indent=4)
        logging.info(f"URL успешно сохранены в {filename}")
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения в JSON: {str(e)}")
        return False

def run_transfermarkt_spider():
    """Запускает паука TransfermarktSpider для сбора статистики игроков"""
    process = CrawlerProcess()
    process.crawl(TransfermarktSpider)
    process.start()

def parse_team_and_players(team_name):
    """Парсит информацию о команде и игроках, если команда не найдена в БД"""
    db = Database()
    scraper = BaseScraper()
    
    try:
        team_scraper = TeamScraper(scraper.driver)
        input_team_name, team_url = team_scraper.find_team_url(team_name)
        if not team_url:
            return None

        # Сохранение команды в БД
        team_id = db.save_team(team_name, team_url)
        if not team_id:
            return None

        # Парсинг игроков
        player_scraper = PlayerScraper(scraper.driver)
        player_urls = player_scraper.find_all_urls(team_url)
        logging.info(f"Найдено игроков: {len(player_urls)} для команды {team_name}")

        # Сохранение игроков
        for url in player_urls:
            db.save_player(team_id, url)

        return player_urls
            
    finally:
        scraper.close_driver()
        db.close()
        logging.info("Парсинг завершен")

def main():
    """Основная функция для получения URL игроков из БД или парсинга"""
    setup_logger()
    team_name = input("Введите название команды: ").strip()
    
    if not team_name:
        logging.error("Не указано название команды")
        return

    # Получаем URL из базы данных
    player_urls = get_player_urls_from_db(team_name)
    
    if not player_urls:
        # Если не нашли URL, начинаем парсинг команды и игроков
        player_urls = parse_team_and_players(team_name)
    
    if player_urls:
        # Сохраняем в JSON
        if save_urls_to_json(player_urls):
            # Запускаем паука для сбора статистики
            run_transfermarkt_spider()

if __name__ == '__main__':
    print("Получение URL игроков из базы данных или парсинг новой команды")
    main()
