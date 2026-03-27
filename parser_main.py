"""
ГЛАВНЫЙ МОДУЛЬ ПАРСЕРА TRANSFERMARKT
=====================================
Основной orchestrator, который:
1. Собирает все матчи из папки competitions
2. Для каждого матча обрабатывает обе команды
3. Получает URL команд из базы данных
4. Собирает ссылки на игроков
5. Запускает Scrapy паука для парсинга статистики
6. Сохраняет результаты в структурированные папки
7. Отслеживает ошибки и позволяет повторно обработать упавшие команды
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
from scraper.transfermarkt_spider import TransfermarktSpider
from scraper.base_scraper import BaseScraper
from scraper.player_scraper import PlayerScraper

# =============================================================================
# КОНСТАНТЫ И ГЛОБАЛЬНЫЕ НАСТРОЙКИ
# =============================================================================
ERROR_LOG_FILE = "failed_teams.log"  # Файл для логирования упавших команд
COMPETITIONS_DIR = "competitions"     # Папка с файлами соревнований
COMMANDS_DIR = "commands"             # Папка для сохранения результатов
OUTPUT_JSON = "output.json"            # Временный файл для URL игроков

# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# =============================================================================

def get_team_url_from_db(team_name):
    """
    Получает URL команды из базы данных по её названию.
    
    Аргументы:
        team_name (str): Название команды для поиска
        
    Возвращает:
        str или None: URL команды на Transfermarkt или None если не найдена
        
    Логика:
        1. Подключается к базе данных
        2. Выполняет SQL запрос для поиска команды
        3. Возвращает URL или None с соответствующим логированием
    """
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
        db.close()  # Важно всегда закрывать соединение

# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ
# =============================================================================

def save_urls_to_json(urls):
    """
    Сохраняет список URL игроков во временный JSON файл.
    Файл перезаписывается при каждом вызове.
    
    Аргументы:
        urls (list): Список URL страниц игроков
        
    Возвращает:
        bool: True если сохранение успешно, False при ошибке
        
    Назначение:
        Создает промежуточный файл, который будет использован
        Scrapy пауком для последовательного парсинга игроков
    """
    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(urls, f, ensure_ascii=False, indent=4)
        logging.info(f"Сохранено {len(urls)} URL в {OUTPUT_JSON}")
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения URL: {str(e)}")
        return False

def get_all_matches_from_competitions():
    """
    Сканирует папку competitions и собирает все предстоящие матчи
    из всех файлов JSON.
    
    Возвращает:
        list: Список словарей с информацией о матчах.
              Каждый словарь содержит 'home_team' и 'away_team'
    
    Логика работы:
        1. Рекурсивно обходит все папки внутри competitions
        2. Ищет файлы, содержащие 'upcoming_matches' в имени
        3. Из каждого файла извлекает список матчей
        4. Добавляет все матчи в общий список
    """
    all_matches = []
    
    if not os.path.exists(COMPETITIONS_DIR):
        logging.error(f"Папка {COMPETITIONS_DIR} не существует")
        return all_matches
    
    # os.walk рекурсивно обходит все подпапки
    for root, dirs, files in os.walk(COMPETITIONS_DIR):
        for filename in files:
            if filename.endswith('.json') and 'upcoming_matches' in filename:
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Извлекаем матчи из поля 'matches' (если оно есть)
                    for match in data.get('matches', []):
                        all_matches.append(match)
                        logging.info(f"Матч: {match['home_team']} vs {match['away_team']}")
                            
                except Exception as e:
                    logging.error(f"Ошибка чтения {filename}: {str(e)}")
    
    logging.info(f"Всего матчей: {len(all_matches)}")
    return all_matches

def clean_filename(name):
    """
    Очищает название команды от недопустимых символов для имени папки.
    
    Аргументы:
        name (str): Исходное название команды
        
    Возвращает:
        str: Очищенное название, безопасное для использования в пути файла
        
    Поддерживает кроссплатформенность:
        Удаляет символы, запрещенные в Windows, Linux и macOS
    """
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '')
    return name.strip()

def create_match_folder(home_team, away_team):
    """
    Создает структуру папок для хранения результатов матча.
    
    Аргументы:
        home_team (str): Название домашней команды
        away_team (str): Название гостевой команды
        
    Возвращает:
        str: Путь к созданной папке матча
    
    Структура:
        commands/
          └── {home_team} - {away_team}/
              ├── {home_team}.json  # Данные домашней команды
              └── {away_team}.json  # Данные гостевой команды
    """
    folder_name = f"{clean_filename(home_team)} - {clean_filename(away_team)}"
    
    # Создаем основную папку commands если её нет
    if not os.path.exists(COMMANDS_DIR):
        os.makedirs(COMMANDS_DIR)
        logging.info(f"Создана основная папка: {COMMANDS_DIR}")
    
    # Создаем папку для конкретного матча
    match_dir = os.path.join(COMMANDS_DIR, folder_name)
    if not os.path.exists(match_dir):
        os.makedirs(match_dir)
        logging.info(f"Создана папка матча: {match_dir}")
    
    return match_dir

def log_failed_team(team_name, error_msg):
    """
    Записывает информацию о команде, которую не удалось обработать,
    в специальный лог-файл для последующего повтора.
    
    Аргументы:
        team_name (str): Название команды
        error_msg (str): Описание ошибки
        
    Формат записи:
        timestamp | team_name | error_message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {team_name} | {error_msg}\n")
        logging.warning(f"Команда {team_name} добавлена в список упавших")
    except Exception as e:
        logging.error(f"Не удалось записать в лог ошибок: {str(e)}")

