import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import statistics

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

class LeagueCalibrator:
    """Калибратор для разных лиг"""
    
    LEAGUE_PARAMS = {
        'premier_league': {'avg_goals': 2.8, 'home_advantage': 1.15, 'scoring_factor': 1.1},
        'la_liga': {'avg_goals': 2.5, 'home_advantage': 1.12, 'scoring_factor': 1.0},
        'serie_a': {'avg_goals': 2.7, 'home_advantage': 1.1, 'scoring_factor': 0.95},
        'bundesliga': {'avg_goals': 3.2, 'home_advantage': 1.18, 'scoring_factor': 1.2},
        'ligue_1': {'avg_goals': 2.6, 'home_advantage': 1.08, 'scoring_factor': 0.9},
        'rpl': {'avg_goals': 2.4, 'home_advantage': 1.1, 'scoring_factor': 0.85},
        'argentina': {'avg_goals': 2.2, 'home_advantage': 1.05, 'scoring_factor': 0.8},
        # НОВЫЙ - Бразильская Серия А:
        'serie_a_brazil': {'avg_goals': 2.3, 'home_advantage': 1.12, 'scoring_factor': 0.82},
        'default': {'avg_goals': 2.5, 'home_advantage': 1.1, 'scoring_factor': 1.0}
    }
    
    @staticmethod
    def get_league_factor(league_name: str) -> Dict:
        """Получение параметров лиги"""
        league_key = league_name.lower().replace(' ', '_')
        return LeagueCalibrator.LEAGUE_PARAMS.get(league_key, LeagueCalibrator.LEAGUE_PARAMS['default'])

class TeamDataEnhancer:
    """Улучшенная загрузка и обработка данных команды"""
    
    @staticmethod
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
            
            if 'вратарь' in pos or 'goalkeeper' in pos:
                goalkeepers.append(readiness * 1.3)
            elif 'защитник' in pos or 'defender' in pos:
                defenders.append(readiness * 0.9)
            elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos or 'forward' in pos or 'attacker' in pos:
                attackers.append(readiness * 1.1)
            elif 'полузащитник' in pos or 'хав' in pos or 'midfielder' in pos:
                midfielders.append(readiness * 0.7)
                attackers.append(readiness * 0.4)
            else:
                midfielders.append(readiness * 0.6)
                attackers.append(readiness * 0.4)
        
        # Расчет общей готовности
        all_players = goalkeepers + defenders + midfielders + attackers
        avg_readiness = np.mean(all_players) if all_players else 0.5
        
        # Расчет силы атаки (топ-3 нападающих + вклад полузащиты)
        attacking_players = sorted(attackers, reverse=True)[:3]
        if midfielders:
            attacking_players.append(np.mean(midfielders) * 0.6)
        attack_power = np.mean(attacking_players) if attacking_players else 0.3
        
        # Расчет силы защиты (вратари + защитники + вклад полузащиты)
        defense_players = goalkeepers + defenders
        if midfielders:
            defense_players.append(np.mean(midfielders) * 0.4)
        defense_power = np.mean(defense_players) if defense_players else 0.5
        
        # Топ-атакующие
        top_attackers = sorted(attackers, reverse=True)[:3]
        
        return avg_readiness, attack_power, defense_power, top_attackers
    
    @staticmethod
    def calculate_form_impact(last_results: List[float], matches_considered: int = 5) -> float:
        """Расчет влияния формы с учетом весов (последние матчи важнее)"""
        if not last_results:
            return 1.0
        
        weights = [0.1, 0.15, 0.2, 0.25, 0.3]  # Веса для последних 5 матчей
        weighted_results = sum(r * w for r, w in zip(last_results[-matches_considered:], weights[:len(last_results)]))
        
        # Форма влияет на производительность от 0.8 до 1.2
        return 0.8 + (weighted_results * 0.4)
    
    @staticmethod
    def analyze_playing_style(team: Dict) -> Dict:
        """Анализ стиля игры команды"""
        attack = team["attack_power"]
        defense = team["defense_power"]
        
        characteristics = {
            "style": "",
            "attack_level": "",
            "defense_level": "",
            "balance": "",
            "formation": team.get("formation", "4-4-2"),
            "preferred_tactics": "",
            "weaknesses": [],
            "strengths": [],
            "avg_goals_scored": team.get("avg_goals_scored", 1.2),
            "avg_goals_conceded": team.get("avg_goals_conceded", 1.2)
        }
        
        # Определение стиля на основе соотношения атаки и защиты
        attack_defense_ratio = attack / (defense + 0.1)
        if attack_defense_ratio > 1.4:
            characteristics["style"] = "атакующая"
            characteristics["preferred_tactics"] = "высокий прессинг, атакующий футбол"
        elif attack_defense_ratio < 0.7:
            characteristics["style"] = "оборонительная"
            characteristics["preferred_tactics"] = "глухая оборона, контратаки"
        else:
            characteristics["style"] = "сбалансированная"
            characteristics["preferred_tactics"] = "универсальная тактика"
        
        # Уровень атаки
        if attack > 0.75:
            characteristics["attack_level"] = "сильная"
            characteristics["strengths"].append("эффективная атака")
        elif attack < 0.35:
            characteristics["attack_level"] = "слабая"
            characteristics["weaknesses"].append("проблемы в атаке")
        else:
            characteristics["attack_level"] = "средняя"
        
        # Уровень защиты
        if defense > 0.75:
            characteristics["defense_level"] = "надежная"
            characteristics["strengths"].append("крепкая защита")
        elif defense < 0.35:
            characteristics["defense_level"] = "уязвимая"
            characteristics["weaknesses"].append("слабая оборона")
        else:
            characteristics["defense_level"] = "стабильная"
        
        # Баланс команды
        total_power = attack + defense
        if total_power > 1.5:
            characteristics["balance"] = "сильная команда"
        elif total_power < 0.8:
            characteristics["balance"] = "слабая команда"
        else:
            characteristics["balance"] = "середняк"
        
        # Анализ звездных игроков
        if team["top_attackers"] and team["top_attackers"][0] > 0.8:
            characteristics["strengths"].append("есть звездный нападающий")
        
        if team.get('avg_readiness', 1.0) < 0.4:
            characteristics["weaknesses"].append("низкая готовность команды")
        
        return characteristics

