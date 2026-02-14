# # database.py
# # database.py
# database.py
import pymysql
import logging
from config import DB_CONFIG


class Database:
    def __init__(self):
        self.conn = self.create_db_connection()

    def create_db_connection(self):
        """Создать соединение с базой данных."""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            logging.info("Успешное подключение к БД")
            return conn
        except pymysql.Error as err:
            logging.error(f"Ошибка подключения к БД: {err}")
            return None

    def save_team(self, team_name, team_url):
        """Сохранить команду в БД."""
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("SELECT team_id FROM Teams WHERE team_url = %s", (team_url,))
                existing_team = cursor.fetchone()
                
                if existing_team:
                    cursor.execute("""
                        UPDATE Teams 
                        SET team_name = %s 
                        WHERE team_url = %s AND (team_name = '' OR team_name != %s)
                    """, (team_name, team_url, team_name))
                    self.conn.commit()
                    logging.info(f"Название команды обновлено: '{team_name}'")
                    return existing_team[0]
                else:
                    cursor.execute("""
                        INSERT INTO Teams (team_name, team_url)
                        VALUES (%s, %s)
                    """, (team_name, team_url))
                    self.conn.commit()
                    logging.info(f"Команда '{team_name}' сохранена")
                    return cursor.lastrowid
            except pymysql.Error as err:
                logging.error(f"Ошибка сохранения команды: {err}")
                return None

    def save_player(self, team_id, player_url):
        """Сохранить игрока в БД с привязкой к team_id."""
        if team_id is None:
            logging.error("Невозможно сохранить игрока, так как team_id не найден.")
            return False

        with self.conn.cursor() as cursor:
            try:
                player_name = player_url.split('/')[-3].replace('-', ' ').title()
                cursor.execute("""
                    INSERT INTO Players (team_id, transfermarkt_url, full_name, position)
                    VALUES (%s, %s, %s, 'Unknown')
                    ON DUPLICATE KEY UPDATE team_id = VALUES(team_id)
                """, (team_id, player_url, player_name))
                self.conn.commit()
                logging.info(f"Игрок '{player_name}' сохранен (team_id: {team_id})")
                return True
            except pymysql.Error as err:
                logging.error(f"Ошибка сохранения игрока: {err}")
                return False

    def get_players_by_team(self, team_id):
        """Получить список игроков конкретной команды."""
        if not self.conn:
            logging.error("Нет соединения с БД")
            return []

        try:
            with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT player_id, transfermarkt_url 
                    FROM Players 
                    WHERE team_id = %s 
                    AND transfermarkt_url IS NOT NULL
                """, (team_id,))
                return cursor.fetchall()
        except pymysql.Error as err:
            logging.error(f"Ошибка получения игроков команды {team_id}: {err}")
            return []

    def update_player_info(self, player_id, full_name, position):
        """Обновить информацию об игроке."""
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    UPDATE Players 
                    SET full_name = %s, position = %s 
                    WHERE player_id = %s
                """, (full_name, position, player_id))
                self.conn.commit()
                return True
            except pymysql.Error as err:
                logging.error(f"Ошибка обновления игрока {player_id}: {err}")
                return False

    def save_player_stats(self, player_id, tournament_stats):
        """Сохранить статистику игрока по турнирам."""
        with self.conn.cursor() as cursor:
            try:
                # Удаляем старую статистику перед сохранением новой
                cursor.execute("""
                    DELETE FROM PlayerTournamentStats 
                    WHERE player_id = %s
                """, (player_id,))
                
                # Сохраняем новую статистику
                for stat in tournament_stats:
                    cursor.execute("""
                        INSERT INTO PlayerTournamentStats (
                            player_id, tournament_id, matches, minutes, 
                            goals, assists, yellow_cards, red_cards
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        player_id,
                        self._get_or_create_tournament_id(stat['name']),
                        stat.get('matches', 0),
                        stat.get('minutes', 0),
                        stat.get('goals', 0),
                        stat.get('assists', 0),
                        stat.get('yellow_cards', 0),
                        stat.get('red_cards', 0)
                    ))
                self.conn.commit()
                return True
            except pymysql.Error as err:
                self.conn.rollback()
                logging.error(f"Ошибка сохранения статистики игрока {player_id}: {err}")
                return False

    def _get_or_create_tournament_id(self, tournament_name):
        """Получить или создать ID турнира."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT tournament_id FROM Tournaments 
                WHERE tournament_name = %s
            """, (tournament_name,))
            tournament = cursor.fetchone()
            
            if tournament:
                return tournament[0]
            else:
                cursor.execute("""
                    INSERT INTO Tournaments (tournament_name, season)
                    VALUES (%s, '2023/2024')
                """, (tournament_name,))
                self.conn.commit()
                return cursor.lastrowid

    def close(self):
        """Закрыть соединение с базой данных."""
        if self.conn and self.conn.open:
            self.conn.close()
            logging.info("Соединение с БД закрыто")
# import pymysql
# import logging
# from config import DB_CONFIG
# import json

# class Database:
#     def __init__(self):
#         self.conn = None
#         self.create_db_connection()

#     def create_db_connection(self):
#         """Создать соединение с базой данных"""
#         try:
#             self.conn = pymysql.connect(
#                 host=DB_CONFIG['host'],
#                 user=DB_CONFIG['user'],
#                 password=DB_CONFIG['password'],
#                 database=DB_CONFIG['database'],
#                 charset='utf8mb4',
#                 cursorclass=pymysql.cursors.DictCursor
#             )
#             logging.info("Успешное подключение к БД")
#         except pymysql.Error as err:
#             logging.error(f"Ошибка подключения к БД: {err}")
#             raise

#     def save_team(self, team_name, team_url):
#         """Сохранить команду в БД"""
#         try:
#             with self.conn.cursor() as cursor:
#                 cursor.execute(
#                     "INSERT INTO Teams (team_name, team_url) VALUES (%s, %s) ON DUPLICATE KEY UPDATE team_name = VALUES(team_name)",
#                     (team_name, team_url)
#                 )
#                 self.conn.commit()
#                 return cursor.lastrowid
#         except pymysql.Error as err:
#             logging.error(f"Ошибка сохранения команды: {err}")
#             return None

#     def save_player(self, team_id, player_url):
#         """Сохранить игрока в таблицу PlayersTrans"""
#         try:
#             with self.conn.cursor() as cursor:
#                 player_name = player_url.split('/')[-3].replace('-', ' ').title()
#                 cursor.execute(
#                     """INSERT INTO PlayersTrans (team_id, full_name, transfermarkt_url) 
#                     VALUES (%s, %s, %s) 
#                     ON DUPLICATE KEY UPDATE 
#                         team_id = VALUES(team_id),
#                         full_name = VALUES(full_name)""",
#                     (team_id, player_name, player_url)
#                 )
#                 self.conn.commit()
#                 return cursor.lastrowid
#         except pymysql.Error as err:
#             logging.error(f"Ошибка сохранения игрока: {err}")
#             return None

#     def get_players_by_team(self, team_id):
#         """Получить список игроков команды из PlayersTrans"""
#         try:
#             with self.conn.cursor() as cursor:
#                 cursor.execute(
#                     """SELECT player_id, transfermarkt_url 
#                     FROM PlayersTrans 
#                     WHERE team_id = %s AND transfermarkt_url IS NOT NULL""",
#                     (team_id,)
#                 )
#                 return cursor.fetchall()
#         except pymysql.Error as err:
#             logging.error(f"Ошибка получения игроков: {err}")
#             return []

#     def save_player_stats(self, player_id, player_data):
#         """Сохранить статистику игрока в PlayersTrans"""
#         try:
#             with self.conn.cursor() as cursor:
#                 # Проверяем существование колонки player_data
#                 cursor.execute("SHOW COLUMNS FROM PlayersTrans LIKE 'player_data'")
#                 if not cursor.fetchone():
#                     raise ValueError("Column player_data does not exist in PlayersTrans")
                
#                 cursor.execute(
#                     """UPDATE PlayersTrans 
#                     SET full_name = %s, 
#                         position = %s,
#                         player_data = %s
#                     WHERE player_id = %s""",
#                     (player_data['name'], 
#                      player_data['position'],
#                      json.dumps(player_data['stats']),
#                      player_id)
#                 )
#                 self.conn.commit()
#                 return True
#         except pymysql.Error as err:
#             self.conn.rollback()
#             logging.error(f"Ошибка сохранения статистики: {err}")
#             return False
#         except Exception as e:
#             self.conn.rollback()
#             logging.error(f"Неожиданная ошибка: {str(e)}")
#             return False

#     def close(self):
#         """Закрыть соединение с БД"""
#         if self.conn and self.conn.open:
#             self.conn.close()
#             logging.info("Соединение с БД закрыто")