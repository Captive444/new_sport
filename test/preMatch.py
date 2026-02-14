import os
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def get_upcoming_matches(url):
    """
    Упрощенная функция для получения предстоящих матчей
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Название лиги
        league_name = "Неизвестная лига"
        title = soup.find('title')
        if title:
            league_name = title.text.split(' - ')[0].strip()
        
        print(f"Лига: {league_name}")
        
        # Предстоящие матчи
        matches = []
        next_tur_block = soup.find('div', id='next_tur')
        
        if next_tur_block:
            game_blocks = next_tur_block.find_all('div', class_='game_block')
            
            for block in game_blocks:
                game_link = block.find('a', class_='game_link')
                if game_link:
                    # Дата и время
                    status_div = game_link.find('div', class_='status')
                    date_time = status_div.text.strip() if status_div else ''
                    
                    # Команды
                    result_div = game_link.find('div', class_='result')
                    if result_div:
                        home_team_div = result_div.find('div', class_='ht')
                        away_team_div = result_div.find('div', class_='at')
                        
                        if home_team_div and away_team_div:
                            home_team_span = home_team_div.find('span')
                            away_team_span = away_team_div.find('span')
                            
                            home_team = home_team_span.text.strip() if home_team_span else ''
                            away_team = away_team_span.text.strip() if away_team_span else ''
                            
                            match_data = {
                                'date_time': date_time,
                                'home_team': home_team,
                                'away_team': away_team,
                                'match': f"{home_team} - {away_team}"
                            }
                            
                            matches.append(match_data)
                            print(f"Добавлен матч: {home_team} - {away_team} ({date_time})")
        
        result_data = {
            'league': league_name,
            'total_matches': len(matches),
            'matches': matches
        }
        
        # Создаем папку на основе ID лиги из URL
        league_id = extract_league_id(url)
        folder_path = f"competitions/{league_id}"
        os.makedirs(folder_path, exist_ok=True)
        
        # Сохраняем в файл в соответствующей папке
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', league_name)
        filename = f"{folder_path}/upcoming_matches_{safe_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"Данные сохранены в файл: {filename}")
        
        return result_data
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def extract_league_id(url):
    """Извлекает ID лиги из URL"""
    # Пример: "https://soccer365.ru/competitions/723/" -> "723"
    match = re.search(r'/competitions/(\d+)/', url)
    if match:
        return match.group(1)
    return "unknown"

def main():
    # Массив URL лиг
    league_urls = [
        "https://soccer365.ru/competitions/723/"   # АПЛ
   
        # Добавьте другие лиги по необходимости
    ]
    
    for url in league_urls:
        print(f"\nПарсинг лиги: {url}")
        matches_data = get_upcoming_matches(url)
        
        if matches_data:
            print(f"✅ Успешно получены данные для лиги: {matches_data['league']}")
            print(f"📊 Количество матчей: {matches_data['total_matches']}")
        else:
            print(f"❌ Не удалось получить данные для лиги: {url}")

if __name__ == "__main__":
    main()