def calculate_motivation_enhanced(team: Dict, match_type: str, opponent_strength: float) -> float:
    """Улучшенный расчет мотивации"""
    base_motivation = {
        'вылет': 0.25,
        'еврокубки': 0.20,
        'дерби': 0.18,
        'кубок': 0.15,
        'лидеры': 0.12,
        'обычный': 0.05
    }.get(match_type, 0.05)
    
    position = team.get('position_in_league', 1)
    total_teams = team.get('total_teams_in_league', 20)
    
    # Мотивация в зависимости от положения в таблице
    if position >= total_teams - 3:  # Зона вылета
        base_motivation += 0.15
    elif position <= 4:  # Зона еврокубков
        base_motivation += 0.12
    elif position <= 6:
        base_motivation += 0.08
    
    # Мотивация против сильного соперника
    strength_diff = opponent_strength - (team["attack_power"] + team["defense_power"])/2
    if strength_diff > 0.3:
        base_motivation += 0.08  # Дополнительная мотивация против фаворита
    elif strength_diff < -0.3:
        base_motivation -= 0.03  # Меньше мотивации против аутсайдера
    
    # Учет формы
    if team.get('last_results'):
        recent_form = sum(team['last_results'][-5:]) / min(5, len(team['last_results']))
        if recent_form > 0.7:
            base_motivation += 0.06
        elif recent_form < 0.2:
            base_motivation -= 0.04
    
    return min(0.35, max(0.0, base_motivation))

