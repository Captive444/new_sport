import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Tuple

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

def calculate_team_strengths(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
    """Расчет силы команды на основе данных игроков из JSON"""
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
    
    # Расчет силы атаки (топ-3 атакующих + полузащитники)
    attacking_players = sorted(attackers, reverse=True)[:3]
    if midfielders:
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    # Расчет силы защиты (вратари + защитники + часть полузащитников)
    defense_players = goalkeepers + defenders
    if midfielders:
        defense_players.append(np.mean(midfielders) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    # Топ-атакующие игроки
    top_attackers = sorted(attackers, reverse=True)[:3]
    
    return avg_readiness, attack_power, defense_power, top_attackers

def analyze_team_characteristics(team_data: Dict) -> Dict:
    """Анализ характеристик команды на основе игроков"""
    readiness = team_data["avg_readiness"]
    attack = team_data["attack_power"]
    defense = team_data["defense_power"]
    
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
    if team_data["top_attackers"] and team_data["top_attackers"][0] > 0.7:
        characteristics["strengths"].append("есть звездный игрок")
    
    if readiness < 0.4:
        characteristics["weaknesses"].append("низкая готовность")
    
    return characteristics

def calculate_goal_potential(team1: Dict, team2: Dict) -> Dict:
    """Расчет голевого потенциала на основе силы команд"""
    # Базовые ожидаемые голы на основе силы атаки/защиты
    team1_goals = team1["attack_power"] * (1.5 - team2["defense_power"])
    team2_goals = team2["attack_power"] * (1.5 - team1["defense_power"])
    
    # Корректировка на домашнее поле
    if team1["is_home"]:
        team1_goals *= 1.2
        team2_goals *= 0.9
    else:
        team1_goals *= 0.9
        team2_goals *= 1.2
    
    # Учет звездных игроков
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        team1_goals *= 1.2
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        team2_goals *= 1.2
    
    return {
        "team1_goals": max(0.3, team1_goals),
        "team2_goals": max(0.3, team2_goals)
    }

def calculate_exact_scores(mean_goals_team1: float, mean_goals_team2: float, max_goals=5):
    """Расчет точных счетов на основе распределения Пуассона"""
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_goals_team1, i) * poisson_probability(mean_goals_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    # Нормализация вероятностей
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}

def calculate_1x2_probabilities(exact_scores: Dict) -> Dict:
    """Расчет вероятностей 1X2"""
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

def calculate_totals_probabilities(exact_scores: Dict) -> Dict:
    """Расчет вероятностей тоталов"""
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

def load_and_analyze_team(file_path: str, is_home: bool = True) -> Dict:
    """Загрузка и анализ команды из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки {file_path}: {e}")
        players = []
    
    # Расчет основных показателей команды
    avg_readiness, attack_power, defense_power, top_attackers = calculate_team_strengths(players)
    
    team_data = {
        'name': file_path.replace('.json', '').replace('output_with_readiness_', 'Команда '),
        'is_home': is_home,
        'players': players,
        'avg_readiness': avg_readiness,
        'attack_power': attack_power,
        'defense_power': defense_power,
        'top_attackers': top_attackers
    }
    
    # Добавляем анализ характеристик
    team_data['characteristics'] = analyze_team_characteristics(team_data)
    
    return team_data

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

def calculate_match_probabilities(team1: Dict, team2: Dict) -> Dict:
    """Основная функция расчета вероятностей матча"""
    # Расчет голевого потенциала
    goal_potential = calculate_goal_potential(team1, team2)
    
    # Расчет точных счетов
    exact_scores = calculate_exact_scores(
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
    # Расчет всех вероятностей
    forecasts = {
        "1X2": calculate_1x2_probabilities(exact_scores),
        "Тоталы": calculate_totals_probabilities(exact_scores),
        "Индивидуальные тоталы": calculate_individual_totals(
            goal_potential["team1_goals"], 
            goal_potential["team2_goals"]
        ),
        "Точный счет": dict(sorted(exact_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
        "Анализ матча": {
            **analyze_matchup(team1, team2),
            "goal_potential": goal_potential
        }
    }
    
    return forecasts

def print_detailed_analysis(forecast, team1, team2):
    """Красивый вывод анализа матча"""
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
    
    if analysis["key_advantages"]:
        print("\n✅ ПРЕИМУЩЕСТВА:")
        for advantage in analysis["key_advantages"]:
            print(f"  • {advantage}")
    
    if analysis["potential_weaknesses"]:
        print("\n⚠️ СЛАБЫЕ СТОРОНЫ:")
        for weakness in analysis["potential_weaknesses"]:
            print(f"  • {weakness}")
    
    if analysis["betting_insights"]:
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
    
    print(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    for bet_type, prob in forecast["Индивидуальные тоталы"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        print(f"  {score}: {prob:.4f}")

# ИСПОЛЬЗОВАНИЕ:
if __name__ == "__main__":
    # Просто загружаем данные из JSON файлов
    team1 = load_and_analyze_team("output_with_readiness_1.json", is_home=True)
    team2 = load_and_analyze_team("output_with_readiness_2.json", is_home=False)
    
    # Расчет прогноза
    forecast = calculate_match_probabilities(team1, team2)
    
    # Вывод результатов
    print_detailed_analysis(forecast, team1, team2)
    print_forecasts(forecast)