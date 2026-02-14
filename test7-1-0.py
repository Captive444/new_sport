import json
import numpy as np
import os
import sys
from pathlib import Path
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from datetime import datetime

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

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

def load_team_data_from_analysis(team_data: Dict, is_home: bool, team_name: str) -> Dict:
    """Загрузка данных команды из анализа матча"""
    try:
        # Используем только базовые данные из анализа
        position_in_league = team_data.get("position_in_league", 10)
        last_results = team_data.get("last_results", [])
        
        # Пока используем заглушку для игроков - в будущем будем загружать из *_res.json
        players = []
        
        # Расчет основных показателей на основе статистики
        avg_readiness = 0.5
        attack_power = 0.5
        defense_power = 0.5
        top_attackers = [0.5]
        
        # Учет формы
        if last_results:
            form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
        else:
            form_coefficient = 1.0
        
        # Учет позиции в лиге
        position_factor = 1.0 - (position_in_league / 20) * 0.3
        
        # Базовые расчеты (можно улучшить)
        attack_power = 0.5 * position_factor * form_coefficient
        defense_power = 0.5 * position_factor * form_coefficient
        
        # Улучшенная логика с учетом статистики голов
        scoring_stats = team_data.get("scoring_stats", {})
        if scoring_stats:
            home_avg_scored = scoring_stats.get("home", {}).get("avg_scored", 0.5)
            away_avg_scored = scoring_stats.get("away", {}).get("avg_scored", 0.5)
            
            # Атака на основе средней результативности
            if is_home:
                attack_power = min(0.9, max(0.3, home_avg_scored / 3.0))
            else:
                attack_power = min(0.9, max(0.3, away_avg_scored / 3.0))
            
            # Защита на основе средних пропущенных
            home_avg_conceded = scoring_stats.get("home", {}).get("avg_conceded", 1.0)
            away_avg_conceded = scoring_stats.get("away", {}).get("avg_conceded", 1.0)
            
            if is_home:
                defense_power = min(0.9, max(0.3, 1.0 - (home_avg_conceded / 3.0)))
            else:
                defense_power = min(0.9, max(0.3, 1.0 - (away_avg_conceded / 3.0)))
        
        team_data_dict = {
            'name': team_name,
            'is_home': is_home,
            'position_in_league': position_in_league,
            'last_results': last_results,
            'players': players,
            'avg_readiness': avg_readiness,
            'attack_power': attack_power,
            'defense_power': defense_power,
            'top_attackers': top_attackers,
            'form_coefficient': form_coefficient
        }
        
        # Добавляем анализ характеристик
        team_data_dict['characteristics'] = analyze_team_characteristics(team_data_dict)
        
        return team_data_dict
        
    except Exception as e:
        print(f"Ошибка загрузки данных команды {team_name}: {e}")
        # Возвращаем базовые данные в случае ошибки
        return {
            'name': team_name,
            'is_home': is_home,
            'position_in_league': team_data.get("position_in_league", 10),
            'last_results': team_data.get("last_results", []),
            'players': [],
            'avg_readiness': 0.5,
            'attack_power': 0.5,
            'defense_power': 0.5,
            'top_attackers': [0.5],
            'form_coefficient': 1.0,
            'characteristics': {
                "style": "сбалансированная",
                "attack_level": "средняя",
                "defense_level": "стабильная",
                "balance": "середняк",
                "weaknesses": [],
                "strengths": []
            }
        }

def load_team_data_with_players(team_data: Dict, is_home: bool, team_name: str, res_file_path: str) -> Dict:
    """Загрузка данных команды с игроками из *_res.json файла"""
    try:
        # Загружаем данные игроков
        if os.path.exists(res_file_path):
            with open(res_file_path, 'r', encoding='utf-8') as f:
                players = json.load(f)
        else:
            players = []
            print(f"⚠️ Файл с игроками не найден: {res_file_path}")
        
        # Расчет силы команды на основе игроков
        avg_readiness, attack_power, defense_power, top_attackers = calculate_team_strengths(players)
        
        # Данные из анализа матча
        position_in_league = team_data.get("position_in_league", 10)
        last_results = team_data.get("last_results", [])
        
        # Учет формы
        if last_results:
            form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
        else:
            form_coefficient = 1.0
        
        # Корректировка на основе статистики голов (если доступна)
        scoring_stats = team_data.get("scoring_stats", {})
        if scoring_stats and players:  # Используем статистику только если есть игроки
            home_avg_scored = scoring_stats.get("home", {}).get("avg_scored", 0.5)
            away_avg_scored = scoring_stats.get("away", {}).get("avg_scored", 0.5)
            
            # Усиливаем атаку на основе статистики
            if is_home:
                attack_multiplier = min(1.5, max(0.7, 1.0 + (home_avg_scored - 1.0) * 0.3))
            else:
                attack_multiplier = min(1.5, max(0.7, 1.0 + (away_avg_scored - 1.0) * 0.3))
            
            attack_power = min(0.95, attack_power * attack_multiplier)
        
        team_data_dict = {
            'name': team_name,
            'is_home': is_home,
            'position_in_league': position_in_league,
            'last_results': last_results,
            'players': players,
            'avg_readiness': avg_readiness,
            'attack_power': attack_power * form_coefficient,
            'defense_power': defense_power * form_coefficient,
            'top_attackers': top_attackers,
            'form_coefficient': form_coefficient
        }
        
        # Добавляем анализ характеристик
        team_data_dict['characteristics'] = analyze_team_characteristics(team_data_dict)
        
        return team_data_dict
        
    except Exception as e:
        print(f"❌ Ошибка загрузки команды {team_name} с игроками: {e}")
        # Возвращаем базовые данные
        return load_team_data_from_analysis(team_data, is_home, team_name)

