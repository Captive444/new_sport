import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Dict

class UniversalLeagueParser:
    """Универсальный парсер таблиц лиг с Transfermarkt"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def parse_league(self, url: str) -> List[Dict]:
        """Парсит лигу по URL и возвращает список команд"""
        try:
            self.logger.info(f"Парсинг лиги: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._parse_table(soup)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга {url}: {e}")
            return []
    
    def _parse_table(self, soup: BeautifulSoup) -> List[Dict]:
        """Парсит таблицу из BeautifulSoup объекта"""
        teams = []
        
        # Находим все строки таблицы
        rows = soup.select('table.items tbody tr')
        
        for row in rows:
            team_data = self._parse_team_row(row)
            if team_data:
                teams.append(team_data)
        
        # Сортируем по позиции
        teams.sort(key=lambda x: x['position'])
        self.logger.info(f"Извлечено {len(teams)} команд")
        
        return teams
    
    def _parse_team_row(self, row) -> Dict:
        """Парсит строку с данными команды"""
        try:
            # Позиция (извлекаем первое число)
            pos_cell = row.find('td', class_='rechts')
            if not pos_cell:
                return None
                
            position_text = pos_cell.get_text(strip=True)
            position = int(position_text.split()[0])
            
            # Название команды (из атрибута title ссылки)
            team_link = row.find('a', href=lambda x: x and '/spielplan/verein/' in x)
            if not team_link:
                return None
                
            team_name = team_link.get('title', '').strip()
            if not team_name:
                return None
            
            # Статистика: матчи, разница голов, очки
            stats_cells = row.find_all('td', class_='zentriert')
            stats = []
            
            for cell in stats_cells:
                text = cell.get_text(strip=True)
                # Проверяем, что это число (может быть отрицательным)
                if text and self._is_number(text.replace('-', '').replace('+', '')):
                    stats.append(text)
            
            if len(stats) < 3:
                return None
            
            # Преобразуем в числа
            matches_played = int(stats[0])
            goal_difference = int(stats[1])
            points = int(stats[2])
            
            return {
                'position': position,
                'team_name': team_name,
                'matches_played': matches_played,
                'goal_difference': goal_difference,
                'points': points
            }
            
        except (ValueError, AttributeError, IndexError) as e:
            return None
    
    def _is_number(self, s: str) -> bool:
        """Проверяет, является ли строка числом"""
        try:
            float(s)
            return True
        except ValueError:
            return False
    
    def save_to_json(self, data: List[Dict], filename: str):
        """Сохраняет данные в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Данные сохранены в {filename}")

# Пример использования
def main():
    parser = UniversalLeagueParser()
    
    # Список лиг для парсинга
    leagues = {
        "premier_league": "https://www.transfermarkt.world/premier-league/startseite/wettbewerb/GB1",
        "bundesliga": "https://www.transfermarkt.world/bundesliga/startseite/wettbewerb/L1", 
        "la_liga": "https://www.transfermarkt.world/laliga/startseite/wettbewerb/ES1",
        "serie_a": "https://www.transfermarkt.world/serie-a/startseite/wettbewerb/IT1",
        "ligue_1": "https://www.transfermarkt.world/ligue-1/startseite/wettbewerb/FR1"
    }
    
    for league_name, url in leagues.items():
        print(f"\n🔄 Парсинг {league_name}...")
        
        teams = parser.parse_league(url)
        
        if teams:
            # Сохраняем в файл
            filename = f"{league_name}_table.json"
            parser.save_to_json(teams, filename)
            
            # Выводим результаты
            print(f"✅ {league_name}: {len(teams)} команд")
            print("Топ-5 команд:")
            for team in teams[:5]:
                print(f"  {team['position']}. {team['team_name']} - {team['points']} очков")
        else:
            print(f"❌ Не удалось спарсить {league_name}")

if __name__ == "__main__":
    main()