def read_failed_teams():
    """
    Читает список упавших команд из лог-файла.
    
    Возвращает:
        list: Список уникальных названий команд, которые не удалось обработать
        
    Используется для повторной обработки команд после основного цикла
    """
    failed_teams = set()  # Используем set для автоматического удаления дубликатов
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            team_name = parts[1].strip()
                            if team_name:  # Проверяем, что название не пустое
                                failed_teams.add(team_name)
    except Exception as e:
        logging.error(f"Ошибка чтения файла ошибок: {str(e)}")
    
    return list(failed_teams)

def print_final_summary(successful_matches, total_matches):
    """
    Выводит итоговую сводку по результатам парсинга.
    
    Аргументы:
        successful_matches (int): Количество успешно обработанных матчей
        total_matches (int): Общее количество матчей
    """
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    print(f"✅ Успешно обработано: {successful_matches}/{total_matches} матчей")
    
    # Проверяем, есть ли упавшие команды
    failed_teams = read_failed_teams()
    if failed_teams:
        print(f"❌ Проваленные команды ({len(failed_teams)}):")
        for team in sorted(failed_teams)[:10]:  # Показываем первые 10
            print(f"   • {team}")
        if len(failed_teams) > 10:
            print(f"   • ... и еще {len(failed_teams) - 10}")
        print(f"\n📄 Полный список сохранен в: {ERROR_LOG_FILE}")
        print(f"💡 Для повторной обработки запустите: python retry_failed.py")
    else:
        print("🎉 Все команды успешно обработаны!")
    print("="*60)

# =============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ПАРСИНГА (ASYNC)
# =============================================================================

