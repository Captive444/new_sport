import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)
# замена 25102025
# def calculate_exact_scores(team1: Dict, team2: Dict, max_goals=5):
#     """Расчет вероятностей точного счета"""
#     # Среднее ожидаемое количество голов для каждой команды
#     mean_team1 = 0.8 * team1["attack_strength"] / team2["defense_strength"]
#     mean_team2 = 1.2 * team2["attack_strength"] / team1["defense_strength"]
    
#     # Корректировка на домашнее поле
#     if team1["is_home"]:
#         mean_team1 *= 1.2
#         mean_team2 *= 0.9
#     else:
#         mean_team1 *= 0.9
#         mean_team2 *= 1.2

# def calculate_exact_scores(team1: Dict, team2: Dict, max_goals=5):
#     # Увеличить вес обороны
#     mean_team1 = 0.7 * team1["attack_strength"] / (team2["defense_strength"] + 0.3)
#     mean_team2 = 0.7 * team2["attack_strength"] / (team1["defense_strength"] + 0.3)
    
#     # Сильнее корректировка на позицию в таблице
#     if team1["position_in_league"] <= 3 and team2["position_in_league"] >= 10:
#         mean_team1 *= 1.3  # Лидер против аутсайдера
#         mean_team2 *= 0.7
    
#     # Рассчитываем вероятности для всех возможных счетов
#     scores = {}
#     for i in range(max_goals + 1):
#         for j in range(max_goals + 1):
#             prob = poisson_probability(mean_team1, i) * poisson_probability(mean_team2, j)
#             scores[f"{i}-{j}"] = round(prob, 4)
    
#     # Нормализуем вероятности
#     total = sum(scores.values())
#     return {score: prob/total for score, prob in scores.items()}
def calculate_exact_scores(team1: Dict, team2: Dict, max_goals=5):
    """ИСПРАВЛЕННЫЙ расчет точных счетов"""
    # Увеличиваем среднее количество голов
    mean_team1 = 1.1 * team1["attack_strength"] / (team2["defense_strength"] + 0.1)
    mean_team2 = 1.1 * team2["attack_strength"] / (team1["defense_strength"] + 0.1)
    
    # Домашнее преимущество
    if team1["is_home"]:
        mean_team1 *= 1.3
        mean_team2 *= 0.9
    else:
        mean_team1 *= 0.9
        mean_team2 *= 1.3
    
    # Корректировка на позицию
    if team1["position_in_league"] <= 3 and team2["position_in_league"] >= 10:
        mean_team1 *= 1.2
    elif team2["position_in_league"] <= 3 and team1["position_in_league"] >= 10:
        mean_team2 *= 1.2
    
    # Минимальные значения для избежания 0-0
    mean_team1 = max(0.4, mean_team1)
    mean_team2 = max(0.4, mean_team2)
    
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_team1, i) * poisson_probability(mean_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}

def load_team_data(file_path: str, is_home: bool, position_in_league: int, last_results: Optional[List[int]] = None) -> Dict:
    """Загружает данные команды из JSON файла с расширенной аналитикой"""
    with open(file_path, 'r', encoding='utf-8') as f:
        players = json.load(f)
    
    if not players:
        return {
            'name': file_path.replace('.json', ''),
            'is_home': is_home,
            'position_in_league': position_in_league,
            'last_results': last_results or [],
            'players': [],
            'avg_readiness': 0.5,
            'attack_strength': 0.5,
            'defense_strength': 0.5,
            'top_attackers': []
        }
    
    # Рассчитываем показатели команды
    readiness = []
    defense = []
    attackers = []
    
    for player in players:
        pos = player['position'].lower()
        readiness.append(player['readiness'])
        
        if 'вратарь' in pos:
            defense.append(player['readiness'] * 1.2)  # Усиленный вес вратарей
        elif 'защитник' in pos:
            defense.append(player['readiness'] * 0.8)
        elif 'нап' in pos or 'вингер' in pos:
            attackers.append(player['readiness'])
        elif 'полузащитник' in pos:
            defense.append(player['readiness'] * 0.4)
            attackers.append(player['readiness'] * 0.6)
    
    # Топ-3 атакующих игрока (если есть)
    top_attackers = sorted(attackers, reverse=True)[:3] if attackers else [0.3]
    
    # Учёт формы (последние 5 матчей: 1-победа, 0-поражение, 0.5-ничья)
    form_coefficient = 1.0
    if last_results:
        form_coefficient = 0.9 + (sum(last_results) / len(last_results)) * 0.2
    
    return {
        'name': file_path.replace('.json', ''),
        'is_home': is_home,
        'position_in_league': position_in_league,
        'last_results': last_results or [],
        'players': players,
        'avg_readiness': np.mean(readiness) if readiness else 0.5,
        'attack_strength': np.mean(top_attackers) * form_coefficient,
        'defense_strength': np.mean(defense) if defense else 0.5,
        'top_attackers': top_attackers,
        'form_coefficient': form_coefficient
    }

