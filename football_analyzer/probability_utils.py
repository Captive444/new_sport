from math import factorial, exp
from typing import Dict

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

def calculate_dynamic_attack(team: Dict, opponent: Dict) -> float:
    """Динамический расчет атаки с учетом соперника"""
    base_attack = team["attack_power"]
    
    defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
    form_boost = 1.0
    if team.get('last_results'):
        recent_goals = sum(team['last_results'])
        form_boost = 0.8 + (recent_goals / len(team['last_results'])) * 0.4
    
    motivation_boost = 1.0 + team.get('motivation', 0) * 2
    
    return base_attack * defense_multiplier * form_boost * motivation_boost

def calculate_goal_efficiency(team1: Dict, team2: Dict) -> Dict:
    """Расчет реальной голевой эффективности"""
    
    team1_goal_potential = calculate_dynamic_attack(team1, team2)
    team2_goal_potential = calculate_dynamic_attack(team2, team1)
    
    if team1["is_home"]:
        team1_goal_potential *= 1.3
        team2_goal_potential *= 0.9
    else:
        team1_goal_potential *= 0.9
        team2_goal_potential *= 1.3
    
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
    
    team1_scores = team1["attack_power"] * (1.3 - team2["defense_power"])
    team2_scores = team2["attack_power"] * (1.3 - team1["defense_power"])
    
    both_score_prob = team1_scores * team2_scores * 1.2
    
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
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        upset_factors["strong_attack_vs_weak_defense"] = True
    
    motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
    if motivation_diff > 0.1:
        upset_factors["motivation_disparity"] = True
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.75:
        upset_factors["star_player_impact"] = True
    
    if team1.get('last_results') and team2.get('last_results'):
        form1 = sum(team1['last_results']) / len(team1['last_results'])
        form2 = sum(team2['last_results']) / len(team2['last_results'])
        if form2 > form1 * 1.5:
            upset_factors["recent_form_gap"] = True
    
    return upset_factors

def calculate_exact_scores_dynamic(team1: Dict, team2: Dict, mean_goals_team1: float, mean_goals_team2: float, max_goals=5):
    """Расчет точных счетов на основе динамических средних голов"""
    
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
    
    if position >= 16:
        base_motivation += 0.12
    elif position <= 4:
        base_motivation += 0.10
    elif position <= 6:
        base_motivation += 0.07
    elif position <= 8:
        base_motivation += 0.04
    
    if team.get('last_results'):
        win_rate = sum(team['last_results']) / len(team['last_results'])
        if win_rate > 0.6:
            base_motivation += 0.04
        elif win_rate < 0.2:
            base_motivation -= 0.03
    
    return min(0.25, max(0.0, base_motivation))