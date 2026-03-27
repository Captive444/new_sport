# database.py

import psycopg2
import logging
from typing import Optional, Tuple, List

class Database:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self):
        """Инициализация подключения к базе данных"""
        self.conn = None
        self.connect()
    
    def connect(self):
        """Установка соединения с базой данных"""
        try:
            # Параметры подключения - измените под вашу конфигурацию
            self.conn = psycopg2.connect(
                database="sport_db",  # название вашей БД
                user="postgres",      # ваш пользователь
                password="your_password",  # ваш пароль
                host="localhost",
                port="5432"
            )
            logging.info("Успешное подключение к базе данных")
        except Exception as e:
            logging.error(f"Ошибка подключения к базе данных: {e}")
            self.conn = None
    
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            logging.info("Соединение с БД закрыто")
    
    def get_team_url(self, team_name: str) -> Optional[str]:
        """
        Получение URL команды по названию
        
        Args:
            team_name: Название команды
            
        Returns:
            URL команды или None если не найдена
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT team_url FROM teams WHERE team_name = %s",
                    (team_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logging.error(f"Ошибка получения URL команды {team_name}: {e}")
            return None
    
    def get_all_teams(self) -> List[Tuple[str, str]]:
        """
        Получение всех команд из базы данных
        
        Returns:
            Список кортежей (название_команды, url)
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT team_name, team_url FROM teams ORDER BY team_name"
                )
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка получения списка команд: {e}")
            return []
    
    def add_team(self, team_name: str, team_url: str) -> bool:
        """
        Добавление новой команды в базу данных
        
        Args:
            team_name: Название команды
            team_url: URL команды на Transfermarkt
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO teams (team_name, team_url) VALUES (%s, %s) ON CONFLICT (team_name) DO UPDATE SET team_url = EXCLUDED.team_url",
                    (team_name, team_url)
                )
                self.conn.commit()
                logging.info(f"Команда {team_name} добавлена/обновлена")
                return True
        except Exception as e:
            logging.error(f"Ошибка добавления команды {team_name}: {e}")
            self.conn.rollback()
            return False
    
    def update_team_url(self, team_name: str, new_url: str) -> bool:
        """
        Обновление URL команды
        
        Args:
            team_name: Название команды
            new_url: Новый URL
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE teams SET team_url = %s WHERE team_name = %s",
                    (new_url, team_name)
                )
                self.conn.commit()
                logging.info(f"URL команды {team_name} обновлен")
                return True
        except Exception as e:
            logging.error(f"Ошибка обновления URL команды {team_name}: {e}")
            self.conn.rollback()
            return False
    
    def delete_team(self, team_name: str) -> bool:
        """
        Удаление команды из базы данных
        
        Args:
            team_name: Название команды
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM teams WHERE team_name = %s",
                    (team_name,)
                )
                self.conn.commit()
                logging.info(f"Команда {team_name} удалена")
                return True
        except Exception as e:
            logging.error(f"Ошибка удаления команды {team_name}: {e}")
            self.conn.rollback()
            return False
    
    def team_exists(self, team_name: str) -> bool:
        """
        Проверка существования команды в базе данных
        
        Args:
            team_name: Название команды
            
        Returns:
            True если команда существует
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM teams WHERE team_name = %s",
                    (team_name,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Ошибка проверки существования команды {team_name}: {e}")
            return False

# SQL для создания таблицы (выполните один раз в PostgreSQL)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(255) UNIQUE NOT NULL,
    team_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_team_name ON teams(team_name);
"""