def calculate_motivation(team: Dict, match_type: str) -> float:
    """Усовершенствованный расчёт мотивации"""
    base_motivation = {
        'вылет': 0.25,
        'еврокубки': 0.2,
        'дерби': 0.15,
        'кубок': 0.15,
        'клубный_чемпионат': 0.2,
        'обычный': 0.05
    }.get(match_type, 0.05)
    
    position = team.get('position_in_league', 1)
    if position >= 18:  # Зона прямого вылета
        base_motivation += 0.15
    elif 16 <= position <= 17:  # Зона плей-офф вылета
        base_motivation += 0.10
    elif position <= 4:  # Лига чемпионов
        base_motivation += 0.12 if match_type != 'вылет' else 0.05
    elif 5 <= position <= 6:  # Лига Европы
        base_motivation += 0.08
    elif 7 <= position <= 9:  # Конференционная лига
        base_motivation += 0.05
    elif 10 <= position <= 15:  # Середняки
        base_motivation += 0.02
    
    # Учёт формы
    if team.get('last_results'):
        win_rate = sum(team['last_results']) / len(team['last_results'])
        if win_rate > 0.7:
            base_motivation += 0.05
        elif win_rate < 0.3:
            base_motivation -= 0.03
    
    return min(0.35, max(0.0, base_motivation))
# изменил 25102025
# def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
#     """Улучшенный расчёт вероятностей с учётом всех факторов"""
#     # 1. Корректировки силы команд
#     home_advantage = 0.1 if team1["position_in_league"] < 10 else 0.05
#     weather_impact = {
#         "rain": -0.02,
#         "sunny": 0.03,
#         "windy": -0.01,
#         "snow": -0.03,
#         None: 0.0
#     }.get(weather, 0.0)
    
#     # 2. Мотивация с учётом формы
#     team1_motivation = calculate_motivation(team1, match_type)
#     team2_motivation = calculate_motivation(team2, match_type)
    
#     # 3. Итоговые показатели
#     team1_power = (
#         team1["avg_readiness"] * 0.4 +
#         team1["attack_strength"] * 0.4 +
#         team1["defense_strength"] * 0.2 +
#         home_advantage +
#         team1_motivation
#     )
    
#     team2_power = (
#         team2["avg_readiness"] * 0.4 +
#         team2["attack_strength"] * 0.4 +
#         team2["defense_strength"] * 0.2 -
#         home_advantage * 0.6 +
#         team2_motivation
#     )
    
#     # 4. Разница в силе
#     diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
# def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
#     # 1. Корректировки силы команд
#     home_advantage = 0.1 if team1["position_in_league"] < 10 else 0.05
#     weather_impact = {
#         "rain": -0.02, "sunny": 0.03, "windy": -0.01, "snow": -0.03, None: 0.0
#     }.get(weather, 0.0)
    