def calculate_dynamic_attack_enhanced(team: Dict, opponent: Dict, league_params: Dict) -> float:
    """Улучшенный динамический расчет атаки"""
    base_attack = team["attack_power"]
    
    # Усиление атаки против слабой защиты
    defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
    # Учет формы с весами
    form_boost = TeamDataEnhancer.calculate_form_impact(team.get('last_results', []))
    
    # Учет мотивации
    motivation_boost = 1.0 + team.get('motivation', 0) * 1.5
    
    # Учет реальной голевой эффективности
    goals_scored_factor = team.get("characteristics", {}).get("avg_goals_scored", 1.2) / 1.2
    
    # Лига-специфичный множитель
    league_scoring_factor = league_params.get('scoring_factor', 1.0)
    
    result = base_attack * defense_multiplier * form_boost * motivation_boost * goals_scored_factor * league_scoring_factor
    
    return max(0.2, min(3.0, result))

def calculate_goal_efficiency_enhanced(team1: Dict, team2: Dict, league_name: str) -> Dict:
    """Улучшенный расчет голевой эффективности с калибровкой по лиге"""
    
    league_params = LeagueCalibrator.get_league_factor(league_name)
    
    # Расчет мотивации с учетом силы соперника
    team2_strength = (team2["attack_power"] + team2["defense_power"]) / 2
    team1_strength = (team1["attack_power"] + team1["defense_power"]) / 2
    
    team1['motivation'] = calculate_motivation_enhanced(team1, 'обычный', team2_strength)
    team2['motivation'] = calculate_motivation_enhanced(team2, 'обычный', team1_strength)
    
    # Динамическая сила атаки
    team1_goal_potential = calculate_dynamic_attack_enhanced(team1, team2, league_params)
    team2_goal_potential = calculate_dynamic_attack_enhanced(team2, team1, league_params)
    
    # Корректировка на домашнее поле с учетом лиги
    home_advantage = league_params.get('home_advantage', 1.1)
    if team1["is_home"]:
        team1_goal_potential *= home_advantage
        team2_goal_potential *= (2 - home_advantage)  # Симметричное уменьшение
    else:
        team1_goal_potential *= (2 - home_advantage)
        team2_goal_potential *= home_advantage
    
    # Учет тактических схем
    formation_impact = calculate_formation_matchup_impact(team1, team2)
    team1_goal_potential *= formation_impact["team1_attack_boost"]
    team2_goal_potential *= formation_impact["team2_attack_boost"]
    
    # Учет звездных игроков
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.8:
        team1_goal_potential *= 1.2
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.8:
        team2_goal_potential *= 1.2
    
    # Калибровка под среднюю результативность лиги
    avg_goals_league = league_params.get('avg_goals', 2.5)
    current_total = team1_goal_potential + team2_goal_potential
    if current_total > 0:
        calibration_factor = avg_goals_league / current_total
        team1_goal_potential *= calibration_factor * 0.9  # Небольшая коррекция
        team2_goal_potential *= calibration_factor * 0.9
    
    return {
        "team1_goals": max(0.3, min(4.0, team1_goal_potential)),
        "team2_goals": max(0.3, min(4.0, team2_goal_potential)),
        "total_goals": team1_goal_potential + team2_goal_potential
    }

def calculate_formation_matchup_impact(team1: Dict, team2: Dict) -> Dict:
    """Расчет влияния тактических схем"""
    formation1 = team1.get("characteristics", {}).get("formation", "4-4-2")
    formation2 = team2.get("characteristics", {}).get("formation", "4-4-2")
    
    # Базовые коэффициенты
    team1_attack = 1.0
    team2_attack = 1.0
    
    # Простые тактические противостояния
    formation_matchups = {
        "4-3-3": {"weak_vs": ["4-4-2"], "strong_vs": ["3-5-2"]},
        "4-4-2": {"weak_vs": ["3-5-2"], "strong_vs": ["4-3-3"]},
        "3-5-2": {"weak_vs": ["4-3-3"], "strong_vs": ["4-4-2"]},
        "4-2-3-1": {"weak_vs": ["4-4-2"], "strong_vs": ["4-3-3"]}
    }
    
    if formation1 in formation_matchups and formation2 in formation_matchups:
        if formation2 in formation_matchups[formation1]["weak_vs"]:
            team1_attack = 1.15
        elif formation2 in formation_matchups[formation1]["strong_vs"]:
            team1_attack = 0.9
    
    return {
        "team1_attack_boost": team1_attack,
        "team2_attack_boost": team2_attack,
        "matchup_description": f"{formation1} vs {formation2}"
    }

