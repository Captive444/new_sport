import json
import logging
import os
import sys
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from database import Database
from utils.logger import setup_logger
from scraper.transfermarkt_spider import TransfermarktSpider
from scraper.base_scraper import BaseScraper
from scraper.player_scraper import PlayerScraper

def get_team_url_from_db(team_name):
    """Получает URL команды из базы данных"""
    db = Database()
    try:
        with db.conn.cursor() as cursor:
            cursor.execute(
                "SELECT team_url FROM Teams WHERE team_name = %s",
                (team_name,)
            )
            team = cursor.fetchone()
            
            if not team:
                logging.error(f"Команда '{team_name}' не найдена в базе данных")
                return None
            
            logging.info(f"Найден URL команды: {team[0]}")
            return team[0]
            
    except Exception as e:
        logging.error(f"Ошибка получения URL команды: {str(e)}")
        return None
    finally:
        db.close()

def save_urls_to_json(urls):
    """Сохраняет список URL в JSON файл (перезаписывает)"""
    try:
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(urls, f, ensure_ascii=False, indent=4)
        logging.info(f"Сохранено {len(urls)} URL в output.json")
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения URL: {str(e)}")
        return False

def get_all_matches_from_competitions():
    """Получает все матчи из папки competitions"""
    competitions_dir = "competitions"
    all_matches = []
    
    if not os.path.exists(competitions_dir):
        logging.error(f"Папка {competitions_dir} не существует")
        return all_matches
    
    for root, dirs, files in os.walk(competitions_dir):
        for filename in files:
            if filename.endswith('.json') and 'upcoming_matches' in filename:
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for match in data.get('matches', []):
                        all_matches.append(match)
                        logging.info(f"Матч: {match['home_team']} vs {match['away_team']}")
                            
                except Exception as e:
                    logging.error(f"Ошибка чтения {filename}: {str(e)}")
    
    logging.info(f"Всего матчей: {len(all_matches)}")
    return all_matches

def create_match_folder(home_team, away_team):
    """Создает папку для матча"""
    def clean_name(name):
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip()
    
    folder_name = f"{clean_name(home_team)} - {clean_name(away_team)}"
    
    commands_dir = "commands"
    if not os.path.exists(commands_dir):
        os.makedirs(commands_dir)
    
    match_dir = os.path.join(commands_dir, folder_name)
    if not os.path.exists(match_dir):
        os.makedirs(match_dir)
        logging.info(f"Создана папка: {match_dir}")
    
    return match_dir

@defer.inlineCallbacks
def process_team(team_name, match_folder, runner):
    """Обрабатывает одну команду асинхронно"""
    logging.info(f"Обработка команды: {team_name}")
    
    # 1. Получаем URL команды из БД
    team_url = get_team_url_from_db(team_name)
    if not team_url:
        defer.returnValue(False)

    # 2. Получаем URL игроков
    scraper = BaseScraper()
    try:
        player_scraper = PlayerScraper(scraper.driver)
        player_urls = player_scraper.find_all_urls(team_url)
        
        if not player_urls:
            logging.error(f"Не найдено игроков для {team_name}")
            defer.returnValue(False)

        # 3. Сохраняем URLы
        if save_urls_to_json(player_urls):
            # 4. Запускаем парсинг асинхронно
            logging.info(f"Запуск парсинга: {team_name}")
            yield runner.crawl(TransfermarktSpider, team_name=team_name, match_folder=match_folder)
            defer.returnValue(True)
        else:
            defer.returnValue(False)
            
    except Exception as e:
        logging.error(f"Ошибка парсинга {team_name}: {str(e)}")
        defer.returnValue(False)
    finally:
        scraper.close_driver()

@defer.inlineCallbacks
def process_match(match, match_index, runner):
    """Обрабатывает один матч асинхронно"""
    home_team = match.get('home_team', '').strip()
    away_team = match.get('away_team', '').strip()
    
    if not home_team or not away_team:
        defer.returnValue(False)
    
    logging.info(f"\n" + "="*50)
    logging.info(f"МАТЧ {match_index}: {home_team} vs {away_team}")
    logging.info("="*50)
    
    # Создаем папку для матча
    match_folder = create_match_folder(home_team, away_team)
    
    # Обрабатываем домашнюю команду
    success_home = yield process_team(home_team, match_folder, runner)
    
    # Обрабатываем гостевую команду  
    success_away = yield process_team(away_team, match_folder, runner)
    
    defer.returnValue(success_home and success_away)

@defer.inlineCallbacks
def main():
    """Основная асинхронная функция"""
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    setup_logger()
    configure_logging()
    
    logging.info("ЗАПУСК ПАРСИНГА")
    
    # Создаем runner
    runner = CrawlerRunner()
    
    # Получаем все матчи
    all_matches = get_all_matches_from_competitions()
    if not all_matches:
        return
    
    # Обрабатываем матчи по очереди
    successful_matches = 0
    
    for i, match in enumerate(all_matches, 1):
        success = yield process_match(match, i, runner)
        if success:
            successful_matches += 1
    
    # Итоги
    logging.info(f"\n" + "="*50)
    logging.info(f"ЗАВЕРШЕНО: {successful_matches}/{len(all_matches)} матчей")
    
    # Останавливаем реактор
    reactor.stop()

if __name__ == '__main__':
    main()
    reactor.run()

    