#     # 2. Мотивация с учётом формы
#     team1_motivation = calculate_motivation(team1, match_type)
#     team2_motivation = calculate_motivation(team2, match_type)
    
#     # 3. Итоговые показатели с НОВЫМИ весами
#     team1_power = (
#         team1["avg_readiness"] * 0.3 +           # 30% готовность
#         team1["attack_strength"] * 0.35 +        # 35% атака
#         team1["defense_strength"] * 0.35 +       # 35% защита
#         home_advantage * 0.8 +                   # скорректированное домашнее преимущество
#         team1_motivation * 1.2                   # усиленная мотивация
#     )
    
#     team2_power = (
#         team2["avg_readiness"] * 0.3 +           # 30% готовность  
#         team2["attack_strength"] * 0.35 +        # 35% атака
#         team2["defense_strength"] * 0.35 +       # 35% защита
#         -home_advantage * 0.6 +                  # гостевой недостаток (меньше)
#         team2_motivation * 1.2                   # усиленная мотивация
#     )
    
#     # 4. Разница в силе
#     diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
    
#     # ... остальной код без изменений   
#     # 5. Основные прогнозы
#     forecasts = {
#         "1X2": {
#             "П1": max(0.1, min(0.9, 0.45 + diff * 0.6)),
#             "X": max(0.1, min(0.9, 0.3 - abs(diff) * 0.7)),
#             "П2": max(0.1, min(0.9, 0.25 - diff * 0.6))
#         },
#         # "Тоталы": {
#         #     ">1.5": 0.65 + (team1["attack_strength"] + team2["attack_strength"]) * 0.25 + weather_impact,
#         #     "<1.5": 0.35 - (team1["attack_strength"] + team2["attack_strength"]) * 0.25 - weather_impact,
#         #     ">2.5": 0.55 + (team1["attack_strength"] + team2["attack_strength"]) * 0.2 + weather_impact * 0.7,
#         #     "<2.5": 0.45 - (team1["attack_strength"] + team2["attack_strength"]) * 0.2 - weather_impact * 0.7,
#         #     ">3.5": 0.4 + (team1["attack_strength"] + team2["attack_strength"]) * 0.15 + weather_impact * 0.5
#         # },
#         "Тоталы": {
#             ">1.5": 0.55 + (team1["attack_strength"] + team2["attack_strength"]) * 0.15,
#             "<1.5": 0.45 - (team1["attack_strength"] + team2["attack_strength"]) * 0.15,
#             ">2.5": 0.45 + (team1["attack_strength"] + team2["attack_strength"]) * 0.15,
#             "<2.5": 0.55 - (team1["attack_strength"] + team2["attack_strength"]) * 0.15,
#         },
#         "Форы": {
#             "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.4),
#             "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.4),
#             "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.5),
#             "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.5)
#         },
#         "Обе забьют": {
#             "Да": min(0.95, max(0.05,
#                 (team1["attack_strength"] * 0.6 + team2["attack_strength"] * 0.6) * 0.6 - weather_impact * 0.1
#             )),
#             "Нет": 1 - (team1["attack_strength"] * 0.6 + team2["attack_strength"] * 0.6) * 0.6 + weather_impact * 0.1
#         },
#         "Первый гол": {
#             "1": team1["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
#             "2": team2["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
#             "Нет": 0.15
#         },
#         "Точный счет": {}
#     }
    
#     # Нормализация
#     forecasts["1X2"] = {k: v / sum(forecasts["1X2"].values()) for k, v in forecasts["1X2"].items()}
#     for market in ["Тоталы", "Форы"]:
#         forecasts[market] = {k: max(0.05, min(0.95, v)) for k, v in forecasts[market].items()}
    
#     # Учёт звёздных игроков
#     if len(team1["top_attackers"]) >= 1 and team1["top_attackers"][0] > 0.6:
#         forecasts["1X2"]["П1"] *= 1.1
#         forecasts["Тоталы"][">2.5"] *= 1.15
    
