import requests
from bs4 import BeautifulSoup
import json
import re
import os
from pathlib import Path
import time
from datetime import datetime

def get_team_data_by_id(team_id, team_name):
    """
    Получает расширенные данные команды по её ID с soccer365.ru
    """
    try:
        url = f"https://soccer365.ru/clubs/{team_id}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"Запрос данных для {team_name} (ID: {team_id})...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  Ошибка HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Позиция в лиге
        position = None
        standings_table = soup.find('table', class_='stngs')
        if standings_table:
            for row in standings_table.find_all('tr'):
                team_link = row.find('a', href=f"/clubs/{team_id}/")
                if team_link:
                    first_cell = row.find('td')
                    if first_cell:
                        match = re.search(r'(\d+)', first_cell.text.strip())
                        if match:
                            position = int(match.group(1))
                            break
        
        # 2. Последние результаты
        last_results = get_team_last_results(soup, team_id, team_name)
        
        # 3. Статистика голов (НОВАЯ ФУНКЦИЯ)
        scoring_stats = calculate_team_scoring_stats(soup, team_id, team_name)
        
        # 4. Формируем статистику
        form_stats = {
            'total_matches': len(last_results),
            'wins': last_results.count(1),
            'draws': last_results.count(0.5),
            'losses': last_results.count(0),
            'points': last_results.count(1) * 3 + last_results.count(0.5),
            'form': ''.join(['W' if r == 1 else 'D' if r == 0.5 else 'L' for r in last_results])
        }
        
        # 5. Собираем все данные о команде
        team_data = {
            'team_id': team_id,
            'team_name': team_name,
            'team_url': url,
            'position_in_league': position,
            'last_results': last_results,
            'form_stats': form_stats,
            'scoring_stats': scoring_stats  # Добавляем новую статистику
        }
        
        print(f"✓ Данные получены: {team_name}")
        print(f"  Позиция: {position}, Форма: {form_stats['form']}")
        if scoring_stats:
            print(f"  Статистика голов: Дома - {scoring_stats['home']['avg_scored']:.2f} забито, {scoring_stats['home']['avg_conceded']:.2f} пропущено; "
                  f"В гостях - {scoring_stats['away']['avg_scored']:.2f} забито, {scoring_stats['away']['avg_conceded']:.2f} пропущено")
        
        return team_data
        
    except Exception as e:
        print(f"Ошибка для команды {team_name}: {str(e)[:100]}")
        return None

def get_team_last_results(soup, team_id, team_name):
    """
    Извлекает последние результаты команды из расписания.
    """
    last_results = []
    schedule_div = soup.find('div', id='club_schedule')
    
    if not schedule_div:
        return []
    
    game_blocks = schedule_div.find_all('div', class_='game_block')
    
    for block in game_blocks:
        score_divs = block.find_all('div', class_='gls')
        if len(score_divs) < 2:
            continue
        
        home_score_text = score_divs[0].text.strip()
        away_score_text = score_divs[1].text.strip()
        
        # Пропускаем будущие матчи
        if home_score_text == '-' or away_score_text == '-':
            continue
        
        if not re.match(r'^\d+$', home_score_text) or not re.match(r'^\d+$', away_score_text):
            continue
        
        try:
            home_score = int(home_score_text)
            away_score = int(away_score_text)
        except ValueError:
            continue
        
        home_div = block.find('div', class_='ht')
        away_div = block.find('div', class_='at')
        
        if not home_div or not away_div:
            continue
        
        home_span = home_div.find('span')
        away_span = away_div.find('span')
        
        if not home_span or not away_span:
            continue
        
        home_team = home_span.text.strip()
        away_team = away_span.text.strip()
        
        # Определяем, где играла наша команда
        home_team_link = home_div.find('a', href=f"/clubs/{team_id}/")
        away_team_link = away_div.find('a', href=f"/clubs/{team_id}/")
        
        is_home = (home_team_link is not None or 
                  team_name.lower() in home_team.lower() or 
                  home_team.lower() in team_name.lower())
        
        is_away = (away_team_link is not None or 
                  team_name.lower() in away_team.lower() or 
                  away_team.lower() in team_name.lower())
        
        if is_home:
            if home_score > away_score:
                result = 1
            elif home_score == away_score:
                result = 0.5
            else:
                result = 0
            last_results.append(result)
            
        elif is_away:
            if away_score > home_score:
                result = 1
            elif away_score == home_score:
                result = 0.5
            else:
                result = 0
            last_results.append(result)
    
    return last_results[:5]

