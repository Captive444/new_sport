import requests
from bs4 import BeautifulSoup
import json
import re

def parse_team_data(url):
    """
    Парсит данные команды с soccer365.ru: позицию в лиге и последние 5 матчей
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем название команды из активной строки в таблице
        team_name = extract_team_name_from_table(soup)
        
        # Извлекаем позицию в лиге из таблицы
        league_position = extract_league_position(soup, team_name)
        
        # Извлекаем последние 5 матчей
        last_matches = extract_last_matches(soup, 5)
        
        # Конвертируем результаты в числовой формат
        last_results = convert_results_to_numeric(last_matches, team_name)
        
        return {
            'team_name': team_name,
            'position_in_league': league_position,
            'last_results': last_results,
            'last_matches_details': last_matches
        }
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return None

def extract_team_name_from_table(soup):
    """Извлекает название команды из активной строки в таблице"""
    try:
        # Ищем активную строку в таблице
        tables = soup.find_all('table', class_=['tablesorter', 'stngs'])
        
        for table in tables:
            active_row = table.find('tr', class_='active')
            if active_row:
                team_cell = active_row.find_all('td')[1]  # Вторая ячейка содержит название
                if team_cell:
                    team_link = team_cell.find('a')
                    if team_link:
                        return team_link.text.strip()
                    team_span = team_cell.find('span')
                    if team_span:
                        return team_span.text.strip()
        
        # Если не нашли активную строку, берем из заголовка
        title = soup.find('title')
        if title:
            title_text = title.text
            team_name = title_text.split(' - ')[0].strip()
            # Очищаем название от лишнего текста
            if 'ФК' in team_name:
                team_name = team_name.replace('ФК', '').strip().strip('"')
            return team_name
                
    except Exception as e:
        print(f"Ошибка при извлечении названия команды: {e}")
    
    return "Арсенал"  # fallback

def extract_league_position(soup, team_name):
    """Извлекает позицию команды в лиге из таблицы"""
    try:
        # Ищем все таблицы с классами
        tables = soup.find_all('table', class_=['tablesorter', 'stngs'])
        
        for table in tables:
            # Ищем строку с классом active (текущая команда)
            active_row = table.find('tr', class_='active')
            if active_row:
                position_cell = active_row.find('td')
                if position_cell:
                    position_div = position_cell.find('div', class_='plc')
                    if position_div:
                        position_text = position_div.text.strip()
                        # Извлекаем число из позиции
                        position_match = re.search(r'(\d+)', position_text)
                        if position_match:
                            return int(position_match.group(1))
        
        # Если не нашли активную строку, ищем по названию команды в таблице
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                team_cells = row.find_all('td')
                if len(team_cells) > 1:
                    team_cell = team_cells[1]  # Вторая ячейка обычно содержит название команды
                    team_text = team_cell.get_text().strip()
                    # Сравниваем упрощенные названия
                    if simplify_team_name(team_name) in simplify_team_name(team_text):
                        position_cell = team_cells[0]  # Первая ячейка содержит позицию
                        if position_cell:
                            position_div = position_cell.find('div', class_='plc')
                            if position_div:
                                position_text = position_div.text.strip()
                                position_match = re.search(r'(\d+)', position_text)
                                if position_match:
                                    return int(position_match.group(1))
                                
    except Exception as e:
        print(f"Ошибка при извлечении позиции: {e}")
    
    return None

def simplify_team_name(name):
    """Упрощает название команды для сравнения"""
    if not name:
        return ""
    # Убираем лишние слова и символы
    simple_name = re.sub(r'[^\w\s]', '', name.lower())
    simple_name = re.sub(r'\b(фк|fc|клуб|club)\b', '', simple_name)
    return simple_name.strip()

def extract_last_matches(soup, count=5):
    """Извлекает последние матчи команды из расписания"""
    matches = []
    
    try:
        # Ищем блок расписания
        schedule_block = soup.find('div', id='club_schedule')
        if not schedule_block:
            return matches
            
        game_blocks = schedule_block.find_all('div', class_='game_block')
        
        # Собираем только сыгранные матчи (где есть счет)
        played_matches = []
        for block in game_blocks:
            match_data = extract_match_data_from_block(block)
            if match_data and match_data['score_home'] != '-' and match_data['score_away'] != '-':
                # Проверяем, что счет числовой
                try:
                    int(match_data['score_home'])
                    int(match_data['score_away'])
                    played_matches.append(match_data)
                except ValueError:
                    continue
        
        # Берем последние count матчей (первые в списке - самые свежие)
        recent_matches = played_matches[:count]
        return recent_matches
        
    except Exception as e:
        print(f"Ошибка при извлечении матчей: {e}")
    
    return matches

def extract_match_data_from_block(block):
    """Извлекает данные одного матча из блока"""
    try:
        # Ссылка на матч
        game_link = block.find('a', class_='game_link')
        if not game_link:
            return None
        
        # Дата и время
        status_div = game_link.find('div', class_='status')
        date_time = status_div.text.strip() if status_div else ''
        
        # Результат
        result_div = game_link.find('div', class_='result')
        if not result_div:
            return None
        
        # Команды и счет
        home_team_div = result_div.find('div', class_='ht')
        away_team_div = result_div.find('div', class_='at')
        
        if not home_team_div or not away_team_div:
            return None
        
        # Домашняя команда
        home_team_span = home_team_div.find('span')
        home_team = home_team_span.text.strip() if home_team_span else ''
        home_score_div = home_team_div.find('div', class_='gls')
        home_score = home_score_div.text.strip() if home_score_div else '-'
        
        # Гостевая команда  
        away_team_span = away_team_div.find('span')
        away_team = away_team_span.text.strip() if away_team_span else ''
        away_score_div = away_team_div.find('div', class_='gls')
        away_score = away_score_div.text.strip() if away_score_div else '-'
        
        # Турнир
        tournament = ''
        cmp_div = game_link.find('div', class_='cmp')
        if cmp_div:
            tournament_span = cmp_div.find('span')
            tournament = tournament_span.text.strip() if tournament_span else ''
        
        return {
            'date_time': date_time,
            'home_team': home_team,
            'away_team': away_team,
            'score_home': home_score,
            'score_away': away_score,
            'score': f"{home_score}:{away_score}",
            'tournament': tournament
        }
        
    except Exception as e:
        print(f"Ошибка при извлечении данных матча: {e}")
        return None

def convert_results_to_numeric(matches, team_name):
    """Конвертирует результаты матчей в числовой формат: 1-победа, 0.5-ничья, 0-поражение"""
    numeric_results = []
    
    print(f"Анализ результатов для команды: {team_name}")
    print(f"Упрощенное название: {simplify_team_name(team_name)}")
    
    for match in matches:
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        score_home = match.get('score_home', '-')
        score_away = match.get('score_away', '-')
        
        print(f"Матч: {home_team} {score_home}:{score_away} {away_team}")
        
        # Пропускаем матчи без счета
        if score_home == '-' or score_away == '-':
            print("  -> Пропуск: нет счета")
            continue
            
        try:
            home_score = int(score_home)
            away_score = int(score_away)
            
            # Упрощаем названия для сравнения
            simple_team_name = simplify_team_name(team_name)
            simple_home_team = simplify_team_name(home_team)
            simple_away_team = simplify_team_name(away_team)
            
            print(f"  Сравниваем: '{simple_team_name}' с домашней '{simple_home_team}' и гостевой '{simple_away_team}'")
            
            # Определяем результат для нашей команды
            if simple_team_name in simple_home_team or simple_home_team in simple_team_name:
                # Наша команда играла дома
                if home_score > away_score:
                    result = 1  # победа
                    print(f"  -> Победа домашней команды: {result}")
                elif home_score == away_score:
                    result = 0.5  # ничья
                    print(f"  -> Ничья: {result}")
                else:
                    result = 0  # поражение
                    print(f"  -> Поражение домашней команды: {result}")
                numeric_results.append(result)
                    
            elif simple_team_name in simple_away_team or simple_away_team in simple_team_name:
                # Наша команда играла в гостях
                if away_score > home_score:
                    result = 1  # победа
                    print(f"  -> Победа гостевой команды: {result}")
                elif away_score == home_score:
                    result = 0.5  # ничья
                    print(f"  -> Ничья: {result}")
                else:
                    result = 0  # поражение
                    print(f"  -> Поражение гостевой команды: {result}")
                numeric_results.append(result)
            else:
                # Не нашли команду в матче
                print(f"  -> Ошибка: команда не найдена в матче")
                # Попробуем определить по ключевым словам
                if "арсенал" in simple_home_team or "арсенал" in simple_away_team:
                    if "арсенал" in simple_home_team:
                        if home_score > away_score:
                            result = 1
                        elif home_score == away_score:
                            result = 0.5
                        else:
                            result = 0
                    else:
                        if away_score > home_score:
                            result = 1
                        elif away_score == home_score:
                            result = 0.5
                        else:
                            result = 0
                    numeric_results.append(result)
                    print(f"  -> Найдено по ключевому слову 'арсенал': {result}")
                else:
                    numeric_results.append(0.5)
                
        except ValueError as e:
            # Если не удалось преобразовать счет в число
            print(f"  -> Ошибка преобразования счета: {e}")
            numeric_results.append(0.5)
    
    print(f"Итоговые результаты: {numeric_results}")
    return numeric_results

def save_team_data(data, filename=None):
    """Сохраняет данные команды в JSON файл"""
    if not filename and data:
        # Создаем имя файла на основе названия команды
        safe_team_name = re.sub(r'[<>:"/\\|?*]', '_', data['team_name'])
        filename = f"data_{safe_team_name}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в файл: {filename}")
        return filename
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")
        return None

# Упрощенная версия для быстрого использования
def get_team_data_from_soccer365(url):
    """
    Упрощенная функция для получения данных команды с soccer365.ru
    Возвращает данные в формате для load_team_data
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Название команды из активной строки таблицы
        team_name = "Арсенал"  # fallback
        tables = soup.find_all('table', class_=lambda x: x and 'tablesorter' in x)
        for table in tables:
            active_row = table.find('tr', class_='active')
            if active_row:
                team_cells = active_row.find_all('td')
                if len(team_cells) > 1:
                    team_cell = team_cells[1]
                    team_link = team_cell.find('a')
                    if team_link:
                        team_name = team_link.text.strip()
                        break
        
        print(f"Найдена команда: {team_name}")
        
        # Позиция в лиге
        position = None
        for table in tables:
            active_row = table.find('tr', class_='active')
            if active_row:
                position_cell = active_row.find('td')
                if position_cell:
                    position_div = position_cell.find('div', class_='plc')
                    if position_div:
                        pos_match = re.search(r'(\d+)', position_div.text)
                        if pos_match:
                            position = int(pos_match.group(1))
                            print(f"Найдена позиция: {position}")
                            break
        
        # Последние матчи
        last_results = []
        schedule_block = soup.find('div', id='club_schedule')
        if schedule_block:
            game_blocks = schedule_block.find_all('div', class_='game_block')
            played_matches = []
            
            for block in game_blocks:
                result_div = block.find('div', class_='result')
                if result_div:
                    home_team_div = result_div.find('div', class_='ht')
                    away_team_div = result_div.find('div', class_='at')
                    
                    if home_team_div and away_team_div:
                        home_team_span = home_team_div.find('span')
                        away_team_span = away_team_div.find('span')
                        home_score_div = home_team_div.find('div', class_='gls')
                        away_score_div = away_team_div.find('div', class_='gls')
                        
                        if (home_team_span and away_team_span and 
                            home_score_div and away_score_div):
                            
                            home_team = home_team_span.text.strip()
                            away_team = away_team_span.text.strip()
                            home_score = home_score_div.text.strip()
                            away_score = away_score_div.text.strip()
                            
                            # Пропускаем будущие матчи
                            if home_score == '-' or away_score == '-':
                                continue
                            
                            try:
                                home_int = int(home_score)
                                away_int = int(away_score)
                                
                                print(f"Анализ матча: {home_team} {home_int}:{away_int} {away_team}")
                                
                                # Упрощаем названия для сравнения
                                simple_team_name = simplify_team_name(team_name)
                                simple_home_team = simplify_team_name(home_team)
                                simple_away_team = simplify_team_name(away_team)
                                
                                # Определяем результат для нашей команды
                                if simple_team_name in simple_home_team or simple_home_team in simple_team_name:
                                    # Наша команда играла дома
                                    if home_int > away_int:
                                        result = 1
                                        print("  -> Победа")
                                    elif home_int == away_int:
                                        result = 0.5
                                        print("  -> Ничья")
                                    else:
                                        result = 0
                                        print("  -> Поражение")
                                    played_matches.append(result)
                                elif simple_team_name in simple_away_team or simple_away_team in simple_team_name:
                                    # Наша команда играла в гостях
                                    if away_int > home_int:
                                        result = 1
                                        print("  -> Победа")
                                    elif away_int == home_int:
                                        result = 0.5
                                        print("  -> Ничья")
                                    else:
                                        result = 0
                                        print("  -> Поражение")
                                    played_matches.append(result)
                                else:
                                    # Пробуем найти по ключевому слову "арсенал"
                                    if "арсенал" in simple_home_team or "арсенал" in simple_away_team:
                                        if "арсенал" in simple_home_team:
                                            if home_int > away_int:
                                                result = 1
                                            elif home_int == away_int:
                                                result = 0.5
                                            else:
                                                result = 0
                                        else:
                                            if away_int > home_int:
                                                result = 1
                                            elif away_int == home_int:
                                                result = 0.5
                                            else:
                                                result = 0
                                        played_matches.append(result)
                                        print("  -> Найдено по ключевому слову")
                                    else:
                                        print("  -> Команда не найдена в матче")
                            except ValueError:
                                print("  -> Ошибка преобразования счета")
            
            # Берем последние 5 матчей
            last_results = played_matches[:5]
            print(f"Найдено результатов: {last_results}")
        
        return {
            'team_name': team_name,
            'position_in_league': position,
            'last_results': last_results
        }
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def main():
    # Пример использования для Арсенала
    url = "https://soccer365.ru/clubs/149/"
    
    print("Парсинг данных Арсенала...")
    team_data = get_team_data_from_soccer365(url)
    
    if team_data:
        print(f"\nРезультаты:")
        print(f"Команда: {team_data['team_name']}")
        print(f"Позиция в лиге: {team_data['position_in_league']}")
        print(f"Последние результаты: {team_data['last_results']}")
        
        # Сохраняем данные
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', team_data['team_name'])
        filename = f"data_{safe_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(team_data, f, ensure_ascii=False, indent=2)
        
        print(f"Данные сохранены в {filename}")
    else:
        print("Не удалось получить данные команды")

if __name__ == "__main__":
    main()