def calculate_both_teams_to_score_enhanced(team1: Dict, team2: Dict, goal_potential: Dict) -> float:
    """Улучшенный расчет 'Обе забьют'"""
    
    # Базовые вероятности на основе голевого потенциала
    team1_scores_prob = 1 - poisson_probability(goal_potential["team1_goals"], 0)
    team2_scores_prob = 1 - poisson_probability(goal_potential["team2_goals"], 0)
    
    both_score_prob = team1_scores_prob * team2_scores_prob
    
    # Корректировка на стиль команд
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    
    if style1 == "атакующая" and style2 == "атакующая":
        both_score_prob *= 1.4
    elif style1 == "оборонительная" and style2 == "оборонительная":
        both_score_prob *= 0.6
    elif style1 == "атакующая" or style2 == "атакующая":
        both_score_prob *= 1.2
    
    # Учет реальной статистики "обе забьют"
    team1_btc = team1.get("both_teams_scored_rate", 0.5)
    team2_btc = team2.get("both_teams_scored_rate", 0.5)
    historical_factor = (team1_btc + team2_btc) / 2
    
    both_score_prob = (both_score_prob * 0.7) + (historical_factor * 0.3)
    
    return min(0.85, max(0.15, both_score_prob))

def detect_upset_potential_enhanced(team1: Dict, team2: Dict) -> Dict:
    """Улучшенный детектор сенсаций"""
    
    upset_factors = {
        "strong_attack_vs_weak_defense": False,
        "motivation_disparity": False,
        "star_player_impact": False,
        "recent_form_gap": False,
        "tactical_advantage": False
    }
    
    # Сильная атака против слабой защиты
    if team2["attack_power"] > team1["defense_power"] * 1.5:
        upset_factors["strong_attack_vs_weak_defense"] = True
    
    # Разница в мотивации
    motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
    if motivation_diff > 0.15:
        upset_factors["motivation_disparity"] = True
    
    # Влияние звездных игроков
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.85:
        upset_factors["star_player_impact"] = True
    
    # Разница в форме
    if team1.get('last_results') and team2.get('last_results'):
        form1 = sum(team1['last_results'][-5:]) / min(5, len(team1['last_results']))
        form2 = sum(team2['last_results'][-5:]) / min(5, len(team2['last_results']))
        if form2 > form1 * 1.8:
            upset_factors["recent_form_gap"] = True
    
    # Тактическое преимущество
    formation_impact = calculate_formation_matchup_impact(team1, team2)
    if formation_impact["team2_attack_boost"] > 1.1:
        upset_factors["tactical_advantage"] = True
    
    return upset_factors

