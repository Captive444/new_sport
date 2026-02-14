import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
import os

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

def load_league_table(file_path: str) -> Dict[str, Dict]:
    """Загрузка таблицы чемпионата из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        league_table = {}
        for team_data in data.get('teams', []):
            team_name = team_data['team']
            league_table[team_name] = {
                'position': int(team_data['position']),
                'games': int(team_data['games']),
                'wins': int(team_data['wins']),
                'draws': int(team_data['draws']),
                'losses': int(team_data['losses']),
                'goals_for': int(team_data['goals_for']),
                'goals_against': int(team_data['goals_against']),
                'goal_difference': team_data['goal_difference'],
                'points': int(team_data['points'])
            }
        
        return league_table
    except Exception as e:
        print(f"Ошибка загрузки таблицы чемпионата: {e}")
        return {}

def calculate_attack_power_from_stats(team_stats: Dict) -> float:
    """Расчет силы атаки на основе статистики"""
    goals_per_game = team_stats['goals_for'] / team_stats['games']
    win_rate = team_stats['wins'] / team_stats['games']
    
    # Более реалистичная нормализация
    base_attack = min(1.0, goals_per_game / 2.5)
    win_bonus = win_rate * 0.2
    
    return min(1.0, max(0.1, base_attack + win_bonus))

def calculate_defense_power_from_stats(team_stats: Dict) -> float:
    """Расчет силы защиты на основе статистики"""
    goals_against_per_game = team_stats['goals_against'] / team_stats['games']
    win_rate = team_stats['wins'] / team_stats['games']
    
    base_defense = max(0.1, 1.0 - (goals_against_per_game / 2.5))
    win_bonus = win_rate * 0.15
    
    return min(1.0, max(0.1, base_defense + win_bonus))

def simulate_recent_form(team_stats: Dict) -> List[float]:
    """Симуляция последних 5 матчей на основе статистики команды"""
    wins = team_stats['wins']
    draws = team_stats['draws']
    losses = team_stats['losses']
    total_matches = team_stats['games']
    
    # Текущие проценты
    win_prob = wins / total_matches
    draw_prob = draws / total_matches
    loss_prob = losses / total_matches
    
    recent_form = []
    
    for i in range(5):
        # Генерируем результат на основе статистики
        rand = np.random.random()
        if rand < win_prob:
            result = 1.0  # победа
        elif rand < win_prob + draw_prob:
            result = 0.5  # ничья
        else:
            result = 0.0  # поражение
        
        recent_form.append(result)
    
    return recent_form

def calculate_team_strengths(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
    """Расчет силы команды по позициям"""
    if not players:
        return 0.5, 0.5, 0.5, [0.3]
    
    goalkeepers = []
    defenders = []
    midfielders = []
    attackers = []
    
    for player in players:
        pos = player['position'].lower()
        readiness = player['readiness']
        
        if 'вратарь' in pos:
            goalkeepers.append(readiness * 1.3)
        elif 'защитник' in pos:
            defenders.append(readiness * 0.9)
        elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
            attackers.append(readiness * 1.1)
        elif 'полузащитник' in pos or 'хав' in pos:
            midfielders.append(readiness * 0.7)
            attackers.append(readiness * 0.4)
        else:
            midfielders.append(readiness * 0.6)
            attackers.append(readiness * 0.4)
    
    # Расчет общей готовности
    all_players = goalkeepers + defenders + midfielders + attackers
    avg_readiness = np.mean(all_players) if all_players else 0.5
    
    # Расчет силы атаки
    attacking_players = sorted(attackers, reverse=True)[:3]
    if midfielders:
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    # Расчет силы защиты
    defense_players = goalkeepers + defenders
    if midfielders:
        defense_players.append(np.mean(midfielders) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    # Топ-атакующие
    top_attackers = sorted(attackers, reverse=True)[:3]
    
    return avg_readiness, attack_power, defense_power, top_attackers

def analyze_team_characteristics(team: Dict) -> Dict:
    """Анализ характеристик команды"""
    readiness = team["avg_readiness"]
    attack = team["attack_power"]
    defense = team["defense_power"]
    
    characteristics = {
        "style": "",
        "attack_level": "",
        "defense_level": "",
        "balance": "",
        "weaknesses": [],
        "strengths": []
    }
    
    # Определение стиля
    attack_ratio = attack / (defense + 0.1)
    if attack_ratio > 1.3:
        characteristics["style"] = "атакующая"
    elif attack_ratio < 0.8:
        characteristics["style"] = "оборонительная"
    else:
        characteristics["style"] = "сбалансированная"
    
    # Уровень атаки
    if attack > 0.7:
        characteristics["attack_level"] = "сильная"
        characteristics["strengths"].append("эффективная атака")
    elif attack < 0.4:
        characteristics["attack_level"] = "слабая"
        characteristics["weaknesses"].append("проблемы в атаке")
    else:
        characteristics["attack_level"] = "средняя"
    
    # Уровень защиты
    if defense > 0.7:
        characteristics["defense_level"] = "надежная"
        characteristics["strengths"].append("крепкая защита")
    elif defense < 0.4:
        characteristics["defense_level"] = "уязвимая"
        characteristics["weaknesses"].append("слабая оборона")
    else:
        characteristics["defense_level"] = "стабильная"
    
    # Баланс команды
    total_power = attack + defense
    if total_power > 1.4:
        characteristics["balance"] = "сильная команда"
    elif total_power < 0.8:
        characteristics["balance"] = "слабая команда"
    else:
        characteristics["balance"] = "середняк"
    
    # Анализ звездных игроков
    if team["top_attackers"] and team["top_attackers"][0] > 0.7:
        characteristics["strengths"].append("есть звездный игрок")
    
    if readiness < 0.4:
        characteristics["weaknesses"].append("низкая готовность")
    
    return characteristics

def load_team_data_enhanced(players_file: str, team_name: str, is_home: bool, 
                          league_table: Dict = None) -> Dict:
    """Улучшенная загрузка данных команды с интеграцией статистики чемпионата"""
    
    # Загрузка данных игроков
    try:
        with open(players_file, 'r', encoding='utf-8') as f:
            players = json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки файла игроков {players_file}: {e}")
        players = []
    
    # Расчет основных показателей из данных игроков
    avg_readiness, attack_power_players, defense_power_players, top_attackers = calculate_team_strengths(players)
    
    # Получение статистики из таблицы чемпионата
    team_stats = None
    position = 10
    last_results = [0.5, 0.5, 0.5, 0.5, 0.5]
    
    if league_table and team_name in league_table:
        team_stats = league_table[team_name]
        position = team_stats['position']
        
        # Расчет формы на основе статистики
        last_results = simulate_recent_form(team_stats)
        
        # Расчет силы на основе статистики
        attack_power_stats = calculate_attack_power_from_stats(team_stats)
        defense_power_stats = calculate_defense_power_from_stats(team_stats)
        
        # Комбинируем: 70% статистика, 30% готовность игроков
        attack_power = 0.7 * attack_power_stats + 0.3 * attack_power_players
        defense_power = 0.7 * defense_power_stats + 0.3 * defense_power_players
    else:
        # Используем только данные игроков
        attack_power = attack_power_players
        defense_power = defense_power_players
        print(f"⚠️ Команда {team_name} не найдена в таблице чемпионата. Используются только данные игроков.")
    
    team_data = {
        'name': team_name,
        'is_home': is_home,
        'position_in_league': position,
        'last_results': last_results,
        'players': players,
        'avg_readiness': avg_readiness,
        'attack_power': max(0.1, min(1.0, attack_power)),
        'defense_power': max(0.1, min(1.0, defense_power)),
        'top_attackers': top_attackers,
        'team_stats': team_stats
    }
    
    # Добавляем анализ характеристик
    team_data['characteristics'] = analyze_team_characteristics(team_data)
    
    return team_data

def calculate_dynamic_attack(team: Dict, opponent: Dict) -> float:
    """Динамический расчет атаки с учетом соперника"""
    base_attack = team["attack_power"]
    
    # Усиление атаки против слабой защиты
    defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
    # Учет формы (последние 5 матчей)
    form_boost = 1.0
    if team.get('last_results'):
        recent_goals = sum(team['last_results'])  # предполагаем, что результаты связаны с голами
        form_boost = 0.8 + (recent_goals / len(team['last_results'])) * 0.4
    
    # Учет мотивации для атаки
    motivation_boost = 1.0 + team.get('motivation', 0) * 2
    
    return base_attack * defense_multiplier * form_boost * motivation_boost

def calculate_goal_efficiency(team1: Dict, team2: Dict) -> Dict:
    """Расчет реальной голевой эффективности"""
    
    # Динамическая сила атаки против конкретной защиты
    team1_goal_potential = calculate_dynamic_attack(team1, team2)
    team2_goal_potential = calculate_dynamic_attack(team2, team1)
    
    # Корректировка на домашнее поле
    if team1["is_home"]:
        team1_goal_potential *= 1.3
        team2_goal_potential *= 0.9
    else:
        team1_goal_potential *= 0.9
        team2_goal_potential *= 1.3
    
    # Учет звездных игроков (могут решить матч)
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        team1_goal_potential *= 1.25
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        team2_goal_potential *= 1.25
    
    return {
        "team1_goals": max(0.3, team1_goal_potential),
        "team2_goals": max(0.3, team2_goal_potential)
    }

def calculate_both_teams_to_score(team1: Dict, team2: Dict) -> float:
    """Улучшенный расчет 'Обе забьют'"""
    
    # Вероятность, что команда 1 забьет команде 2
    team1_scores = team1["attack_power"] * (1.3 - team2["defense_power"])
    
    # Вероятность, что команда 2 забьет команде 1  
    team2_scores = team2["attack_power"] * (1.3 - team1["defense_power"])
    
    # Общая вероятность, что обе забьют
    both_score_prob = team1_scores * team2_scores * 1.2
    
    # Корректировка на стиль команд
    if team1["characteristics"]["style"] == "атакующая" and team2["characteristics"]["style"] == "атакующая":
        both_score_prob *= 1.3
    elif team1["characteristics"]["style"] == "оборонительная" and team2["characteristics"]["style"] == "оборонительная":
        both_score_prob *= 0.7
    
    return min(0.85, max(0.15, both_score_prob))

def detect_upset_potential(team1: Dict, team2: Dict) -> Dict:
    """Обнаружение потенциала для неожиданного результата"""
    
    upset_factors = {
        "strong_attack_vs_weak_defense": False,
        "motivation_disparity": False,
        "star_player_impact": False,
        "recent_form_gap": False
    }
    
    # Сильная атака против слабой защиты
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        upset_factors["strong_attack_vs_weak_defense"] = True
    
    # Разница в мотивации
    motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
    if motivation_diff > 0.1:
        upset_factors["motivation_disparity"] = True
    
    # Влияние звездных игроков
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.75:
        upset_factors["star_player_impact"] = True
    
    # Разница в форме
    if team1.get('last_results') and team2.get('last_results'):
        form1 = sum(team1['last_results']) / len(team1['last_results'])
        form2 = sum(team2['last_results']) / len(team2['last_results'])
        if form2 > form1 * 1.5:
            upset_factors["recent_form_gap"] = True
    
    return upset_factors

def calculate_exact_scores_dynamic(team1: Dict, team2: Dict, mean_goals_team1: float, mean_goals_team2: float, max_goals=5):
    """Расчет точных счетов на основе динамических средних голов"""
    
    # Гарантируем минимальную продуктивность
    mean_goals_team1 = max(0.4, mean_goals_team1)
    mean_goals_team2 = max(0.4, mean_goals_team2)
    
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_goals_team1, i) * poisson_probability(mean_goals_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}

def calculate_1x2_from_poisson(exact_scores: Dict) -> Dict:
    """Расчет 1X2 на основе точных счетов"""
    p1 = 0.0
    draw = 0.0
    p2 = 0.0
    
    for score, prob in exact_scores.items():
        home_goals, away_goals = map(int, score.split('-'))
        if home_goals > away_goals:
            p1 += prob
        elif home_goals == away_goals:
            draw += prob
        else:
            p2 += prob
    
    return {"П1": p1, "X": draw, "П2": p2}

def calculate_totals_from_poisson(exact_scores: Dict) -> Dict:
    """Расчет тоталов на основе точных счетов"""
    over_15 = 0.0
    over_25 = 0.0
    
    for score, prob in exact_scores.items():
        home_goals, away_goals = map(int, score.split('-'))
        total_goals = home_goals + away_goals
        
        if total_goals > 1.5:
            over_15 += prob
        if total_goals > 2.5:
            over_25 += prob
    
    return {
        ">1.5": over_15,
        "<1.5": 1 - over_15,
        ">2.5": over_25,
        "<2.5": 1 - over_25
    }

def calculate_individual_totals(mean_goals_team1: float, mean_goals_team2: float) -> Dict:
    """Расчет индивидуальных тоталов"""
    # Вероятность, что команда забьет больше 1.5 голов
    itb1_15 = 1 - (poisson_probability(mean_goals_team1, 0) + poisson_probability(mean_goals_team1, 1))
    itb2_15 = 1 - (poisson_probability(mean_goals_team2, 0) + poisson_probability(mean_goals_team2, 1))
    
    return {
        "ИТБ1 1.5": max(0.05, min(0.95, itb1_15)),
        "ИТМ1 1.5": max(0.05, min(0.95, 1 - itb1_15)),
        "ИТБ2 1.5": max(0.05, min(0.95, itb2_15)),
        "ИТМ2 1.5": max(0.05, min(0.95, 1 - itb2_15))
    }

def calculate_motivation(team: Dict, match_type: str) -> float:
    """Расчет мотивации команды"""
    base_motivation = {
        'вылет': 0.20,
        'еврокубки': 0.15,
        'дерби': 0.12,
        'кубок': 0.10,
        'обычный': 0.03
    }.get(match_type, 0.03)
    
    position = team.get('position_in_league', 1)
    
    # Мотивация в зависимости от положения в таблице
    if position >= 16:
        base_motivation += 0.12
    elif position <= 4:
        base_motivation += 0.10
    elif position <= 6:
        base_motivation += 0.07
    elif position <= 8:
        base_motivation += 0.04
    
    # Учет формы
    if team.get('last_results'):
        win_rate = sum(team['last_results']) / len(team['last_results'])
        if win_rate > 0.6:
            base_motivation += 0.04
        elif win_rate < 0.2:
            base_motivation -= 0.03
    
    return min(0.25, max(0.0, base_motivation))

def analyze_matchup(team1: Dict, team2: Dict) -> Dict:
    """Анализ противостояния команд"""
    analysis = {
        "style_matchup": "",
        "key_advantages": [],
        "potential_weaknesses": [],
        "expected_dynamics": "",
        "betting_insights": []
    }
    
    # Анализ стилей
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    analysis["style_matchup"] = f"{style1} vs {style2}"
    
    # Ключевые преимущества
    if team1["attack_power"] > team2["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team1['name']} имеет атакующее преимущество")
        analysis["betting_insights"].append("ИТБ1 1.5")
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team2['name']} может быть опасна в атаке")
        analysis["betting_insights"].append("ИТБ2 1.5")
    
    # Анализ слабостей
    if team1["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team1['name']} проблемы в защите")
    
    if team2["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team2['name']} слабая оборона")
    
    # Ожидаемая динамика матча
    total_attack = team1["attack_power"] + team2["attack_power"]
    if total_attack > 1.2:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif total_attack < 0.8:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    # Домашнее преимущество
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    return analysis

def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """Расчет вероятностей с динамическим подходом"""
    
    # Расчет мотивации
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    team1['motivation'] = team1_motivation
    team2['motivation'] = team2_motivation
    
    # 1. Динамический расчет голевого потенциала
    goal_potential = calculate_goal_efficiency(team1, team2)
    
    # 2. Детектор сенсаций
    upset_potential = detect_upset_potential(team1, team2)
    
    # 3. Расчет точных счетов через Пуассон
    exact_scores = calculate_exact_scores_dynamic(
        team1, team2, 
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
    # 4. Основные рынки на основе реальной силы
    forecasts = {
        "1X2": calculate_1x2_from_poisson(exact_scores),
        "Тоталы": calculate_totals_from_poisson(exact_scores),
        "Обе забьют": {
            "Да": calculate_both_teams_to_score(team1, team2),
            "Нет": 1 - calculate_both_teams_to_score(team1, team2)
        },
        "Индивидуальные тоталы": calculate_individual_totals(
            goal_potential["team1_goals"], 
            goal_potential["team2_goals"]
        ),
        "Точный счет": dict(sorted(exact_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
        "Анализ матча": {
            **analyze_matchup(team1, team2),
            "upset_alert": any(upset_potential.values()),
            "upset_factors": upset_potential,
            "goal_potential": goal_potential
        }
    }
    
    return forecasts

def print_team_stats(team: Dict):
    """Вывод статистики команды"""
    print(f"\n📊 СТАТИСТИКА {team['name']}:")
    print(f"Позиция в лиге: {team['position_in_league']}")
    
    if team.get('team_stats'):
        stats = team['team_stats']
        print(f"Матчи: {stats['games']} | Победы: {stats['wins']} | Ничьи: {stats['draws']} | Поражения: {stats['losses']}")
        print(f"Голы: {stats['goals_for']}-{stats['goals_against']} (разница: {stats['goal_difference']})")
        print(f"Очки: {stats['points']}")
        print(f"Забивает: {stats['goals_for']/stats['games']:.2f} г/м | Пропускает: {stats['goals_against']/stats['games']:.2f} г/м")
    
    print(f"Сила атаки: {team['attack_power']:.2f}")
    print(f"Сила защиты: {team['defense_power']:.2f}")
    print(f"Форма (последние 5): {[f'{x:.1f}' for x in team['last_results']]}")

def print_detailed_analysis(forecast, team1, team2):
    """Детальный вывод анализа матча"""
    print(f"\n{'='*60}")
    print(f"📊 ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    print(f"{'='*60}")
    
    print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    print(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    print(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    print(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    
    print(f"\n🎯 СТИЛЬ КОМАНД:")
    print(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    print(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    print(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    print(f"Стилевое противостояние: {analysis['style_matchup']}")
    print(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
    
    if analysis["upset_alert"]:
        print(f"🚨 ВНИМАНИЕ: Возможна сенсация!")
        for factor, active in analysis["upset_factors"].items():
            if active:
                print(f"   • {factor}")
    
    if analysis["key_advantages"]:
        print("\n✅ ПРЕИМУЩЕСТВА:")
        for advantage in analysis["key_advantages"]:
            print(f"  • {advantage}")
    
    if analysis["potential_weaknesses"]:
        print("\n⚠️ СЛАБЫЕ СТОРОНЫ:")
        for weakness in analysis["potential_weaknesses"]:
            print(f"  • {weakness}")
    
    print(f"\n💡 СТАТИСТИЧЕСКИЕ ВЫВОДЫ:")
    for insight in analysis["betting_insights"]:
        print(f"  • {insight}")

def print_forecasts(forecast):
    """Вывод прогнозов"""
    print(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    print(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nТОТАЛЫ:")
    for bet_type, prob in forecast["Тоталы"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nОБЕ ЗАБЬЮТ:")
    for bet_type, prob in forecast["Обе забьют"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    for bet_type, prob in forecast["Индивидуальные тоталы"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        print(f"  {score}: {prob:.4f}")

if __name__ == "__main__":
    # ★★★★★ КОНФИГУРАЦИЯ - ВВЕДИТЕ ДАННЫЕ ЗДЕСЬ ★★★★★
    
    # 1. Укажите путь к файлу с таблицей чемпионата
    LEAGUE_TABLE_FILE = "Чемпионат Англии по футболу 2025_2026, Премьер-Лига_table.json"  # ваш файл с таблицей
    
    # 2. Укажите названия команд (должны совпадать с названиями в таблице)
    TEAM1_NAME = "Сандерленд"      # домашняя команда
    TEAM2_NAME = "Арсенал" # гостевая команда
    
    # 3. Укажите пути к файлам с данными игроков
    TEAM1_PLAYERS_FILE = "output_with_readiness_1.json"
    TEAM2_PLAYERS_FILE = "output_with_readiness_2.json"
    
    # 4. Укажите параметры матча
    MATCH_TYPE = "еврокубки"  # варианты: 'вылет', 'еврокубки', 'дерби', 'кубок', 'обычный'
    WEATHER = "sunny"         # погода (пока не используется активно)
    
    # ★★★★★ КОНЕЦ КОНФИГУРАЦИИ ★★★★★
    
    print("⚽ ЗАГРУЗКА ДАННЫХ МАТЧА...")
    
    # Загрузка таблицы чемпионата
    league_table = load_league_table(LEAGUE_TABLE_FILE)
    if not league_table:
        print(f"❌ Ошибка: Не удалось загрузить таблицу из файла {LEAGUE_TABLE_FILE}")
        exit()
    
    # Автоматическая загрузка данных команд
    team1 = load_team_data_enhanced(
        players_file=TEAM1_PLAYERS_FILE,
        team_name=TEAM1_NAME,
        is_home=True,
        league_table=league_table
    )
    
    team2 = load_team_data_enhanced(
        players_file=TEAM2_PLAYERS_FILE,
        team_name=TEAM2_NAME,
        is_home=False,
        league_table=league_table
    )
    
    # Вывод статистики команд
    print_team_stats(team1)
    print_team_stats(team2)
    
    # Расчет прогноза
    print(f"\n🎯 РАСЧЕТ ПРОГНОЗА...")
    forecast = calculate_match_probabilities(
        team1=team1,
        team2=team2,
        weather=WEATHER,
        match_type=MATCH_TYPE
    )
    
    # Вывод результатов
    print_detailed_analysis(forecast, team1, team2)
    print_forecasts(forecast)