# main_injury_parser.py

"""
ГЛАВНЫЙ МОДУЛЬ ПАРСЕРА ТРАВМ TRANSFERMARKT
===========================================
Собирает историю травм футболистов из указанных команд
"""

import json
import logging
import os
import sys
import time
import random
import traceback
from datetime import datetime
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from database import Database
from utils.logger import setup_logger
from scraper.transfermarkt_injury_spider import TransfermarktInjurySpider
from scraper.base_scraper import BaseScraper
from scraper.injury_url_scraper import InjuryUrlScraper

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
ERROR_LOG_FILE = "failed_teams_injuries.log"
COMPETITIONS_DIR = "competitions"
INJURIES_DIR = "injuries"  # Новая папка для данных о травмах
OUTPUT_INJURY_JSON = "output_injuries.json"

# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ
# =============================================================================

def save_injury_urls_to_json(urls):
    """Сохраняет список URL травм во временный JSON файл"""
    try:
        with open(OUTPUT_INJURY_JSON, 'w', encoding='utf-8') as f:
            json.dump(urls, f, ensure_ascii=False, indent=4)
        logging.info(f"Сохранено {len(urls)} URL травм в {OUTPUT_INJURY_JSON}")
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения URL травм: {str(e)}")
        return False

def create_injury_folder(home_team, away_team):
    """Создает структуру папок для хранения данных о травмах"""
    folder_name = f"{clean_filename(home_team)} - {clean_filename(away_team)}"
    
    if not os.path.exists(INJURIES_DIR):
        os.makedirs(INJURIES_DIR)
        logging.info(f"Создана основная папка: {INJURIES_DIR}")
    
    match_dir = os.path.join(INJURIES_DIR, folder_name)
    if not os.path.exists(match_dir):
        os.makedirs(match_dir)
        logging.info(f"Создана папка матча: {match_dir}")
    
    return match_dir

def clean_filename(name):
    """Очищает название от недопустимых символов"""
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '')
    return name.strip()