def calculate_team_scoring_stats(soup, team_id, team_name):
    """
    Анализирует сыгранные матчи команды для расчета средней статистики голов:
    - Среднее количество забитых мячей дома (avg_scored_home)
    - Среднее количество пропущенных мячей дома (avg_conceded_home)
    - Среднее количество забитых мячей в гостях (avg_scored_away)
    - Среднее количество пропущенных мячей в гостях (avg_conceded_away)
    """
    home_matches = []  # Список словарей {'scored': X, 'conceded': Y} для домашних игр
    away_matches = []  # ... для гостевых игр
    
    schedule_div = soup.find('div', id='club_schedule')
    if not schedule_div:
        return None
    
    game_blocks = schedule_div.find_all('div', class_='game_block')
    
    for block in game_blocks:
        score_divs = block.find_all('div', class_='gls')
        if len(score_divs) < 2:
            continue
        
        home_score_text = score_divs[0].text.strip()
        away_score_text = score_divs[1].text.strip()
        
        # Анализируем ТОЛЬКО сыгранные матчи (есть счет)
        if home_score_text == '-' or away_score_text == '-':
            continue
        
        if not re.match(r'^\d+$', home_score_text) or not re.match(r'^\d+$', away_score_text):
            continue
        
        try:
            home_score = int(home_score_text)
            away_score = int(away_score_text)
        except ValueError:
            continue
        
        home_div = block.find('div', class_='ht')
        away_div = block.find('div', class_='at')
        
        if not home_div or not away_div:
            continue
        
        home_span = home_div.find('span')
        away_span = away_div.find('span')
        
        if not home_span or not away_span:
            continue
        
        # Определяем, где играла наша команда
        home_team_link = home_div.find('a', href=f"/clubs/{team_id}/")
        away_team_link = away_div.find('a', href=f"/clubs/{team_id}/")
        
        is_home = (home_team_link is not None or 
                  team_name.lower() in home_span.text.strip().lower())
        
        is_away = (away_team_link is not None or 
                  team_name.lower() in away_span.text.strip().lower())
        
        if is_home:
            # Наша команда играла дома: home_score - наши голы, away_score - голы соперника
            home_matches.append({
                'scored': home_score,
                'conceded': away_score
            })
        elif is_away:
            # Наша команда играла в гостях: away_score - наши голы, home_score - голы соперника
            away_matches.append({
                'scored': away_score,
                'conceded': home_score
            })
    
    # Рассчитываем средние показатели
    def calculate_avg(matches_list):
        if not matches_list:
            return {'avg_scored': 0.0, 'avg_conceded': 0.0, 'matches_count': 0}
        total_scored = sum(m['scored'] for m in matches_list)
        total_conceded = sum(m['conceded'] for m in matches_list)
        count = len(matches_list)
        return {
            'avg_scored': total_scored / count,
            'avg_conceded': total_conceded / count,
            'matches_count': count
        }
    
    home_stats = calculate_avg(home_matches)
    away_stats = calculate_avg(away_matches)
    
    # Формируем итоговую структуру
    scoring_stats = {
        'home': home_stats,
        'away': away_stats,
        'overall': {
            'avg_scored': (home_stats['avg_scored'] * home_stats['matches_count'] + away_stats['avg_scored'] * away_stats['matches_count']) / max((home_stats['matches_count'] + away_stats['matches_count']), 1),
            'avg_conceded': (home_stats['avg_conceded'] * home_stats['matches_count'] + away_stats['avg_conceded'] * away_stats['matches_count']) / max((home_stats['matches_count'] + away_stats['matches_count']), 1),
            'total_matches': home_stats['matches_count'] + away_stats['matches_count']
        }
    }
    
    # Выводим отчет о найденных матчах
    print(f"    Для статистики голов найдено: {home_stats['matches_count']} домашних и {away_stats['matches_count']} гостевых матчей.")
    
    return scoring_stats