def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """ПЕРЕПИСАННЫЙ расчет вероятностей с динамическим подходом"""
    
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

def get_detailed_analysis_str(forecast, team1, team2) -> str:
    """Возвращает строку с детальным анализом матча"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"📊 ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    lines.append(f"{'='*60}")
    
    lines.append(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    lines.append(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    lines.append(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    lines.append(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    lines.append(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    lines.append(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    
    lines.append(f"\n🎯 СТИЛЬ КОМАНД:")
    lines.append(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    lines.append(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    lines.append(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    lines.append(f"Стилевое противостояние: {analysis['style_matchup']}")
    lines.append(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
    
    if analysis["upset_alert"]:
        lines.append(f"🚨 ВНИМАНИЕ: Возможна сенсация!")
        for factor, active in analysis["upset_factors"].items():
            if active:
                lines.append(f"   • {factor}")
    
    if analysis["key_advantages"]:
        lines.append("\n✅ ПРЕИМУЩЕСТВА:")
        for advantage in analysis["key_advantages"]:
            lines.append(f"  • {advantage}")
    
    if analysis["potential_weaknesses"]:
        lines.append("\n⚠️ СЛАБЫЕ СТОРОНЫ:")
        for weakness in analysis["potential_weaknesses"]:
            lines.append(f"  • {weakness}")
    
    lines.append(f"\n💡 СТАТИСТИЧЕСКИЕ ВЫВОДЫ:")
    for insight in analysis["betting_insights"]:
        lines.append(f"  • {insight}")
    
    return "\n".join(lines)

def get_forecasts_str(forecast) -> str:
    """Возвращает строку с прогнозами"""
    lines = []
    lines.append(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    lines.append(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nТОТАЛЫ:")
    for bet_type, prob in forecast["Тоталы"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nОБЕ ЗАБЬЮТ:")
    for bet_type, prob in forecast["Обе забьют"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    for bet_type, prob in forecast["Индивидуальные тоталы"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        lines.append(f"  {score}: {prob:.4f}")
    
    return "\n".join(lines)

def process_all_matches(commands_dir: str = "commands") -> None:
    """Обработка всех матчей в папке commands"""
    
    print(f"🔍 Поиск матчей в папке: {commands_dir}")
    
    # Находим все папки с матчами
    match_folders = []
    for root, dirs, files in os.walk(commands_dir):
        # Ищем папки, содержащие файлы _analysis.json
        for file in files:
            if file.endswith("_analysis.json"):
                match_folders.append(root)
                break
    
    print(f"📁 Найдено папок с матчами: {len(match_folders)}")
    
    if not match_folders:
        print("❌ Не найдены папки с матчами!")
        return
    
    # Файл для сохранения результатов
    output_file = f"all_matches_forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"📊 СВОДКА ПРОГНОЗОВ НА ВСЕ МАТЧИ\n")
        f.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        total_matches = 0
        processed_matches = 0
        
        for match_folder in match_folders:
            # Ищем файл анализа в папке
            analysis_files = [f for f in os.listdir(match_folder) if f.endswith("_analysis.json")]
            
            if not analysis_files:
                print(f"⚠️ В папке {match_folder} не найден файл анализа")
                continue
            
            analysis_file = analysis_files[0]
            analysis_path = os.path.join(match_folder, analysis_file)
            
            print(f"\n🔍 Обработка матча: {analysis_file}")
            
            try:
                # Загружаем данные анализа
                with open(analysis_path, 'r', encoding='utf-8') as af:
                    match_data = json.load(af)
                
                total_matches += 1
                
                # Извлекаем данные команд
                match_name = match_data.get("match", "Неизвестный матч")
                home_data = match_data.get("home_team", {})
                away_data = match_data.get("away_team", {})
                
                if not home_data or not away_data:
                    print(f"⚠️ Нет данных о командах в матче: {match_name}")
                    continue
                
                home_team_name = home_data.get("team_name", "Команда 1")
                away_team_name = away_data.get("team_name", "Команда 2")
                
                print(f"   Матч: {match_name}")
                print(f"   Домашняя: {home_team_name}")
                print(f"   Гостевая: {away_team_name}")
                
                # Ищем файлы с игроками
                home_res_file = os.path.join(match_folder, f"{home_team_name}_res.json")
                away_res_file = os.path.join(match_folder, f"{away_team_name}_res.json")
                
                # Загружаем данные команд (с игроками если есть, иначе только базовые)
                if os.path.exists(home_res_file):
                    team1 = load_team_data_with_players(home_data, True, home_team_name, home_res_file)
                else:
                    team1 = load_team_data_from_analysis(home_data, True, home_team_name)
                    print(f"   ⚠️ Файл игроков для домашней команды не найден: {home_res_file}")
                
                if os.path.exists(away_res_file):
                    team2 = load_team_data_with_players(away_data, False, away_team_name, away_res_file)
                else:
                    team2 = load_team_data_from_analysis(away_data, False, away_team_name)
                    print(f"   ⚠️ Файл игроков для гостевой команды не найден: {away_res_file}")
                
                # Рассчитываем прогноз
                forecast = calculate_match_probabilities(
                    team1=team1,
                    team2=team2,
                    weather="sunny",  # Можно добавить получение погоды из данных
                    match_type="обычный"  # Можно определить тип матча
                )
                
                # Формируем вывод
                analysis_str = get_detailed_analysis_str(forecast, team1, team2)
                forecasts_str = get_forecasts_str(forecast)
                
                # Записываем в файл
                f.write(f"\n🎯 МАТЧ: {match_name}\n")
                f.write(f"📅 Дата: {match_data.get('date_time', 'Неизвестно')}\n")
                f.write(f"🏆 Лига: {match_data.get('league', 'Неизвестно')}\n")
                f.write("-"*60 + "\n")
                f.write(analysis_str)
                f.write("\n")
                f.write(forecasts_str)
                f.write("\n" + "="*80 + "\n\n")
                
                processed_matches += 1
                print(f"   ✅ Обработан успешно")
                
            except Exception as e:
                print(f"   ❌ Ошибка обработки матча {analysis_file}: {e}")
                f.write(f"\n❌ ОШИБКА ОБРАБОТКИ МАТЧА: {analysis_file}\n")
                f.write(f"Ошибка: {str(e)}\n")
                f.write("="*80 + "\n\n")
    
    # Итоговая статистика
    print(f"\n{'='*60}")
    print(f"📊 ОБРАБОТКА ЗАВЕРШЕНА")
    print(f"{'='*60}")
    print(f"Всего матчей найдено: {total_matches}")
    print(f"Успешно обработано: {processed_matches}")
    print(f"Результаты сохранены в: {output_file}")
    
    # Добавляем статистику в файл
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"📈 ИТОГОВАЯ СТАТИСТИКА\n")
        f.write(f"{'='*80}\n")
        f.write(f"Всего матчей найдено: {total_matches}\n")
        f.write(f"Успешно обработано: {processed_matches}\n")
        f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def print_detailed_analysis(forecast, team1, team2):
    """Вывод детального анализа в консоль"""
    print(get_detailed_analysis_str(forecast, team1, team2))

def print_forecasts(forecast):
    """Вывод прогнозов в консоль"""
    print(get_forecasts_str(forecast))

if __name__ == "__main__":
    print("="*60)
    print("🏆 АНАЛИЗАТОР ФУТБОЛЬНЫХ МАТЧЕЙ")
    print("="*60)
    
    # Вариант 1: Обработка всех матчей в папке commands
    process_all_matches("commands")
    
    # Вариант 2: Пример обработки одного конкретного матча (для тестирования)
    """
    # Загружаем данные анализа матча
    analysis_file = "commands/Аланьяспор - Фенербахче/Аланьяспор - Фенербахче_analysis.json"
    
    if os.path.exists(analysis_file):
        with open(analysis_file, 'r', encoding='utf-8') as f:
            match_data = json.load(f)
        
        home_data = match_data["home_team"]
        away_data = match_data["away_team"]
        
        # Загружаем данные команд (с игроками если есть)
        match_folder = os.path.dirname(analysis_file)
        home_res_file = os.path.join(match_folder, f"{home_data['team_name']}_res.json")
        away_res_file = os.path.join(match_folder, f"{away_data['team_name']}_res.json")
        
        team1 = load_team_data_with_players(home_data, True, home_data["team_name"], home_res_file)
        team2 = load_team_data_with_players(away_data, False, away_data["team_name"], away_res_file)
        
        # Расчет прогноза
        forecast = calculate_match_probabilities(
            team1=team1,
            team2=team2,
            weather="sunny",
            match_type="еврокубки"
        )
        
        # Вывод в консоль
        print_detailed_analysis(forecast, team1, team2)
        print_forecasts(forecast)
    else:
        print(f"Файл анализа не найден: {analysis_file}")
    """