import os
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time

def get_upcoming_matches_with_team_ids(url):
    """
    Получение предстоящих матчей с ID команд из ссылок /clubs/
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
                    
                    # Команды и их ID
                    result_div = game_link.find('div', class_='result')
                    if result_div:
                        home_team_div = result_div.find('div', class_='ht')
                        away_team_div = result_div.find('div', class_='at')
                        
                        if home_team_div and away_team_div:
                            home_team_span = home_team_div.find('span')
                            away_team_span = away_team_div.find('span')
                            
                            home_team = home_team_span.text.strip() if home_team_span else ''
                            away_team = away_team_span.text.strip() if away_team_span else ''
                            
                            # Ищем ID команд в ссылках /clubs/
                            home_team_id = None
                            away_team_id = None
                            
                            # Ищем все ссылки на клубы в блоке матча
                            club_links = block.find_all('a', href=re.compile(r'/clubs/\d+/'))
                            
                            for link in club_links:
                                href = link['href']
                                # Извлекаем ID из ссылки /clubs/123/
                                club_match = re.search(r'/clubs/(\d+)/', href)
                                if club_match:
                                    team_id = club_match.group(1)
                                    link_text = link.get_text(strip=True)
                                    
                                    # Определяем какая это команда
                                    if link_text.lower() == home_team.lower():
                                        home_team_id = team_id
                                    elif link_text.lower() == away_team.lower():
                                        away_team_id = team_id
                                    # Если названия не совпадают, пробуем по классам родителя
                                    elif 'ht' in link.find_parent().get('class', []):
                                        home_team_id = team_id
                                    elif 'at' in link.find_parent().get('class', []):
                                        away_team_id = team_id
                            
                            # Если ID не найдены через ссылки, пробуем получить их через страницу матча
                            if not home_team_id or not away_team_id:
                                match_href = game_link.get('href', '')
                                if match_href:
                                    ht_id, at_id = get_team_ids_from_match_page(match_href)
                                    if ht_id and not home_team_id:
                                        home_team_id = ht_id
                                    if at_id and not away_team_id:
                                        away_team_id = at_id
                            
                            match_data = {
                                'date_time': date_time,
                                'home_team': home_team,
                                'away_team': away_team,
                                'match': f"{home_team} - {away_team}",
                                'home_team_id': home_team_id,
                                'away_team_id': away_team_id,
                                'home_team_url': f"https://soccer365.ru/clubs/{home_team_id}/" if home_team_id else None,
                                'away_team_url': f"https://soccer365.ru/clubs/{away_team_id}/" if away_team_id else None,
                                'match_url': game_link.get('href', '')
                            }
                            
                            matches.append(match_data)
                            print(f"Матч: {home_team} ({home_team_id}) - {away_team} ({away_team_id})")
        
        result_data = {
            'league': league_name,
            'league_url': url,
            'league_id': extract_league_id(url),
            'scraped_at': datetime.now().isoformat(),
            'total_matches': len(matches),
            'matches': matches
        }
        
        # Сохраняем данные
        save_upcoming_matches(result_data)
        
        return result_data
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_team_ids_from_match_page(match_url):
    """
    Получает ID команд со страницы матча
    """
    try:
        if not match_url.startswith('http'):
            match_url = 'https://soccer365.ru' + match_url
        
        # Добавляем небольшую задержку, чтобы не перегружать сервер
        time.sleep(0.5)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(match_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        home_team_id = None
        away_team_id = None
        
        # Ищем ссылки на клубы с классами live_game_ht и live_game_at
        home_team_div = soup.find('div', class_='live_game_ht')
        if home_team_div:
            home_link = home_team_div.find('a', href=re.compile(r'/clubs/\d+/'))
            if home_link:
                match = re.search(r'/clubs/(\d+)/', home_link['href'])
                if match:
                    home_team_id = match.group(1)
        
        away_team_div = soup.find('div', class_='live_game_at')
        if away_team_div:
            away_link = away_team_div.find('a', href=re.compile(r'/clubs/\d+/'))
            if away_link:
                match = re.search(r'/clubs/(\d+)/', away_link['href'])
                if match:
                    away_team_id = match.group(1)
        
        # Альтернативный поиск
        if not home_team_id or not away_team_id:
            club_links = soup.find_all('a', href=re.compile(r'/clubs/\d+/'))
            for link in club_links:
                match = re.search(r'/clubs/(\d+)/', link['href'])
                if match:
                    team_id = match.group(1)
                    # Пытаемся определить домашняя/гостевая
                    parent_div = link.find_parent('div')
                    if parent_div:
                        parent_classes = parent_div.get('class', [])
                        if 'live_game_ht' in parent_classes or 'ht' in parent_classes:
                            home_team_id = team_id
                        elif 'live_game_at' in parent_classes or 'at' in parent_classes:
                            away_team_id = team_id
        
        print(f"  [Страница матча] ID команд: домашняя={home_team_id}, гостевая={away_team_id}")
        return home_team_id, away_team_id
        
    except Exception as e:
        print(f"Ошибка при парсинге страницы матча: {e}")
        return None, None

def extract_league_id(url):
    """Извлекает ID лиги из URL"""
    match = re.search(r'/competitions/(\d+)/', url)
    if match:
        return match.group(1)
    return "unknown"

def save_upcoming_matches(data):
    """Сохраняет данные о матчах в файл"""
    try:
        league_id = data['league_id']
        folder_path = f"competitions/{league_id}"
        os.makedirs(folder_path, exist_ok=True)
        
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', data['league'])
        filename = f"{folder_path}/upcoming_matches_{safe_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные сохранены в: {filename}")
        
        # Дополнительно сохраняем статистику
        matches_with_ids = sum(1 for m in data['matches'] if m['home_team_id'] and m['away_team_id'])
        print(f"📊 Статистика: {matches_with_ids}/{data['total_matches']} матчей с ID команд")
        
    except Exception as e:
        print(f"Ошибка сохранения файла: {e}")

def main():
    # Массив URL лиг
    league_urls = [
        # "https://soccer365.ru/competitions/723/",  
        # "https://soccer365.ru/competitions/13/",
        # 'https://soccer365.ru/competitions/12/'    # Пример другой лиги
        'https://soccer365.ru/competitions/17/'
      
    ]
     
    print("=== ПАРСИНГ ПРЕДСТОЯЩИХ МАТЧЕЙ С ID КОМАНД ===")
    print(f"Всего лиг для обработки: {len(league_urls)}")
    
    for url in league_urls:
        print(f"\n{'='*60}")
        print(f"Обработка лиги: {url}")
        print(f"{'='*60}")
        
        matches_data = get_upcoming_matches_with_team_ids(url)
        
        if matches_data:
            print(f"\n✅ Успешно обработано: {matches_data['league']}")
            print(f"📊 Всего матчей: {matches_data['total_matches']}")
            
            # Детальная статистика
            matches_with_both_ids = 0
            matches_with_one_id = 0
            matches_without_ids = 0
            
            for match in matches_data['matches']:
                if match['home_team_id'] and match['away_team_id']:
                    matches_with_both_ids += 1
                elif match['home_team_id'] or match['away_team_id']:
                    matches_with_one_id += 1
                else:
                    matches_without_ids += 1
            
            print(f"🎯 Матчей с двумя ID: {matches_with_both_ids}")
            print(f"⚠️  Матчей с одним ID: {matches_with_one_id}")
            print(f"❌ Матчей без ID: {matches_without_ids}")
        else:
            print(f"\n❌ Не удалось получить данные для лиги: {url}")

if __name__ == "__main__":
    main()