def log_failed_team(team_name, error_msg):
    """Записывает информацию о команде, которую не удалось обработать"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {team_name} | {error_msg}\n")
        logging.warning(f"Команда {team_name} добавлена в список упавших")
    except Exception as e:
        logging.error(f"Не удалось записать в лог ошибок: {str(e)}")

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

def get_all_matches_from_competitions():
    """Собирает все матчи из папки competitions"""
    all_matches = []
    
    if not os.path.exists(COMPETITIONS_DIR):
        logging.error(f"Папка {COMPETITIONS_DIR} не существует")
        return all_matches
    
    for root, dirs, files in os.walk(COMPETITIONS_DIR):
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

# =============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ПАРСИНГА ТРАВМ
# =============================================================================

@defer.inlineCallbacks
def process_team_injuries(team_name, match_folder, runner, retry_count=0):
    """
    Асинхронно обрабатывает травмы игроков одной команды
    """
    logging.info(f"{'='*40}")
    logging.info(f"ОБРАБОТКА ТРАВМ КОМАНДЫ: {team_name}")
    if retry_count > 0:
        logging.info(f"Попытка #{retry_count}")
    logging.info(f"{'='*40}")
    
    max_internal_retries = 3
    
    for attempt in range(max_internal_retries):
        try:
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
            # Получаем URL команды
            team_url = get_team_url_from_db(team_name)
            if not team_url:
                error_msg = "URL команды не найден в базе данных"
                log_failed_team(team_name, error_msg)
                defer.returnValue(False)

            # Запускаем Selenium для сбора URL страниц травм
            scraper = BaseScraper()
            try:
                injury_scraper = InjuryUrlScraper(scraper.driver)
                
                # Получаем URL страниц травм для всех игроков
                injury_urls = injury_scraper.find_all_injury_urls(team_url)
                
                if not injury_urls:
                    error_msg = f"Не найдено URL травм (попытка {attempt + 1})"
                    logging.warning(error_msg)
                    
                    if attempt < max_internal_retries - 1:
                        wait_time = 10 * (attempt + 1)
                        logging.info(f"Ждем {wait_time} сек перед следующей попыткой...")
                        time.sleep(wait_time)
                        continue
                    else:
                        log_failed_team(team_name, "Нет URL травм после всех попыток")
                        defer.returnValue(False)

                # Сохраняем URL травм во временный файл
                if save_injury_urls_to_json(injury_urls):
                    # Запускаем Scrapy паука для парсинга травм
                    logging.info(f"🚀 Запуск парсинга травм игроков: {team_name}")
                    yield runner.crawl(
                        TransfermarktInjurySpider, 
                        team_name=team_name, 
                        match_folder=match_folder
                    )
                    
                    logging.info(f"✅ Травмы команды {team_name} успешно обработаны")
                    defer.returnValue(True)
                else:
                    error_msg = "Ошибка сохранения URL травм в JSON"
                    log_failed_team(team_name, error_msg)
                    defer.returnValue(False)
                    
            except Exception as e:
                error_msg = f"Ошибка парсинга: {str(e)}"
                logging.error(error_msg)
                logging.debug(traceback.format_exc())
                
                if attempt < max_internal_retries - 1:
                    logging.info(f"Повторная попытка {attempt + 2}/{max_internal_retries}")
                    time.sleep(15 * (attempt + 1))
                else:
                    log_failed_team(team_name, f"{error_msg}\n{traceback.format_exc()}")
                    defer.returnValue(False)
            finally:
                scraper.close_driver()
                
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            logging.error(error_msg)
            logging.debug(traceback.format_exc())
            
            if attempt == max_internal_retries - 1:
                log_failed_team(team_name, error_msg)
                defer.returnValue(False)
    
    defer.returnValue(False)

@defer.inlineCallbacks
def process_match_injuries(match, match_index, runner):
    """
    Асинхронно обрабатывает травмы игроков для одного матча
    """
    home_team = match.get('home_team', '').strip()
    away_team = match.get('away_team', '').strip()
    
    if not home_team or not away_team:
        logging.error(f"Матч #{match_index}: отсутствует название команды")
        defer.returnValue(False)
    
    logging.info(f"\n{'#'*60}")
    logging.info(f"МАТЧ #{match_index}: {home_team} vs {away_team} (ТРАВМЫ)")
    logging.info(f"{'#'*60}")
    
    match_folder = create_injury_folder(home_team, away_team)
    
    # Обрабатываем домашнюю команду
    logging.info(f"\n🏠 ДОМАШНЯЯ КОМАНДА: {home_team}")
    success_home = yield process_team_injuries(home_team, match_folder, runner)
    
    if success_home:
        time.sleep(random.uniform(2, 5))
    
    # Обрабатываем гостевую команду
    logging.info(f"\n✈️ ГОСТЕВАЯ КОМАНДА: {away_team}")
    success_away = yield process_team_injuries(away_team, match_folder, runner)
    
    if success_home and success_away:
        logging.info(f"\n✅ МАТЧ #{match_index} ПОЛНОСТЬЮ ОБРАБОТАН")
    else:
        logging.warning(f"\n⚠️ МАТЧ #{match_index} ОБРАБОТАН ЧАСТИЧНО")
        if not success_home:
            logging.warning(f"   • Не обработана: {home_team}")
        if not success_away:
            logging.warning(f"   • Не обработана: {away_team}")
    
    defer.returnValue(success_home and success_away)

# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

@defer.inlineCallbacks
def main():
    """
    ГЛАВНАЯ ФУНКЦИЯ ПАРСЕРА ТРАВМ
    """
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    setup_logger()
    configure_logging()
    
    if os.path.exists(ERROR_LOG_FILE):
        os.remove(ERROR_LOG_FILE)
        logging.info(f"Очищен файл лога ошибок: {ERROR_LOG_FILE}")
    
    logging.info("\n" + "🏥"*10)
    logging.info("ЗАПУСК ПАРСЕРА ТРАВМ TRANSFERMARKT")
    logging.info("🏥"*10 + "\n")
    
    runner = CrawlerRunner()
    
    all_matches = get_all_matches_from_competitions()
    if not all_matches:
        logging.error("Нет матчей для обработки. Проверьте папку competitions.")
        reactor.stop()
        return
    
    logging.info(f"\n📋 Найдено матчей для обработки: {len(all_matches)}")
    
    successful_matches = 0
    start_time = datetime.now()
    
    for i, match in enumerate(all_matches, 1):
        try:
            success = yield process_match_injuries(match, i, runner)
            if success:
                successful_matches += 1
            
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / i if i > 0 else 0
            remaining = avg_time * (len(all_matches) - i)
            
            logging.info(f"\n📊 ПРОГРЕСС: {i}/{len(all_matches)} матчей")
            logging.info(f"   ✅ Успешно: {successful_matches}")
            logging.info(f"   ⏱️  Среднее время на матч: {avg_time:.1f} сек")
            logging.info(f"   ⏳ Осталось примерно: {remaining/60:.1f} мин")
            
        except Exception as e:
            logging.error(f"Критическая ошибка при обработке матча #{i}: {str(e)}")
            logging.debug(traceback.format_exc())
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    logging.info(f"\n{'='*60}")
    logging.info("ЗАВЕРШЕНИЕ РАБОТЫ")
    logging.info(f"{'='*60}")
    logging.info(f"📊 Общее время работы: {total_time/60:.1f} минут")
    logging.info(f"✅ Успешно обработано матчей: {successful_matches}/{len(all_matches)}")
    logging.info(f"📁 Данные сохранены в папке: {INJURIES_DIR}")
    
    reactor.stop()

if __name__ == '__main__':
    try:
        main()
        reactor.run()
    except KeyboardInterrupt:
        logging.info("\n⚠️ Программа остановлена пользователем")
        reactor.stop()
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        logging.debug(traceback.format_exc())
        reactor.stop()