def load_team_data_enhanced(file_path: str, is_home: bool, position_in_league: int, 
                           last_results: Optional[List[float]] = None,
                           formation: str = "4-4-2",
                           avg_goals_scored: float = 1.2,
                           avg_goals_conceded: float = 1.2,
                           both_teams_scored_rate: float = 0.5,
                           total_teams_in_league: int = 20,
                           league_name: str = "premier_league") -> Dict:
    """Улучшенная загрузка данных команды"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
    except:
        players = []
    
    # Расчет основных показателей
    avg_readiness, attack_power, defense_power, top_attackers = TeamDataEnhancer.calculate_team_strengths(players)
    
    # Учет формы
    form_coefficient = TeamDataEnhancer.calculate_form_impact(last_results or [])
    
    team_data = {
        'name': file_path.replace('.json', '').replace('output_with_readiness_', 'Команда '),
        'is_home': is_home,
        'position_in_league': position_in_league,
        'total_teams_in_league': total_teams_in_league,
        'last_results': last_results or [],
        'players': players,
        'avg_readiness': avg_readiness,
        'attack_power': attack_power * form_coefficient,
        'defense_power': defense_power * form_coefficient,
        'top_attackers': top_attackers,
        'form_coefficient': form_coefficient,
        'formation': formation,
        'avg_goals_scored': avg_goals_scored,
        'avg_goals_conceded': avg_goals_conceded,
        'both_teams_scored_rate': both_teams_scored_rate
    }
    
    # Добавляем анализ характеристик
    team_data['characteristics'] = TeamDataEnhancer.analyze_playing_style(team_data)
    
    return team_data

def calculate_match_probabilities_enhanced(team1: Dict, team2: Dict, weather: str, match_type: str, league_name: str = "premier_league") -> Dict:
    """Улучшенный расчет вероятностей с калибровкой"""
    
    # 1. Расчет голевого потенциала с калибровкой лиги
    goal_potential = calculate_goal_efficiency_enhanced(team1, team2, league_name)
    
    # 2. Расчет точных счетов через Пуассон
    exact_scores = calculate_exact_scores_dynamic(
        team1, team2, 
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
    # 3. Улучшенный детектор сенсаций
    upset_potential = detect_upset_potential_enhanced(team1, team2)
    
    # 4. Расчет основных рынков
    forecasts = {
        "1X2": calculate_1x2_from_poisson(exact_scores),
        "Тоталы": calculate_totals_from_poisson(exact_scores),
        "Обе забьют": {
            "Да": calculate_both_teams_to_score_enhanced(team1, team2, goal_potential),
            "Нет": 1 - calculate_both_teams_to_score_enhanced(team1, team2, goal_potential)
        },
        "Индивидуальные тоталы": calculate_individual_totals(
            goal_potential["team1_goals"], 
            goal_potential["team2_goals"]
        ),
        "Точный счет": dict(sorted(exact_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
        "Анализ матча": {
            **analyze_matchup_enhanced(team1, team2),
            "upset_alert": any(upset_potential.values()),
            "upset_factors": upset_potential,
            "goal_potential": goal_potential,
            "expected_total_goals": goal_potential["total_goals"],
            "league_adjustment": LeagueCalibrator.get_league_factor(league_name)
        }
    }
    
    return forecasts

def analyze_matchup_enhanced(team1: Dict, team2: Dict) -> Dict:
    """Улучшенный анализ противостояния"""
    analysis = {
        "style_matchup": "",
        "formation_matchup": "",
        "key_advantages": [],
        "potential_weaknesses": [],
        "expected_dynamics": "",
        "betting_insights": [],
        "tactical_analysis": ""
    }
    
    # Анализ стилей
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    analysis["style_matchup"] = f"{style1} vs {style2}"
    
    # Тактический анализ
    formation1 = team1["characteristics"]["formation"]
    formation2 = team2["characteristics"]["formation"]
    analysis["formation_matchup"] = f"{formation1} vs {formation2}"
    
    formation_impact = calculate_formation_matchup_impact(team1, team2)
    analysis["tactical_analysis"] = formation_impact["matchup_description"]
    
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
    
    # Ожидаемая динамика матча на основе реальной статистики
    avg_goals_expected = (team1["avg_goals_scored"] + team2["avg_goals_scored"] + 
                         team1["avg_goals_conceded"] + team2["avg_goals_conceded"]) / 2
    
    if avg_goals_expected > 3.0:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif avg_goals_expected < 2.0:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    # Домашнее преимущество
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    # Анализ "Обе забьют"
    btc_prob = (team1["both_teams_scored_rate"] + team2["both_teams_scored_rate"]) / 2
    if btc_prob > 0.6:
        analysis["betting_insights"].append("Обе забьют - вероятно")
    elif btc_prob < 0.4:
        analysis["betting_insights"].append("Обе забьют - маловероятно")
    
    return analysis

# Сохраняем оригинальные функции для совместимости
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
    over_35 = 0.0
    
    for score, prob in exact_scores.items():
        home_goals, away_goals = map(int, score.split('-'))
        total_goals = home_goals + away_goals
        
        if total_goals > 1.5:
            over_15 += prob
        if total_goals > 2.5:
            over_25 += prob
        if total_goals > 3.5:
            over_35 += prob
    
    return {
        ">1.5": over_15,
        "<1.5": 1 - over_15,
        ">2.5": over_25,
        "<2.5": 1 - over_25,
        ">3.5": over_35,
        "<3.5": 1 - over_35
    }

def calculate_individual_totals(mean_goals_team1: float, mean_goals_team2: float) -> Dict:
    """Расчет индивидуальных тоталов"""
    itb1_15 = 1 - (poisson_probability(mean_goals_team1, 0) + poisson_probability(mean_goals_team1, 1))
    itb2_15 = 1 - (poisson_probability(mean_goals_team2, 0) + poisson_probability(mean_goals_team2, 1))
    
    itb1_05 = 1 - poisson_probability(mean_goals_team1, 0)
    itb2_05 = 1 - poisson_probability(mean_goals_team2, 0)
    
    return {
        "ИТБ1 0.5": max(0.05, min(0.95, itb1_05)),
        "ИТМ1 0.5": max(0.05, min(0.95, 1 - itb1_05)),
        "ИТБ2 0.5": max(0.05, min(0.95, itb2_05)),
        "ИТМ2 0.5": max(0.05, min(0.95, 1 - itb2_05)),
        "ИТБ1 1.5": max(0.05, min(0.95, itb1_15)),
        "ИТМ1 1.5": max(0.05, min(0.95, 1 - itb1_15)),
        "ИТБ2 1.5": max(0.05, min(0.95, itb2_15)),
        "ИТМ2 1.5": max(0.05, min(0.95, 1 - itb2_15))
    }

def print_detailed_analysis_enhanced(forecast, team1, team2):
    """Улучшенный вывод анализа"""
    print(f"\n{'='*60}")
    print(f"📊 УЛУЧШЕННЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    print(f"{'='*60}")
    
    print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    print(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    print(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    print(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    print(f"Всего: {goal_potential['total_goals']:.2f} ожидаемых голов")
    
    print(f"\n🎯 СТИЛЬ И ТАКТИКА:")
    print(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['formation']})")
    print(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['formation']})")
    
    print(f"\n📊 РЕАЛЬНАЯ СТАТИСТИКА:")
    print(f"{team1['name']}: {team1['avg_goals_scored']:.1f} забивает / {team1['avg_goals_conceded']:.1f} пропускает в среднем")
    print(f"{team2['name']}: {team2['avg_goals_scored']:.1f} забивает / {team2['avg_goals_conceded']:.1f} пропускает в среднем")
    
    print(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    print(f"Стилевое противостояние: {analysis['style_matchup']}")
    print(f"Тактическое противостояние: {analysis['formation_matchup']}")
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

# Пример использования улучшенной версии
if __name__ == "__main__":
    # Загрузка данных с улучшенными параметрами
    team1 = load_team_data_enhanced(
        "output_with_readiness_1.json",
        league_name="serie_a_brazil",
        is_home=True,
        position_in_league=17,
        last_results=[0, 0, 0, 1, 0],
        formation="4-2-3-1",
        avg_goals_scored=0.9,
        avg_goals_conceded=1.4,
        both_teams_scored_rate=0.7
        
    )
    
    team2 = load_team_data_enhanced(
        "output_with_readiness_2.json",
        league_name="serie_a_brazil",
        is_home=False,
        position_in_league=1,
        last_results=[1, 1, 1, 1, 1],
        formation="4-3-3", 
        avg_goals_scored=1.1,
        avg_goals_conceded=1.3,
        both_teams_scored_rate=0.9
        
    )
    # Расчет прогноза с улучшенной моделью
    forecast = calculate_match_probabilities_enhanced(
        team1=team1,
        team2=team2,
        weather="sunny",
        match_type="еврокубки",
        league_name="serie_a_brazil"
    )
    
    # Вывод результатов
    print_detailed_analysis_enhanced(forecast, team1, team2)
    
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