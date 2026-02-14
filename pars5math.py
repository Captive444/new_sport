import requests
from bs4 import BeautifulSoup
import re

def parse_last_5_matches(team_id=6974):
    """
    Парсит результаты последних 5 матчей команды с сайта soccer365.ru
    
    Args:
        team_id (int): ID команды на сайте (по умолчанию 6974 - НЕК)
    
    Returns:
        list: Список словарей с информацией о матчах
    """
    
    url = f"https://soccer365.ru/clubs/{team_id}/"
    
    try:
        # Отправляем запрос к странице
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Находим блок с расписанием
        schedule_block = soup.find('div', id='club_schedule')
        if not schedule_block:
            print("Блок с расписанием не найден")
            return []
        
        # Находим все блоки с матчами
        match_blocks = schedule_block.find_all('div', class_='game_block')
        
        matches = []
        match_count = 0
        
        for block in match_blocks:
            if match_count >= 5:  # Берем только последние 5 матчей
                break
                
            # Пропускаем будущие матчи (где счет "-")
            score_elements = block.find_all('div', class_='gls')
            if not score_elements or score_elements[0].text.strip() == '-':
                continue
                
            match_data = extract_match_data(block)
            if match_data:
                matches.append(match_data)
                match_count += 1
        
        return matches
        
    except requests.RequestException as e:
        print(f"Ошибка при запросе: {e}")
        return []
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return []

def extract_match_data(match_block):
    """
    Извлекает данные о матче из блока
    """
    try:
        # Извлекаем названия команд
        team_names = match_block.find_all('div', class_='name')
        if len(team_names) < 2:
            return None
            
        home_team = team_names[0].find('span').text.strip()
        away_team = team_names[1].find('span').text.strip()
        
        # Извлекаем счет
        scores = match_block.find_all('div', class_='gls')
        if len(scores) < 2:
            return None
            
        home_score = scores[0].text.strip()
        away_score = scores[1].text.strip()
        
        # Извлекаем дату и статус
        status_div = match_block.find('div', class_='status')
        date_status = status_div.find('span').text.strip() if status_div else "Неизвестно"
        
        # Извлекаем турнир
        tournament_div = match_block.find('div', class_='cmp')
        tournament = tournament_div.find('span').text.strip() if tournament_div else "Неизвестно"
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'score': f"{home_score}:{away_score}",
            'home_score': home_score,
            'away_score': away_score,
            'date_status': date_status,
            'tournament': tournament
        }
        
    except Exception as e:
        print(f"Ошибка при извлечении данных матча: {e}")
        return None

def print_matches(matches):
    """
    Красиво выводит информацию о матчах
    """
    if not matches:
        print("Матчи не найдены")
        return
        
    print("\n" + "="*60)
    print("ПОСЛЕДНИЕ 5 МАТЧЕЙ КОМАНДЫ НЕК")
    print("="*60)
    
    for i, match in enumerate(matches, 1):
        print(f"\nМатч #{i}:")
        print(f"  Команды: {match['home_team']} - {match['away_team']}")
        print(f"  Счет: {match['score']}")
        print(f"  Статус: {match['date_status']}")
        print(f"  Турнир: {match['tournament']}")

# Пример использования
if __name__ == "__main__":
    matches = parse_last_5_matches()
    print_matches(matches)