#     if len(team2["top_attackers"]) >= 1 and team2["top_attackers"][0] > 0.6:
#         forecasts["1X2"]["П2"] *= 1.1
#         forecasts["Тоталы"][">2.5"] *= 1.15
    
#     # Добавляем расчет точного счета
#     forecasts["Точный счет"] = calculate_exact_scores(team1, team2)
#     forecasts["Точный счет"] = dict(sorted(
#         forecasts["Точный счет"].items(),
#         key=lambda item: item[1],
#         reverse=True
#     )[:10])  # Топ-10 вероятных счетов
    
#     return forecasts
def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """ИСПРАВЛЕННАЯ версия с балансировкой атаки/защиты"""
    
    home_advantage = 0.12 if team1["position_in_league"] < 10 else 0.06
    weather_impact = {
        "rain": -0.03, "sunny": 0.02, "windy": -0.02, "snow": -0.05, None: 0.0
    }.get(weather, 0.0)
    
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    
    # ИСПРАВЛЕННЫЕ веса (больше атаки, меньше защиты)
    team1_power = (
        team1["avg_readiness"] * 0.3 +           # 30% готовность
        team1["attack_strength"] * 0.45 +        # 45% атака ⬆️
        team1["defense_strength"] * 0.25 +       # 25% защита ⬇️
        home_advantage +
        team1_motivation * 1.2
    )
    
    team2_power = (
        team2["avg_readiness"] * 0.3 +
        team2["attack_strength"] * 0.45 +        # 45% атака ⬆️
        team2["defense_strength"] * 0.25 +       # 25% защита ⬇️
        -home_advantage * 0.7 +
        team2_motivation * 1.2
    )
    
    diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
    
    # ИСПРАВЛЕННЫЕ тоталы (более агрессивные)
    base_attack = team1["attack_strength"] + team2["attack_strength"]
    
    forecasts = {
        "1X2": {
            "П1": max(0.1, min(0.9, 0.45 + diff * 0.6)),
            "X": max(0.1, min(0.9, 0.3 - abs(diff) * 0.7)),
            "П2": max(0.1, min(0.9, 0.25 - diff * 0.6))
        },
        "Тоталы": {
            ">1.5": 0.6 + base_attack * 0.25,           # ⬆️ больше голов
            "<1.5": 0.4 - base_attack * 0.25,
            ">2.5": 0.35 + base_attack * 0.4,           # ⬆️ значительно больше
            "<2.5": 0.65 - base_attack * 0.4,
        },
        "Форы": {
            "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.4),
            "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.4),
            "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.5),
            "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.5)
        },
        "Обе забьют": {
            "Да": min(0.95, max(0.05,
                (team1["attack_strength"] * 0.7 + team2["attack_strength"] * 0.7) * 0.7  # ⬆️
            )),
            "Нет": 1 - min(0.95, max(0.05,
                (team1["attack_strength"] * 0.7 + team2["attack_strength"] * 0.7) * 0.7
            ))
        },
        "Первый гол": {
            "1": team1["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
            "2": team2["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
            "Нет": 0.08  # ⬇️ меньше вероятности отсутствия голов
        },
        "Точный счет": {}
    }
    
    # Нормализация
    forecasts["1X2"] = {k: v / sum(forecasts["1X2"].values()) for k, v in forecasts["1X2"].items()}
    
    # Звездные игроки дают меньший бонус
    if len(team1["top_attackers"]) >= 1 and team1["top_attackers"][0] > 0.6:
        forecasts["1X2"]["П1"] *= 1.08  # ⬇️ меньше бонус
        forecasts["Тоталы"][">2.5"] *= 1.08
    
    if len(team2["top_attackers"]) >= 1 and team2["top_attackers"][0] > 0.6:
        forecasts["1X2"]["П2"] *= 1.08
        forecasts["Тоталы"][">2.5"] *= 1.08
    
    forecasts["Точный счет"] = calculate_exact_scores(team1, team2)
    forecasts["Точный счет"] = dict(sorted(
        forecasts["Точный счет"].items(),
        key=lambda item: item[1],
        reverse=True
    )[:10])
    
    return forecasts

if __name__ == "__main__":
    # Пример данных
    team1 = load_team_data(
        "output_with_readiness_1.json",
        is_home=True,
        position_in_league=13,
        last_results=[0, 0, 0, 0.5, 0.5]
    )
    
    team2 = load_team_data(
        "output_with_readiness_2.json",
        is_home=False,
        position_in_league=3,
        last_results=[1, 1, 1, 0.5, 0.5]
    )
    
    # Рассчитываем вероятности
    forecast = calculate_match_probabilities(
        team1=team1,
        team2=team2,
        weather="sunny",
        match_type="обычный"
    )
    
    # Выводим результаты
    print(f"\nПрогноз на матч: {team1['name']} vs {team2['name']}")
    print(f"Рейтинг силы: {team1['name']} {team1['attack_strength']:.2f} | {team2['name']} {team2['attack_strength']:.2f}")
    
    for market, values in forecast.items():
        print(f"\n{market}:")
        for bet_type, prob in values.items():
            print(f"  {bet_type}: {prob:.4f}" if market == "Точный счет" else f"  {bet_type}: {prob:.2f}") 

# 222222222222222222222

# import json
# import numpy as np
# from typing import Dict, List

# def load_team_data(file_path: str, is_home: bool, position_in_league: int) -> Dict:
#     """Загружает данные команды из JSON файла и добавляет мета-информацию"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         players = json.load(f)
    
#     if not players:
#         return {
#             'name': file_path.replace('.json', ''),
#             'is_home': is_home,
#             'position_in_league': position_in_league,
#             'players': [],
#             'avg_readiness': 0.5,
#             'attack_strength': 0.5,
#             'defense_strength': 0.5
#         }
    
#     # Рассчитываем средние показатели команды
#     readiness = []
#     attack = []
#     defense = []
    
#     for player in players:
#         pos = player['position'].lower()
#         readiness.append(player['readiness'])
        
#         if 'вратарь' in pos:
#             defense.append(player['readiness'])
#         elif 'защитник' in pos:
#             defense.append(player['readiness'] * 0.7)
#             attack.append(player['readiness'] * 0.3)
#         elif 'нап' in pos or 'вингер' in pos:
#             attack.append(player['readiness'])
#         else:  # полузащитники
#             attack.append(player['readiness'] * 0.6)
#             defense.append(player['readiness'] * 0.4)
    
#     return {
#         'name': file_path.replace('.json', ''),
#         'is_home': is_home,
#         'position_in_league': position_in_league,
#         'players': players,
#         'avg_readiness': np.mean(readiness) if readiness else 0.5,
#         'attack_strength': np.mean(attack) if attack else 0.5,
#         'defense_strength': np.mean(defense) if defense else 0.5
#     }

# def calculate_motivation(team: Dict, match_type: str) -> float:
#     """Рассчитывает мотивационный коэффициент команды"""
#     motivation_rules = {
#         'вылет': 0.2,
#         'еврокубки': 0.15,
#         'дерби': 0.1,
#         'кубок': 0.1,
#          'клубный_чемпионат': 0.15,
#         'обычный': 0.0
#     }
    
#     base_motivation = motivation_rules.get(match_type, 0.0)
    
#     # Учёт позиции в лиге
#     if team.get('position_in_league', 1) > 14:  # Аутсайдеры
#         base_motivation += 0.05
#     elif team.get('position_in_league', 1) < 5:  # Топ-клубы
#         base_motivation += 0.03
    
#     return min(0.3, max(0.0, base_motivation))

# def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
#     """
#     Рассчитывает вероятности исходов матча с учетом мотивации и погоды.
    
#     Параметры:
#         team1, team2: Данные команд
#         weather: 'rain', 'sunny', 'windy'
#         match_type: 'вылет', 'еврокубки', 'дерби', 'кубок', 'обычный'
    
#     Возвращает:
#         Словарь с прогнозами по типам ставок.
#     """
#     # 1. Корректируем силу команд (домашнее поле + погода)
#     home_advantage = 0.1 if team1["is_home"] else -0.1
#     weather_impact = {
#         "rain": -0.05,  # Дождь снижает тоталы
#         "sunny": 0.0,
#         "windy": -0.03
#     }.get(weather, 0.0)
    
#     # 2. Учитываем мотивацию
#     team1_motivation = calculate_motivation(team1, match_type)
#     team2_motivation = calculate_motivation(team2, match_type)
    
#     # 3. Итоговые баллы команд
#     team1_adjusted = team1["avg_readiness"] + home_advantage + team1_motivation
#     team2_adjusted = team2["avg_readiness"] - home_advantage * 0.5 + team2_motivation
    
#     # 4. Разница в силе
#     diff = team1_adjusted - team2_adjusted
    
#     # 5. Прогнозы
#     forecasts = {
#         # Победа 1 / Ничья / Победа 2
#         "1X2": {
#             "П1": max(0.1, min(0.9, 0.4 + diff * 0.5)),
#             "X": max(0.1, min(0.9, 0.3 - abs(diff) * 0.5)),
#             "П2": max(0.1, min(0.9, 0.3 - diff * 0.5))
#         },
        
#         # Тоталы (меньше/больше)
#         "Тоталы": {
#             ">1.5": 0.6 + (team1["attack_strength"] + team2["attack_strength"]) * 0.2 + weather_impact,
#             "<1.5": 0.4 - (team1["attack_strength"] + team2["attack_strength"]) * 0.2 - weather_impact,
#             ">2.5": 0.5 + (team1["attack_strength"] + team2["attack_strength"]) * 0.15 + weather_impact * 0.5,
#             "<2.5": 0.5 - (team1["attack_strength"] + team2["attack_strength"]) * 0.15 - weather_impact * 0.5
#         },
        
#         # Форы
#         "Форы": {
#             "Ф1(-1.5)": max(0.1, 0.4 + diff * 0.3),
#             "Ф2(+1.5)": max(0.1, 0.6 - diff * 0.3),
#             "Ф1(-0.5)": max(0.1, 0.5 + diff * 0.4),
#             "Ф2(+0.5)": max(0.1, 0.5 - diff * 0.4)
#         },
        
#         # Обе забьют
#         "Обе забьют": {
#             "Да": (team1["attack_strength"] + team2["attack_strength"]) * 0.5 - weather_impact * 0.2,
#             "Нет": 1 - (team1["attack_strength"] + team2["attack_strength"]) * 0.5 + weather_impact * 0.2
#         },
        
#         # Первый гол
#         "Первый гол": {
#             "1": team1["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"]),
#             "2": team2["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"])
#         }
#     }
    
#     # Нормализация (чтобы сумма вероятностей была = 1)
#     forecasts["1X2"] = {k: v / sum(forecasts["1X2"].values()) for k, v in forecasts["1X2"].items()}
#     forecasts["Тоталы"] = {k: min(0.95, max(0.05, v)) for k, v in forecasts["Тоталы"].items()}
    
#     return forecasts

# # Пример использования
# if __name__ == "__main__":
#     # Загружаем данные команд (пример)
#     team1 = load_team_data("output_with_readiness_1.json", is_home=True, position_in_league=16)
#     team2 = load_team_data("output_with_readiness_2.json", is_home=False, position_in_league=3)
    
#     # Рассчитываем вероятности
#     forecast = calculate_match_probabilities(
#         team1=team1,
#         team2=team2,
#         weather="sunny",
#         match_type="обычный"
#     )
    
#     # Выводим результаты
#     print(f"\nПрогноз на матч: {team1['name']} vs {team2['name']}")
#     for market, values in forecast.items():
#         print(f"\n{market}:")
#         for bet_type, prob in values.items():
#             print(f"  {bet_type}: {prob:.2f}")