@defer.inlineCallbacks
def process_team(team_name, match_folder, runner, retry_count=0):
    """
    Асинхронно обрабатывает одну команду.
    
    Аргументы:
        team_name (str): Название команды для обработки
        match_folder (str): Путь к папке матча для сохранения результатов
        runner (CrawlerRunner): Экземпляр Scrapy runner
        retry_count (int): Номер текущей попытки (для логирования)
        
    Возвращает:
        bool: True если обработка успешна, False при ошибке
    
    Алгоритм работы:
        1. Получает URL команды из БД
        2. Запускает Selenium для сбора ссылок на игроков
        3. Сохраняет ссылки во временный JSON
        4. Запускает Scrapy паука для парсинга каждого игрока
        5. При ошибках логирует команду для повторной обработки
    """
    logging.info(f"{'='*40}")
    logging.info(f"ОБРАБОТКА КОМАНДЫ: {team_name}")
    if retry_count > 0:
        logging.info(f"Попытка #{retry_count}")
    logging.info(f"{'='*40}")
    
    # Защита от бесконечных повторений внутри одной функции
    max_internal_retries = 3
    
    for attempt in range(max_internal_retries):
        try:
            # Добавляем случайную задержку перед запросом к БД
            # Это снижает нагрузку и делает поведение более человеческим
            delay = random.uniform(1, 3)
            time.sleep(delay)
            
            # ШАГ 1: Получаем URL команды из базы данных
            team_url = get_team_url_from_db(team_name)
            if not team_url:
                error_msg = "URL команды не найден в базе данных"
                log_failed_team(team_name, error_msg)
                defer.returnValue(False)

            # ШАГ 2: Запускаем Selenium для сбора ссылок на игроков
            scraper = BaseScraper()
            try:
                player_scraper = PlayerScraper(scraper.driver)
                
                # Пытаемся получить ссылки на игроков
                player_urls = player_scraper.find_all_urls(team_url)
                
                if not player_urls:
                    error_msg = f"Не найдено игроков (попытка {attempt + 1})"
                    logging.warning(error_msg)
                    
                    # Если это не последняя попытка, пробуем снова
                    if attempt < max_internal_retries - 1:
                        wait_time = 10 * (attempt + 1)
                        logging.info(f"Ждем {wait_time} сек перед следующей попыткой...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Если все попытки исчерпаны, логируем ошибку
                        log_failed_team(team_name, "Нет игроков после всех попыток")
                        defer.returnValue(False)

                # ШАГ 3: Сохраняем URL игроков во временный файл
                if save_urls_to_json(player_urls):
                    # ШАГ 4: Запускаем Scrapy паука для асинхронного парсинга
                    logging.info(f"🚀 Запуск парсинга игроков: {team_name}")
                    yield runner.crawl(
                        TransfermarktSpider, 
                        team_name=team_name, 
                        match_folder=match_folder
                    )
                    
                    logging.info(f"✅ Команда {team_name} успешно обработана")
                    defer.returnValue(True)
                else:
                    error_msg = "Ошибка сохранения URL в JSON"
                    log_failed_team(team_name, error_msg)
                    defer.returnValue(False)
                    
            except Exception as e:
                error_msg = f"Ошибка парсинга: {str(e)}"
                logging.error(error_msg)
                logging.debug(traceback.format_exc())  # Полный traceback для отладки
                
                if attempt < max_internal_retries - 1:
                    logging.info(f"Повторная попытка {attempt + 2}/{max_internal_retries}")
                    time.sleep(15 * (attempt + 1))  # Увеличиваем паузу с каждой попыткой
                else:
                    log_failed_team(team_name, f"{error_msg}\n{traceback.format_exc()}")
                    defer.returnValue(False)
            finally:
                # ВАЖНО: Всегда закрываем драйвер Selenium
                scraper.close_driver()
                
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            logging.error(error_msg)
            logging.debug(traceback.format_exc())
            
            if attempt == max_internal_retries - 1:
                log_failed_team(team_name, error_msg)
                defer.returnValue(False)
    
    # Если мы дошли до сюда, значит все попытки исчерпаны
    defer.returnValue(False)

@defer.inlineCallbacks
def process_match(match, match_index, runner):
    """
    Асинхронно обрабатывает один матч (обе команды).
    
    Аргументы:
        match (dict): Словарь с информацией о матче (home_team, away_team)
        match_index (int): Номер матча в общем списке
        runner (CrawlerRunner): Экземпляр Scrapy runner
        
    Возвращает:
        bool: True если обе команды обработаны успешно, иначе False
    
    Логика:
        1. Создает папку для матча
        2. Последовательно обрабатывает домашнюю команду
        3. Последовательно обрабатывает гостевую команду
        4. Возвращает результат (успех только если обе команды обработаны)
    """
    # Извлекаем и очищаем названия команд
    home_team = match.get('home_team', '').strip()
    away_team = match.get('away_team', '').strip()
    
    if not home_team or not away_team:
        logging.error(f"Матч #{match_index}: отсутствует название команды")
        defer.returnValue(False)
    
    # Красивое оформление в логах
    logging.info(f"\n{'#'*60}")
    logging.info(f"МАТЧ #{match_index}: {home_team} vs {away_team}")
    logging.info(f"{'#'*60}")
    
    # Создаем папку для хранения результатов этого матча
    match_folder = create_match_folder(home_team, away_team)
    
    # Обрабатываем домашнюю команду
    logging.info(f"\n🏠 ДОМАШНЯЯ КОМАНДА: {home_team}")
    success_home = yield process_team(home_team, match_folder, runner)
    
    # Небольшая пауза между обработкой команд
    if success_home:
        time.sleep(random.uniform(2, 5))
    
    # Обрабатываем гостевую команду
    logging.info(f"\n✈️ ГОСТЕВАЯ КОМАНДА: {away_team}")
    success_away = yield process_team(away_team, match_folder, runner)
    
    # Итог по матчу
    if success_home and success_away:
        logging.info(f"\n✅ МАТЧ #{match_index} ПОЛНОСТЬЮ ОБРАБОТАН")
    else:
        logging.warning(f"\n⚠️ МАТЧ #{match_index} ОБРАБОТАН ЧАСТИЧНО")
        if not success_home:
            logging.warning(f"   • Не обработана: {home_team}")
        if not success_away:
            logging.warning(f"   • Не обработана: {away_team}")
    
    defer.returnValue(success_home and success_away)

@defer.inlineCallbacks
def retry_failed_teams_only():
    """
    Специальная функция для повторной обработки только упавших команд.
    Запускается отдельно через скрипт retry_failed.py
    
    Возвращает:
        bool: True если все повторные попытки успешны
    """
    logging.info("\n🔄 ПОВТОРНАЯ ОБРАБОТКА УПАВШИХ КОМАНД")
    
    failed_teams = read_failed_teams()
    if not failed_teams:
        logging.info("Нет команд для повторной обработки")
        defer.returnValue(True)
    
    logging.info(f"Найдено {len(failed_teams)} команд для повторной обработки")
    
    runner = CrawlerRunner()
    successful = 0
    
    for i, team_name in enumerate(failed_teams, 1):
        logging.info(f"\n[{i}/{len(failed_teams)}] Повторная обработка: {team_name}")
        
        # Создаем специальную папку для повторно обработанных команд
        match_folder = create_match_folder("Повторная", "обработка")
        
        # Пробуем обработать с увеличенным количеством попыток
        success = yield process_team(team_name, match_folder, runner, retry_count=i)
        
        if success:
            successful += 1
            logging.info(f"✅ {team_name} успешно обработана повторно")
        else:
            logging.error(f"❌ {team_name} не обработана даже после повтора")
    
    logging.info(f"\n📊 Повторная обработка завершена: {successful}/{len(failed_teams)}")
    defer.returnValue(successful == len(failed_teams))

# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

@defer.inlineCallbacks
def main():
    """
    ГЛАВНАЯ ФУНКЦИЯ ПРОГРАММЫ
    =========================
    
    Полный цикл работы:
        1. Настройка логирования и окружения
        2. Получение списка всех матчей из competitions
        3. Последовательная обработка каждого матча
        4. Сбор статистики и вывод итогов
        5. Остановка реактора Twisted
    
    Особенности:
        - Асинхронная обработка через Twisted
        - Устойчивость к ошибкам (продолжает работу при сбоях)
        - Детальное логирование каждого шага
        - Автоматическое создание структуры папок
    """
    # Настройка кодировки для Windows
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Инициализация логирования
    setup_logger()
    configure_logging()
    
    # Очищаем лог ошибок при новом запуске
    if os.path.exists(ERROR_LOG_FILE):
        os.remove(ERROR_LOG_FILE)
        logging.info(f"Очищен файл лога ошибок: {ERROR_LOG_FILE}")
    
    logging.info("\n" + "🚀"*10)
    logging.info("ЗАПУСК ПАРСЕРА TRANSFERMARKT")
    logging.info("🚀"*10 + "\n")
    
    # Создаем runner для Scrapy
    runner = CrawlerRunner()
    
    # Получаем все матчи из папки competitions
    all_matches = get_all_matches_from_competitions()
    if not all_matches:
        logging.error("Нет матчей для обработки. Проверьте папку competitions.")
        reactor.stop()
        return
    
    logging.info(f"\n📋 Найдено матчей для обработки: {len(all_matches)}")
    
    # Основной цикл обработки матчей
    successful_matches = 0
    start_time = datetime.now()
    
    for i, match in enumerate(all_matches, 1):
        try:
            success = yield process_match(match, i, runner)
            if success:
                successful_matches += 1
            
            # Прогресс после каждого матча
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
    
    # Вычисляем общее время работы
    total_time = (datetime.now() - start_time).total_seconds()
    
    # Итоговая статистика
    logging.info(f"\n{'='*60}")
    logging.info("ЗАВЕРШЕНИЕ РАБОТЫ")
    logging.info(f"{'='*60}")
    logging.info(f"📊 Общее время работы: {total_time/60:.1f} минут")
    
    # Выводим красивую сводку
    print_final_summary(successful_matches, len(all_matches))
    
    # Останавливаем реактор Twisted
    logging.info("\n🛑 Остановка реактора...")
    reactor.stop()

# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

if __name__ == '__main__':
    """
    Точка входа в программу.
    Запускает главную функцию и реактор Twisted.
    """
    try:
        main()
        reactor.run()  # Запускаем асинхронный реактор
    except KeyboardInterrupt:
        logging.info("\n⚠️ Программа остановлена пользователем")
        reactor.stop()
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        logging.debug(traceback.format_exc())
        reactor.stop()