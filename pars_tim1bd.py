import logging
from database import Database
from utils.logger import setup_logger
from scraper.base_scraper import BaseScraper
from scraper.team_scraper import TeamScraper

def check_team_in_db(team_name):
    """Проверяет, есть ли команда в базе данных"""
    db = Database()
    try:
        with db.conn.cursor() as cursor:
            cursor.execute(
                "SELECT team_id, transfermarkt_url FROM Teams WHERE team_name = %s",
                (team_name,)
            )
            result = cursor.fetchone()
            
            if result:
                logging.info(f"Команда '{team_name}' уже есть в БД (ID: {result[0]}, URL: {result[1]})")
                return True
            return False
            
    except Exception as e:
        logging.error(f"Ошибка проверки команды в БД: {str(e)}")
        return False
    finally:
        db.close()

def parse_team_url_only(team_name):
    """Парсит только URL команды и сохраняет в БД (без игроков)"""
    db = Database()
    scraper = BaseScraper()
    
    try:
        team_scraper = TeamScraper(scraper.driver)
        
        # Ищем URL команды
        input_team_name, team_url = team_scraper.find_team_url(team_name)
        if not team_url:
            logging.error(f"Не удалось найти URL для команды {team_name}")
            return False

        logging.info(f"Найден URL для команды '{input_team_name}': {team_url}")

        # Сохранение только команды в БД
        team_id = db.save_team(input_team_name, team_url)
        if not team_id:
            logging.error("Не удалось сохранить команду в БД")
            return False

        logging.info(f"Команда успешно сохранена в БД с ID: {team_id}")
        return True
            
    except Exception as e:
        logging.error(f"Ошибка при парсинге URL команды: {str(e)}")
        return False
    finally:
        scraper.close_driver()
        db.close()

def main():
    """Основная функция для сбора URL команды"""
    setup_logger()
    team_name = input("Введите название команды: ").strip()
    
    if not team_name:
        logging.error("Не указано название команды")
        return

    # Проверяем, есть ли команда уже в БД
    if check_team_in_db(team_name):
        logging.info(f"Команда '{team_name}' уже существует в базе данных")
        return

    # Парсим и сохраняем URL команды
    success = parse_team_url_only(team_name)
    if success:
        logging.info(f"URL команды '{team_name}' успешно сохранен в БД")
    else:
        logging.error(f"Не удалось сохранить URL команды '{team_name}'")

if __name__ == '__main__':
    print("Парсинг URL команды и сохранение в БД (без игроков)")
    main()
