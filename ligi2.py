import requests
from bs4 import BeautifulSoup
import json
import re

def parse_league_table(url):
    """
    Парсит таблицу лиги с сайта soccer365.ru
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Название лиги из заголовка страницы
        title = soup.find('title')
        league_name = "Неизвестная лига"
        if title:
            league_name = title.text.split(' - ')[0].strip()
        
        # Поиск таблицы
        table_div = soup.find('div', id='competition_table')
        if not table_div:
            return None, league_name
            
        table = table_div.find('table')
        if not table:
            return None, league_name
        
        # Извлечение данных из таблицы
        teams_data = []
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 10:
                # Позиция
                position_div = cells[0].find('div')
                position = position_div.text.strip() if position_div else ''
                
                # Название команды
                team_link = cells[1].find('a')
                team_name = team_link.text.strip() if team_link else ''
                
                # Статистика
                stats = [cell.text.strip() for cell in cells[2:10]]
                
                # Очки
                points_cell = cells[9].find('b')
                points = points_cell.text.strip() if points_cell else cells[9].text.strip()
                
                team_data = {
                    'position': position,
                    'team': team_name,
                    'games': stats[0],
                    'wins': stats[1],
                    'draws': stats[2],
                    'losses': stats[3],
                    'goals_for': stats[4],
                    'goals_against': stats[5],
                    'goal_difference': stats[6],
                    'points': points
                }
                
                teams_data.append(team_data)
        
        return teams_data, league_name
        
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {e}")
        return None, "Ошибка"

def parse_next_tour(url):
    """
    Парсит матчи следующего тура
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Поиск блока следующего тура
        next_tour_div = soup.find('div', id='next_tur')
        if not next_tour_div:
            return None, "Неизвестный тур"
        
        # Название тура
        tour_header = next_tour_div.find('div', class_='block_header')
        tour_name = tour_header.text.strip() if tour_header else "Следующий тур"
        
        # Матчи
        matches_data = []
        game_blocks = next_tour_div.find_all('div', class_='game_block')
        
        for block in game_blocks:
            # Извлекаем данные из JSON-LD
            script = block.find('script', type='application/ld+json')
            json_data = {}
            
            if script:
                try:
                    json_data = json.loads(script.string)
                except:
                    pass
            
            # Альтернативный парсинг из HTML
            game_link = block.find('a', class_='game_link')
            if game_link:
                # Дата и время
                status_div = game_link.find('div', class_='status')
                date_time = status_div.text.strip() if status_div else ''
                
                # Команды и результат
                result_div = game_link.find('div', class_='result')
                if result_div:
                    home_team_div = result_div.find('div', class_='ht')
                    away_team_div = result_div.find('div', class_='at')
                    
                    home_team = home_team_div.find('span').text.strip() if home_team_div and home_team_div.find('span') else ''
                    away_team = away_team_div.find('span').text.strip() if away_team_div and away_team_div.find('span') else ''
                    
                    home_score = home_team_div.find('div', class_='gls').text.strip() if home_team_div and home_team_div.find('div', class_='gls') else '-'
                    away_score = away_team_div.find('div', class_='gls').text.strip() if away_team_div and away_team_div.find('div', class_='gls') else '-'
                    
                    match_data = {
                        'home_team': home_team,
                        'away_team': away_team,
                        'score': f"{home_score}:{away_score}",
                        'date_time': date_time,
                        'venue': json_data.get('location', {}).get('name', '') if json_data else '',
                        'start_date': json_data.get('startDate', '') if json_data else ''
                    }
                    
                    matches_data.append(match_data)
        
        return matches_data, tour_name
        
    except Exception as e:
        print(f"Ошибка при парсинге следующего тура: {e}")
        return None, "Ошибка"

def save_to_json(data, filename):
    """
    Сохраняет данные в JSON файл
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в файл: {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении файла {filename}: {e}")

def main():
    url = "https://soccer365.ru/competitions/12/"
    
    print("Парсинг данных...")
    
    # Парсим таблицу лиги
    table_data, league_name = parse_league_table(url)
    
    if table_data:
        # Создаем безопасное имя файла
        safe_league_name = re.sub(r'[<>:"/\\|?*]', '_', league_name)
        table_filename = f"{safe_league_name}_table.json"
        
        table_output = {
            "league": league_name,
            "teams": table_data
        }
        
        save_to_json(table_output, table_filename)
    else:
        print("Не удалось получить данные таблицы")
    
    # Парсим следующий тур
    next_tour_data, tour_name = parse_next_tour(url)
    
    if next_tour_data:
        # Создаем безопасное имя файла
        safe_tour_name = re.sub(r'[<>:"/\\|?*]', '_', tour_name)
        tour_filename = f"{safe_tour_name}_matches.json"
        
        tour_output = {
            "tour": tour_name,
            "matches": next_tour_data
        }
        
        save_to_json(tour_output, tour_filename)
    else:
        print("Не удалось получить данные следующего тура")

if __name__ == "__main__":
    main()