def process_teams_from_file(file_path):
    """
    Обрабатывает файл с матчами и парсит данные команд.
    Теперь также создает папки для каждого матча.
    """
    try:
        print(f"\n{'='*60}")
        print(f"Обработка файла: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Извлекаем команды из матчей
        teams = []
        seen_ids = set()
        # Также сохраняем информацию о матчах для создания папок
        matches_info = []
        
        if "matches" in data:
            for match in data["matches"]:
                match_name = match.get('match', f"{match.get('home_team', 'Команда1')} - {match.get('away_team', 'Команда2')}")
                matches_info.append({
                    'match_name': match_name,
                    'home_id': str(match.get('home_team_id', '')),
                    'away_id': str(match.get('away_team_id', ''))
                })
                
                # Домашняя команда
                if "home_team_id" in match and match["home_team_id"] and match["home_team_id"] not in seen_ids:
                    teams.append({
                        'id': str(match["home_team_id"]),
                        'name': match["home_team"]
                    })
                    seen_ids.add(match["home_team_id"])
                
                # Гостевая команда
                if "away_team_id" in match and match["away_team_id"] and match["away_team_id"] not in seen_ids:
                    teams.append({
                        'id': str(match["away_team_id"]),
                        'name': match["away_team"]
                    })
                    seen_ids.add(match["away_team_id"])
        
        print(f"Найдено команд: {len(teams)}")
        print(f"Найдено матчей: {len(matches_info)}")
        
        # Парсим данные для каждой команды
        teams_data = []
        team_data_by_id = {}  # Кэш для быстрого доступа по ID
        
        for team in teams:
            print(f"\n--- Команда: {team['name']} (ID: {team['id']}) ---")
            
            time.sleep(0.5)  # Задержка между запросами
            
            team_data = get_team_data_by_id(team['id'], team['name'])
            
            if team_data:
                team_data['league'] = data.get('league', 'Неизвестная лига')
                team_data['league_id'] = data.get('league_id', 'unknown')
                team_data['scraped_at'] = datetime.now().isoformat()
                
                teams_data.append(team_data)
                team_data_by_id[team['id']] = team_data
            else:
                print(f"✗ Не удалось получить данные")
        
        # СОЗДАНИЕ ПАПОК И ФАЙЛОВ ДЛЯ КАЖДОГО МАТЧА (НОВОЕ)
        print(f"\n{'='*60}")
        print("Создание папок и файлов для анализа матчей...")
        
        for match in matches_info:
            match_name = match['match_name']
            home_id = match['home_id']
            away_id = match['away_id']
            
            # Получаем данные обеих команд из кэша
            home_data = team_data_by_id.get(home_id)
            away_data = team_data_by_id.get(away_id)
            
            if not home_data or not away_data:
                print(f"  Пропускаем матч '{match_name}': отсутствуют данные одной из команд.")
                continue
            
            # Создаем безопасное имя для папки
            safe_match_name = re.sub(r'[<>:"/\\|?*]', '_', match_name)
            match_folder = os.path.join("commands", safe_match_name)
            os.makedirs(match_folder, exist_ok=True)
            
            # Формируем аналитику матча
            match_analysis = {
                'match': match_name,
                'match_url': data.get('league_url', ''),
                'date_time': next((m.get('date_time', '') for m in data.get('matches', []) if m.get('match') == match_name), ''),
                'league': data.get('league', ''),
                'analysis_date': datetime.now().isoformat(),
                'home_team': home_data,
                'away_team': away_data,
                # Простая сравнительная аналитика на основе новых данных
                'comparison': {
                    'position_difference': (home_data.get('position_in_league') or 20) - (away_data.get('position_in_league') or 20),
                    'home_team_form': home_data.get('form_stats', {}).get('form', ''),
                    'away_team_form': away_data.get('form_stats', {}).get('form', ''),
                    'scoring_insight': f"В среднем {home_data['team_name']} забивает дома {home_data.get('scoring_stats', {}).get('home', {}).get('avg_scored', 0):.2f} мяча, "
                                       f"а {away_data['team_name']} в гостях пропускает {away_data.get('scoring_stats', {}).get('away', {}).get('avg_conceded', 0):.2f} мяча."
                }
            }
            
            # Сохраняем анализ матча в папку
            match_file = os.path.join(match_folder, f"{safe_match_name}_analysis.json")
            with open(match_file, 'w', encoding='utf-8') as f:
                json.dump(match_analysis, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ Создана папка и файл анализа для матча: {match_name}")
        
        return teams_data
        
    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("="*60)
    print("РАСШИРЕННЫЙ ПАРСЕР РЕЗУЛЬТАТОВ И СТАТИСТИКИ КОМАНД")
    print("="*60)
    
    # УКАЖИТЕ ПРАВИЛЬНЫЙ ПУТЬ К ВАШЕМУ ФАЙЛУ
    matches_file = "competitions/17/upcoming_matches_Чемпионат Германии по футболу 2025_2026, Бундеслига.json"
    
    if not os.path.exists(matches_file):
        print(f"Файл не найден: {matches_file}")
        print("Проверьте путь к файлу и запустите скрипт снова.")
        return
    
    # Обрабатываем файл
    teams_data = process_teams_from_file(matches_file)
    
    if teams_data:
        # Сохраняем сводные результаты по всем командам
        output_file = "all_teams_detailed_stats.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print("ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
        print('='*60)
        print(f"✓ Сводные данные по всем командам сохранены в: {output_file}")
        print(f"✓ Обработано команд: {len(teams_data)}")
        print(f"✓ Для каждого матча создана отдельная папка в директории 'commands/'")
        
        # Итоговая статистика
        teams_with_stats = sum(1 for t in teams_data if t.get('scoring_stats'))
        print(f"✓ Команд со статистикой голов: {teams_with_stats}")
        
    else:
        print("\n✗ Не удалось получить данные ни по одной команде.")

if __name__ == "__main__":
    main()

# import requests
# from bs4 import BeautifulSoup
# import json
# import re
# import os
# from pathlib import Path
# import time
# from datetime import datetime

# def get_team_data_by_id(team_id, team_name):
#     """
#     Получает данные команды по её ID с soccer365.ru
#     """
#     try:
#         url = f"https://soccer365.ru/clubs/{team_id}/"
        
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#         }
        
#         print(f"Запрос данных для {team_name} (ID: {team_id})...")
#         response = requests.get(url, headers=headers, timeout=10)
        
#         if response.status_code != 200:
#             print(f"  Ошибка HTTP {response.status_code}")
#             return None
        
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         # 1. Позиция в лиге
#         position = None
#         standings_table = soup.find('table', class_='stngs')
#         if standings_table:
#             # Ищем строку с нашей командой
#             for row in standings_table.find_all('tr'):
#                 team_link = row.find('a', href=f"/clubs/{team_id}/")
#                 if team_link:
#                     first_cell = row.find('td')
#                     if first_cell:
#                         match = re.search(r'(\d+)', first_cell.text.strip())
#                         if match:
#                             position = int(match.group(1))
#                             break
        
#         if position:
#             print(f"  Позиция в лиге: {position}")
#         else:
#             print(f"  Позиция не найдена")
        
#         # 2. Последние результаты
#         last_results = get_team_last_results(soup, team_id, team_name)
        
#         # 3. Формируем статистику
#         form_stats = {
#             'total_matches': len(last_results),
#             'wins': last_results.count(1),
#             'draws': last_results.count(0.5),
#             'losses': last_results.count(0),
#             'points': last_results.count(1) * 3 + last_results.count(0.5),
#             'form': ''.join(['W' if r == 1 else 'D' if r == 0.5 else 'L' for r in last_results])
#         }
        
#         team_data = {
#             'team_id': team_id,
#             'team_name': team_name,
#             'team_url': url,
#             'position_in_league': position,
#             'last_results': last_results,
#             'form_stats': form_stats
#         }
        
#         print(f"✓ Данные получены: {team_name}")
#         print(f"  Результаты: {last_results}, Форма: {form_stats['form']}")
        
#         return team_data
        
#     except Exception as e:
#         print(f"Ошибка для команды {team_name}: {str(e)[:100]}")
#         return None

# def get_team_last_results(soup, team_id, team_name):
#     """
#     Извлекает последние результаты команды из расписания
#     """
#     last_results = []
    
#     # Находим блок с расписанием
#     schedule_div = soup.find('div', id='club_schedule')
#     if not schedule_div:
#         print(f"  Блок club_schedule не найден")
#         return []
    
#     # Находим все матчи
#     game_blocks = schedule_div.find_all('div', class_='game_block')
#     print(f"  Всего матчей на странице: {len(game_blocks)}")
    
#     for i, block in enumerate(game_blocks):
#         # Пропускаем будущие матчи (с тире в счете)
#         score_divs = block.find_all('div', class_='gls')
#         if len(score_divs) < 2:
#             continue
        
#         home_score_text = score_divs[0].text.strip()
#         away_score_text = score_divs[1].text.strip()
        
#         # Пропускаем будущие матчи
#         if home_score_text == '-' or away_score_text == '-':
#             continue
        
#         # Проверяем, что это цифры
#         if not re.match(r'^\d+$', home_score_text) or not re.match(r'^\d+$', away_score_text):
#             continue
        
#         try:
#             home_score = int(home_score_text)
#             away_score = int(away_score_text)
#         except ValueError:
#             continue
        
#         # Находим названия команд
#         home_div = block.find('div', class_='ht')
#         away_div = block.find('div', class_='at')
        
#         if not home_div or not away_div:
#             continue
        
#         # Получаем названия команд
#         home_span = home_div.find('span')
#         away_span = away_div.find('span')
        
#         if not home_span or not away_span:
#             continue
        
#         home_team = home_span.text.strip()
#         away_team = away_span.text.strip()
        
#         # Определяем, где играла наша команда
#         # Проверяем по ID в ссылках
#         home_team_link = home_div.find('a', href=f"/clubs/{team_id}/")
#         away_team_link = away_div.find('a', href=f"/clubs/{team_id}/")
        
#         # Или проверяем по названию (для надежности)
#         is_home = (home_team_link is not None or 
#                   team_name.lower() in home_team.lower() or 
#                   home_team.lower() in team_name.lower())
        
#         is_away = (away_team_link is not None or 
#                   team_name.lower() in away_team.lower() or 
#                   away_team.lower() in team_name.lower())
        
#         if is_home:
#             # Наша команда играла дома
#             if home_score > away_score:
#                 result = 1  # победа
#             elif home_score == away_score:
#                 result = 0.5  # ничья
#             else:
#                 result = 0  # поражение
            
#             last_results.append(result)
#             print(f"    Матч {i+1}: {home_team} {home_score}:{away_score} {away_team} - результат: {result}")
            
#         elif is_away:
#             # Наша команда играла в гостях
#             if away_score > home_score:
#                 result = 1  # победа
#             elif away_score == home_score:
#                 result = 0.5  # ничья
#             else:
#                 result = 0  # поражение
            
#             last_results.append(result)
#             print(f"    Матч {i+1}: {home_team} {home_score}:{away_score} {away_team} - результат: {result}")
    
#     # Берем только последние 5 матчей
#     return last_results[:5]

# def process_teams_from_file(file_path):
#     """
#     Обрабатывает файл с матчами и парсит данные команд
#     """
#     try:
#         print(f"\n{'='*60}")
#         print(f"Обработка файла: {file_path}")
        
#         with open(file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
        
#         # Извлекаем команды из матчей
#         teams = []
#         seen_ids = set()
        
#         if "matches" in data:
#             for match in data["matches"]:
#                 # Домашняя команда
#                 if "home_team_id" in match and match["home_team_id"] and match["home_team_id"] not in seen_ids:
#                     teams.append({
#                         'id': str(match["home_team_id"]),
#                         'name': match["home_team"]
#                     })
#                     seen_ids.add(match["home_team_id"])
                
#                 # Гостевая команда
#                 if "away_team_id" in match and match["away_team_id"] and match["away_team_id"] not in seen_ids:
#                     teams.append({
#                         'id': str(match["away_team_id"]),
#                         'name': match["away_team"]
#                     })
#                     seen_ids.add(match["away_team_id"])
        
#         print(f"Найдено команд: {len(teams)}")
        
#         # Парсим данные для каждой команды
#         teams_data = []
        
#         for team in teams:
#             print(f"\n--- Команда: {team['name']} (ID: {team['id']}) ---")
            
#             # Задержка между запросами
#             time.sleep(0.5)
            
#             team_data = get_team_data_by_id(team['id'], team['name'])
            
#             if team_data:
#                 # Добавляем информацию о лиге
#                 team_data['league'] = data.get('league', 'Неизвестная лига')
#                 team_data['league_id'] = data.get('league_id', 'unknown')
#                 team_data['scraped_at'] = datetime.now().isoformat()
                
#                 teams_data.append(team_data)
#             else:
#                 print(f"✗ Не удалось получить данные")
        
#         return teams_data
        
#     except Exception as e:
#         print(f"Ошибка при обработке файла: {e}")
#         return []

# def main():
#     print("="*60)
#     print("ПАРСЕР РЕЗУЛЬТАТОВ КОМАНД")
#     print("="*60)
    
#     # Путь к файлу с матчами
#     # matches_file = "competitions/723/upcoming_matches_Чемпионат Турции по футболу 2025_2026, Суперлига.json"
    
#     if not os.path.exists(matches_file):
#         print(f"Файл не найден: {matches_file}")
#         return
    
#     # Обрабатываем файл
#     teams_data = process_teams_from_file(matches_file)
    
#     if teams_data:
#         # Сохраняем результаты
#         output_file = "teams_results.json"
#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(teams_data, f, ensure_ascii=False, indent=2)
        
#         print(f"\n✓ Данные сохранены в {output_file}")
#         print(f"✓ Обработано команд: {len(teams_data)}")
        
#         # Статистика
#         with_results = sum(1 for t in teams_data if t['last_results'])
#         print(f"✓ Команд с результатами: {with_results}")
        
#         # Пример вывода
#         print(f"\nПримеры результатов:")
#         for team in teams_data[:3]:
#             if team['last_results']:
#                 print(f"{team['team_name']}: {team['last_results']} (форма: {team['form_stats']['form']})")
#     else:
#         print("\n✗ Не удалось получить данные")

# if __name__ == "__main__":
#     main()