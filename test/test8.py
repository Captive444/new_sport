import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

class BalancedFootballPredictor:
    """Сбалансированная модель предсказания футбольных матчей"""
    
    def __init__(self):
        # Более консервативные коэффициенты для лиг
        self.league_coefficients = {
            'premier_league': {
                'goal_multiplier': 1.1,  # уменьшено с 1.3
                'home_advantage': 1.12,  # уменьшено с 1.15
                'away_penalty': 0.92,    # уменьшено с 0.95
                'btts_bias': 1.05        # уменьшено с 1.1
            },
            'la_liga': {
                'goal_multiplier': 1.05,
                'home_advantage': 1.15,
                'away_penalty': 0.88,
                'btts_bias': 1.0
            },
            'serie_a': {
                'goal_multiplier': 0.95,
                'home_advantage': 1.08,
                'away_penalty': 0.94,
                'btts_bias': 0.85
            },
            'bundesliga': {
                'goal_multiplier': 1.15,  # уменьшено с 1.4
                'home_advantage': 1.18,   # уменьшено с 1.25
                'away_penalty': 0.88,     # уменьшено с 0.85
                'btts_bias': 1.1          # уменьшено с 1.2
            }
        }
        
        # Базовые настройки
        self.default_league = 'premier_league'
        self.min_goals = 0.3
        self.max_goals = 3.0  # уменьшено с 4.0
        
    def poisson_probability(self, mean: float, goals: int) -> float:
        """Расчет вероятности по распределению Пуассона"""
        if mean < 0:
            return 0.0
        return (mean ** goals) * exp(-mean) / factorial(goals)
    
    def calculate_dynamic_attack(self, team: Dict, opponent: Dict, league: str) -> float:
        """Сбалансированный расчет атаки"""
        base_attack = team["attack_power"]
        league_coef = self.league_coefficients[league]
        
        # Более консервативный расчет слабости защиты
        defense_weakness = max(0.1, 1.0 - opponent["defense_power"])
        defense_multiplier = 1.0 + defense_weakness * 0.8  # уменьшено с 1.2
        
        # Учет формы - менее агрессивный
        form_boost = 1.0
        if team.get('last_goals_scored'):
            avg_goals = np.mean(team['last_goals_scored'])
            form_boost = 0.8 + (avg_goals * 0.4)  # уменьшено влияние
        
        # Мотивация - уменьшено влияние
        motivation_boost = 1.0 + team.get('motivation', 0) * 2  # уменьшено с 3
        
        # Коэффициент лиги
        league_attack_boost = league_coef['goal_multiplier']
        
        # Ограничиваем максимальный множитель
        dynamic_attack = base_attack * defense_multiplier * form_boost * motivation_boost
        dynamic_attack = dynamic_attack * league_attack_boost
        
        return max(0.2, min(2.0, dynamic_attack))  # уменьшен максимум
    
    def calculate_pressure_factor(self, team1: Dict, team2: Dict) -> Tuple[float, float]:
        """Расчет фактора давления на команды"""
        pressure_team1 = 0.0
        pressure_team2 = 0.0
        
        pos1, pos2 = team1.get('position_in_league', 10), team2.get('position_in_league', 10)
        
        if pos1 >= 16:
            pressure_team1 += 0.12  # уменьшено
        if pos2 >= 16:
            pressure_team2 += 0.12
            
        if pos1 <= 3:
            pressure_team1 += 0.08  # уменьшено
        if pos2 <= 3:
            pressure_team2 += 0.08
            
        return pressure_team1, pressure_team2
    
    def calculate_goal_efficiency_v3(self, team1: Dict, team2: Dict, league: str) -> Dict:
        """Сбалансированный расчет голевой эффективности"""
        league_coef = self.league_coefficients[league]
        
        # Базовый расчет атаки
        team1_goal_potential = self.calculate_dynamic_attack(team1, team2, league)
        team2_goal_potential = self.calculate_dynamic_attack(team2, team1, league)
        
        # Корректировка на домашнее поле
        if team1["is_home"]:
            team1_goal_potential *= league_coef['home_advantage']
            team2_goal_potential *= league_coef['away_penalty']
        else:
            team1_goal_potential *= league_coef['away_penalty']
            team2_goal_potential *= league_coef['home_advantage']
        
        # Учет звездных игроков - уменьшено влияние
        if team1.get("top_attackers") and team1["top_attackers"][0] > 0.7:
            team1_goal_potential *= 1.15  # уменьшено с 1.35
            
        if team2.get("top_attackers") and team2["top_attackers"][0] > 0.7:
            team2_goal_potential *= 1.15
        
        # Фактор давления
        pressure_team1, pressure_team2 = self.calculate_pressure_factor(team1, team2)
        team1_goal_potential *= (1.0 - pressure_team1 * 0.2)  # уменьшено влияние
        team2_goal_potential *= (1.0 - pressure_team2 * 0.2)
        
        # КОНТРОЛЬ ПЕРЕУСИЛЕНИЯ: ограничиваем суммарный эффект
        total_multiplier = (team1_goal_potential / team1["attack_power"] + 
                          team2_goal_potential / team2["attack_power"]) / 2
        
        if total_multiplier > 2.0:  # если общий множитель слишком большой
            reduction_factor = 2.0 / total_multiplier
            team1_goal_potential *= reduction_factor
            team2_goal_potential *= reduction_factor
        
        # Гарантируем реалистичные значения
        team1_goal_potential = max(self.min_goals, min(self.max_goals, team1_goal_potential))
        team2_goal_potential = max(self.min_goals, min(self.max_goals, team2_goal_potential))
        
        return {
            "team1_goals": team1_goal_potential,
            "team2_goals": team2_goal_potential,
            "total_goals": team1_goal_potential + team2_goal_potential
        }
    
    def calculate_both_teams_to_score_v3(self, team1: Dict, team2: Dict, goal_potential: Dict, league: str) -> float:
        """Сбалансированный расчет 'Обе забьют'"""
        league_coef = self.league_coefficients[league]
        
        # Более консервативные вероятности
        team1_scores_prob = min(0.9, team1["attack_power"] * (1.3 - team2["defense_power"]))  # уменьшено
        team2_scores_prob = min(0.9, team2["attack_power"] * (1.3 - team1["defense_power"]))
        
        both_score_prob = (team1_scores_prob * team2_scores_prob) * 1.1  # уменьшено с 1.3
        
        # Корректировка на стиль команд
        style_multiplier = 1.0
        styles = [team1["characteristics"]["style"], team2["characteristics"]["style"]]
        
        if "атакующая" in styles and "атакующая" in styles:
            style_multiplier = 1.25  # уменьшено
        elif "оборонительная" in styles and "оборонительная" in styles:
            style_multiplier = 0.75  # увеличено
            
        both_score_prob *= style_multiplier
        
        # Корректировка на основе ожидаемых голов
        expected_btts = 1 - (self.poisson_probability(goal_potential["team1_goals"], 0) * 
                            self.poisson_probability(goal_potential["team2_goals"], 0))
        
        # Комбинируем оба подхода
        final_prob = (both_score_prob * 0.7 + expected_btts * 0.3) * league_coef['btts_bias']
        
        return min(0.85, max(0.15, final_prob))
    
    def detect_upset_potential_v3(self, team1: Dict, team2: Dict) -> Dict:
        """Более консервативный детектор сенсаций"""
        
        upset_factors = {
            "strong_attack_vs_weak_defense": False,
            "motivation_disparity": False,
            "star_player_impact": False,
            "recent_form_gap": False,
            "pressure_situation": False
        }
        
        # Более строгие критерии
        if (team2["attack_power"] > team1["defense_power"] * 1.5 or  # увеличено с 1.3
            team1["attack_power"] > team2["defense_power"] * 1.5):
            upset_factors["strong_attack_vs_weak_defense"] = True
        
        # Разница в мотивации
        motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
        if motivation_diff > 0.12:  # увеличено с 0.08
            upset_factors["motivation_disparity"] = True
        
        # Влияние звездных игроков - более строго
        if (team2.get("top_attackers") and team2["top_attackers"][0] > 0.8) or \
           (team1.get("top_attackers") and team1["top_attackers"][0] > 0.8):
            upset_factors["star_player_impact"] = True
        
        # Разница в форме
        if team1.get('last_results') and team2.get('last_results'):
            form1 = sum(team1['last_results']) / len(team1['last_results'])
            form2 = sum(team2['last_results']) / len(team2['last_results'])
            if form2 > form1 * 1.8 or form1 > form2 * 1.8:  # увеличено с 1.3
                upset_factors["recent_form_gap"] = True
        
        # Ситуация давления
        pos1, pos2 = team1.get('position_in_league', 10), team2.get('position_in_league', 10)
        if (pos1 <= 2 and pos2 >= 18) or (pos2 <= 2 and pos1 >= 18):  # более строго
            upset_factors["pressure_situation"] = True
        
        return upset_factors
    
    def apply_upset_correction_v3(self, goal_potential: Dict, upset_factors: Dict) -> Dict:
        """Консервативная коррекция для сенсационных матчей"""
        correction_factor = 1.0
        
        active_factors = sum(1 for factor in upset_factors.values() if factor)
        
        if active_factors >= 4:  # более строго
            correction_factor = 1.2  # уменьшено с 1.4
        elif active_factors == 3:
            correction_factor = 1.15
        elif active_factors == 2:
            correction_factor = 1.08
        elif active_factors == 1:
            correction_factor = 1.03
            
        return {
            "team1_goals": goal_potential["team1_goals"] * correction_factor,
            "team2_goals": goal_potential["team2_goals"] * correction_factor,
            "total_goals": goal_potential["total_goals"] * correction_factor
        }
    
    def calculate_exact_scores_dynamic_v3(self, team1: Dict, team2: Dict, 
                                        mean_goals_team1: float, mean_goals_team2: float, 
                                        max_goals=5) -> Dict:  # уменьшено с 6
        """Сбалансированный расчет точных счетов"""
        
        # Более строгие ограничения
        mean_goals_team1 = max(0.2, min(3.0, mean_goals_team1))  # уменьшено
        mean_goals_team2 = max(0.2, min(3.0, mean_goals_team2))
        
        scores = {}
        total_prob = 0.0
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob = self.poisson_probability(mean_goals_team1, i) * self.poisson_probability(mean_goals_team2, j)
                scores[f"{i}-{j}"] = prob
                total_prob += prob
        
        normalized_scores = {score: prob/total_prob for score, prob in scores.items()}
        top_scores = dict(sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)[:10])  # уменьшено
        
        return top_scores
    
    def calculate_1x2_from_poisson_v3(self, exact_scores: Dict) -> Dict:
        """Расчет 1X2"""
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
        
        return {
            "П1": round(p1, 3),
            "X": round(draw, 3),
            "П2": round(p2, 3)
        }
    
    def calculate_totals_from_poisson_v3(self, exact_scores: Dict) -> Dict:
        """Расчет тоталов"""
        over_15 = over_25 = over_35 = 0.0
        
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
            ">1.5": round(over_15, 3),
            "<1.5": round(1 - over_15, 3),
            ">2.5": round(over_25, 3),
            "<2.5": round(1 - over_25, 3),
            ">3.5": round(over_35, 3),
            "<3.5": round(1 - over_35, 3)
        }
    
    def calculate_individual_totals_v3(self, mean_goals_team1: float, mean_goals_team2: float) -> Dict:
        """Расчет индивидуальных тоталов"""
        itb1_05 = 1 - self.poisson_probability(mean_goals_team1, 0)
        itb1_15 = 1 - (self.poisson_probability(mean_goals_team1, 0) + 
                       self.poisson_probability(mean_goals_team1, 1))
        itb1_25 = 1 - (self.poisson_probability(mean_goals_team1, 0) + 
                       self.poisson_probability(mean_goals_team1, 1) +
                       self.poisson_probability(mean_goals_team1, 2))
        
        itb2_05 = 1 - self.poisson_probability(mean_goals_team2, 0)
        itb2_15 = 1 - (self.poisson_probability(mean_goals_team2, 0) + 
                       self.poisson_probability(mean_goals_team2, 1))
        itb2_25 = 1 - (self.poisson_probability(mean_goals_team2, 0) + 
                       self.poisson_probability(mean_goals_team2, 1) +
                       self.poisson_probability(mean_goals_team2, 2))
        
        return {
            "ИТБ1 0.5": max(0.05, min(0.95, round(itb1_05, 3))),
            "ИТМ1 0.5": max(0.05, min(0.95, round(1 - itb1_05, 3))),
            "ИТБ1 1.5": max(0.05, min(0.95, round(itb1_15, 3))),
            "ИТМ1 1.5": max(0.05, min(0.95, round(1 - itb1_15, 3))),
            "ИТБ1 2.5": max(0.05, min(0.95, round(itb1_25, 3))),
            "ИТМ1 2.5": max(0.05, min(0.95, round(1 - itb1_25, 3))),
            "ИТБ2 0.5": max(0.05, min(0.95, round(itb2_05, 3))),
            "ИТМ2 0.5": max(0.05, min(0.95, round(1 - itb2_05, 3))),
            "ИТБ2 1.5": max(0.05, min(0.95, round(itb2_15, 3))),
            "ИТМ2 1.5": max(0.05, min(0.95, round(1 - itb2_15, 3))),
            "ИТБ2 2.5": max(0.05, min(0.95, round(itb2_25, 3))),
            "ИТМ2 2.5": max(0.05, min(0.95, round(1 - itb2_25, 3)))
        }

    def calculate_team_strengths_v3(self, players: List[Dict]) -> Tuple[float, float, float, List[float]]:
        """Более консервативный расчет силы команды"""
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
                goalkeepers.append(readiness * 1.2)  # уменьшено
            elif 'защитник' in pos:
                defenders.append(readiness * 0.9)    # уменьшено
            elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
                attackers.append(readiness * 1.1)    # уменьшено
            elif 'полузащитник' in pos or 'хав' in pos:
                midfielders.append(readiness * 0.7)
                attackers.append(readiness * 0.2)    # уменьшено
            else:
                midfielders.append(readiness * 0.6)
        
        # Расчет общей готовности
        all_players = goalkeepers + defenders + midfielders + attackers
        avg_readiness = np.mean(all_players) if all_players else 0.5
        
        # Более консервативный расчет силы атаки
        attacking_players = sorted(attackers, reverse=True)[:3]  # уменьшено
        if midfielders:
            attacking_players.append(np.mean(sorted(midfielders, reverse=True)[:2]) * 0.4)  # уменьшено
        
        attack_power = np.mean(attacking_players) if attacking_players else 0.3
        
        # Более консервативный расчет силы защиты
        defense_players = []
        if goalkeepers:
            defense_players.append(np.mean(goalkeepers))  # среднее вместо максимума
        defense_players.extend(sorted(defenders, reverse=True)[:3])  # уменьшено
        if midfielders:
            defense_players.append(np.mean(sorted(midfielders, reverse=True)[:2]) * 0.3)  # уменьшено
        
        defense_power = np.mean(defense_players) if defense_players else 0.5
        
        # Топ-атакующие
        top_attackers = sorted(attackers, reverse=True)[:3]
        
        # Нормализуем значения к более реалистичному диапазону
        attack_power = min(1.0, attack_power)
        defense_power = min(1.0, defense_power)
        
        return avg_readiness, attack_power, defense_power, top_attackers

    def analyze_team_characteristics_v3(self, team: Dict) -> Dict:
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
        if team.get("top_attackers") and team["top_attackers"][0] > 0.7:
            characteristics["strengths"].append("есть звездный игрок")
        
        if readiness < 0.4:
            characteristics["weaknesses"].append("низкая готовность")
        
        return characteristics

    def calculate_motivation_v3(self, team: Dict, match_type: str, opponent_strength: float) -> float:
        """Более консервативный расчет мотивации"""
        base_motivation = {
            'вылет': 0.15,      # уменьшено
            'еврокубки': 0.12,  # уменьшено
            'дерби': 0.10,      # уменьшено
            'кубок': 0.08,      # уменьшено
            'обычный': 0.03     # уменьшено
        }.get(match_type, 0.03)
        
        position = team.get('position_in_league', 1)
        
        if position >= 16:
            base_motivation += 0.10  # уменьшено
        elif position <= 4:
            base_motivation += 0.08  # уменьшено
        elif position <= 6:
            base_motivation += 0.05
        elif position <= 8:
            base_motivation += 0.03
        
        # Учет силы соперника
        if opponent_strength > 0.7:
            base_motivation += 0.05  # уменьшено
        elif opponent_strength < 0.4:
            base_motivation -= 0.02
        
        # Учет формы
        if team.get('last_results'):
            win_rate = sum(team['last_results']) / len(team['last_results'])
            if win_rate > 0.6:
                base_motivation += 0.04  # уменьшено
            elif win_rate < 0.2:
                base_motivation += 0.03
        
        return min(0.2, max(0.0, base_motivation))  # уменьшен максимум

    def load_team_data_v3(self, file_path: str, is_home: bool, position_in_league: int, 
                         last_goals_scored: Optional[List[int]] = None,
                         last_results: Optional[List[int]] = None) -> Dict:
        """Загрузка данных команды"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                players = json.load(f)
        except:
            players = []
        
        # Расчет основных показателей
        avg_readiness, attack_power, defense_power, top_attackers = self.calculate_team_strengths_v3(players)
        
        # Учет формы
        if last_goals_scored:
            form_attack_coef = 0.8 + (np.mean(last_goals_scored) * 0.3)  # уменьшено
        else:
            form_attack_coef = 1.0
            
        if last_results:
            form_result_coef = 0.9 + (sum(last_results) / len(last_results)) * 0.2  # уменьшено
        else:
            form_result_coef = 1.0
        
        # Комбинированный коэффициент формы
        form_coefficient = (form_attack_coef * 0.6 + form_result_coef * 0.4)
        
        team_data = {
            'name': file_path.replace('.json', '').replace('output_with_readiness_', 'Команда '),
            'is_home': is_home,
            'position_in_league': position_in_league,
            'last_goals_scored': last_goals_scored or [],
            'last_results': last_results or [],
            'players': players,
            'avg_readiness': avg_readiness,
            'attack_power': attack_power * form_coefficient,
            'defense_power': defense_power * form_coefficient,
            'top_attackers': top_attackers,
            'form_coefficient': form_coefficient
        }
        
        # Добавляем анализ характеристик
        team_data['characteristics'] = self.analyze_team_characteristics_v3(team_data)
        
        return team_data

    def calculate_match_probabilities_v3(self, team1: Dict, team2: Dict, 
                                       weather: str, match_type: str, 
                                       league: str = 'premier_league') -> Dict:
        """Сбалансированный расчет вероятностей"""
        
        if league not in self.league_coefficients:
            league = self.default_league
        
        # Расчет мотивации
        team1_motivation = self.calculate_motivation_v3(team1, match_type, team2["attack_power"])
        team2_motivation = self.calculate_motivation_v3(team2, match_type, team1["attack_power"])
        team1['motivation'] = team1_motivation
        team2['motivation'] = team2_motivation
        
        # 1. Расчет голевого потенциала
        goal_potential = self.calculate_goal_efficiency_v3(team1, team2, league)
        
        # 2. Детектор сенсаций и коррекция
        upset_potential = self.detect_upset_potential_v3(team1, team2)
        if any(upset_potential.values()):
            goal_potential = self.apply_upset_correction_v3(goal_potential, upset_potential)
        
        # 3. Расчет точных счетов
        exact_scores = self.calculate_exact_scores_dynamic_v3(
            team1, team2, 
            goal_potential["team1_goals"], 
            goal_potential["team2_goals"]
        )
        
        # 4. Основные рынки
        forecasts = {
            "1X2": self.calculate_1x2_from_poisson_v3(exact_scores),
            "Тоталы": self.calculate_totals_from_poisson_v3(exact_scores),
            "Обе забьют": {
                "Да": round(self.calculate_both_teams_to_score_v3(team1, team2, goal_potential, league), 3),
                "Нет": round(1 - self.calculate_both_teams_to_score_v3(team1, team2, goal_potential, league), 3)
            },
            "Индивидуальные тоталы": self.calculate_individual_totals_v3(
                goal_potential["team1_goals"], 
                goal_potential["team2_goals"]
            ),
            "Точный счет": exact_scores,
            "Анализ матча": {
                "goal_potential": goal_potential,
                "upset_alert": any(upset_potential.values()),
                "upset_factors": upset_potential,
                "motivation_analysis": {
                    team1['name']: team1_motivation,
                    team2['name']: team2_motivation
                }
            }
        }
        
        return forecasts

# Пример использования
if __name__ == "__main__":
    predictor = BalancedFootballPredictor()
    
    # Тестовые данные
    team1 = predictor.load_team_data_v3(
        "output_with_readiness_1.json",
        is_home=True,
        position_in_league=4,
        last_goals_scored=[1, 2, 2, 0, 0],  # голы в последних матчах
        last_results=[0.5, 1, 1, 0, 1]   # результаты (1-победа, 0.5-ничья, 0-поражение)
    )
    
    team2 = predictor.load_team_data_v3(
        "output_with_readiness_2.json", 
        is_home=False,
        position_in_league=1,
        last_goals_scored=[3, 2, 2, 2, 1],
        last_results=[1, 1, 1, 1, 1]
    )
    # Расчет прогноза
    forecast = predictor.calculate_match_probabilities_v3(
        team1=team1,
        team2=team2,
        weather="sunny", 
        match_type="еврокубки",
        league="premier_league"
    )
    
    # Вывод результатов
    print(f"\n{'='*60}")
    print(f"⚖️  СБАЛАНСИРОВАННЫЙ АНАЛИЗ МАТЧА")
    print(f"{'='*60}")
    
    print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    print(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    print(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    print(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    print(f"Общий тотал: {goal_potential['total_goals']:.2f} голов")
    
    print(f"\n🎯 СТИЛЬ КОМАНД:")
    print(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    print(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    print(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    print(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        print(f"  {bet_type}: {prob:.3f}")
    
    print(f"\nТОТАЛЫ:")
    for bet_type, prob in forecast["Тоталы"].items():
        print(f"  {bet_type}: {prob:.3f}")
    
    print(f"\nОБЕ ЗАБЬЮТ:")
    for bet_type, prob in forecast["Обе забьют"].items():
        print(f"  {bet_type}: {prob:.3f}")
    
    print(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    itotals = forecast["Индивидуальные тоталы"]
    for i in range(0, len(itotals), 2):
        bet1, prob1 = list(itotals.items())[i]
        bet2, prob2 = list(itotals.items())[i+1]
        print(f"  {bet1}: {prob1:.3f} | {bet2}: {prob2:.3f}")
    
    print(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        print(f"  {score}: {prob:.4f}")
# import json
# import numpy as np
# from math import factorial, exp
# from typing import Dict, List, Optional, Tuple
# from datetime import datetime
# import warnings

# warnings.filterwarnings('ignore')

# class AdvancedFootballPredictor:
#     """Улучшенная модель предсказания футбольных матчей"""
    
#     def __init__(self):
#         # Динамические коэффициенты для разных лиг
#         self.league_coefficients = {
#             'premier_league': {
#                 'goal_multiplier': 1.3,
#                 'home_advantage': 1.15,
#                 'away_penalty': 0.95,
#                 'btts_bias': 1.1
#             },
#             'la_liga': {
#                 'goal_multiplier': 1.2,
#                 'home_advantage': 1.2,
#                 'away_penalty': 0.9,
#                 'btts_bias': 1.0
#             },
#             'serie_a': {
#                 'goal_multiplier': 1.1,
#                 'home_advantage': 1.1,
#                 'away_penalty': 0.95,
#                 'btts_bias': 0.9
#             },
#             'bundesliga': {
#                 'goal_multiplier': 1.4,
#                 'home_advantage': 1.25,
#                 'away_penalty': 0.85,
#                 'btts_bias': 1.2
#             }
#         }
        
#         # Базовые настройки
#         self.default_league = 'premier_league'
#         self.min_goals = 0.4
#         self.max_goals = 4.0
        
#     def poisson_probability(self, mean: float, goals: int) -> float:
#         """Расчет вероятности по распределению Пуассона"""
#         if mean < 0:
#             return 0.0
#         return (mean ** goals) * exp(-mean) / factorial(goals)
    
#     def calculate_dynamic_attack(self, team: Dict, opponent: Dict, league: str) -> float:
#         """Улучшенный расчет атаки с учетом лиги и контекста"""
#         base_attack = team["attack_power"]
#         league_coef = self.league_coefficients[league]
        
#         # Усиление атаки против слабой защиты (более агрессивно)
#         defense_weakness = max(0.1, 1.0 - opponent["defense_power"])
#         defense_multiplier = 1.0 + defense_weakness * 1.2  # было 0.8
        
#         # Учет формы (последние 5 матчей) - более сильное влияние
#         form_boost = 1.0
#         if team.get('last_goals_scored'):
#             avg_goals = np.mean(team['last_goals_scored'])
#             form_boost = 0.7 + (avg_goals * 0.6)  # было 0.4
            
#         # Учет мотивации для атаки
#         motivation_boost = 1.0 + team.get('motivation', 0) * 3  # было 2
        
#         # Коэффициент лиги для атаки
#         league_attack_boost = league_coef['goal_multiplier']
        
#         dynamic_attack = base_attack * defense_multiplier * form_boost * motivation_boost * league_attack_boost
        
#         return max(0.2, min(2.5, dynamic_attack))
    
#     def calculate_pressure_factor(self, team1: Dict, team2: Dict) -> Tuple[float, float]:
#         """Расчет фактора давления на команды"""
#         pressure_team1 = 0.0
#         pressure_team2 = 0.0
        
#         # Давление по позиции в таблице
#         pos1, pos2 = team1.get('position_in_league', 10), team2.get('position_in_league', 10)
        
#         # Команда в зоне вылета испытывает больше давления
#         if pos1 >= 16:
#             pressure_team1 += 0.15
#         if pos2 >= 16:
#             pressure_team2 += 0.15
            
#         # Лидер испытывает давление ожиданий
#         if pos1 <= 3:
#             pressure_team1 += 0.1
#         if pos2 <= 3:
#             pressure_team2 += 0.1
            
#         return pressure_team1, pressure_team2
    
#     def calculate_goal_efficiency_v2(self, team1: Dict, team2: Dict, league: str) -> Dict:
#         """Переработанный расчет голевой эффективности"""
#         league_coef = self.league_coefficients[league]
        
#         # Динамическая сила атаки
#         team1_goal_potential = self.calculate_dynamic_attack(team1, team2, league)
#         team2_goal_potential = self.calculate_dynamic_attack(team2, team1, league)
        
#         # Корректировка на домашнее поле (уменьшено влияние)
#         if team1["is_home"]:
#             team1_goal_potential *= league_coef['home_advantage']
#             team2_goal_potential *= league_coef['away_penalty']
#         else:
#             team1_goal_potential *= league_coef['away_penalty']
#             team2_goal_potential *= league_coef['home_advantage']
        
#         # Учет звездных игроков (усилено влияние)
#         if team1.get("top_attackers") and team1["top_attackers"][0] > 0.7:
#             team1_goal_potential *= 1.35  # было 1.25
            
#         if team2.get("top_attackers") and team2["top_attackers"][0] > 0.7:
#             team2_goal_potential *= 1.35  # было 1.25
        
#         # Фактор давления
#         pressure_team1, pressure_team2 = self.calculate_pressure_factor(team1, team2)
#         team1_goal_potential *= (1.0 - pressure_team1 * 0.3)  # давление снижает эффективность
#         team2_goal_potential *= (1.0 - pressure_team2 * 0.3)
        
#         # Гарантируем минимальную продуктивность
#         team1_goal_potential = max(self.min_goals, min(self.max_goals, team1_goal_potential))
#         team2_goal_potential = max(self.min_goals, min(self.max_goals, team2_goal_potential))
        
#         return {
#             "team1_goals": team1_goal_potential,
#             "team2_goals": team2_goal_potential,
#             "total_goals": team1_goal_potential + team2_goal_potential
#         }
    
#     def calculate_both_teams_to_score_v2(self, team1: Dict, team2: Dict, goal_potential: Dict, league: str) -> float:
#         """Улучшенный расчет 'Обе забьют' с учетом лиги"""
#         league_coef = self.league_coefficients[league]
        
#         # Базовые вероятности забить
#         team1_scores_prob = min(0.95, team1["attack_power"] * (1.5 - team2["defense_power"]))
#         team2_scores_prob = min(0.95, team2["attack_power"] * (1.5 - team1["defense_power"]))
        
#         # Общая вероятность
#         both_score_prob = (team1_scores_prob * team2_scores_prob) * 1.3  # было 1.2
        
#         # Корректировка на стиль команд
#         style_multiplier = 1.0
#         styles = [team1["characteristics"]["style"], team2["characteristics"]["style"]]
        
#         if "атакующая" in styles and "атакующая" in styles:
#             style_multiplier = 1.4  # было 1.3
#         elif "оборонительная" in styles and "оборонительная" in styles:
#             style_multiplier = 0.6  # было 0.7
            
#         both_score_prob *= style_multiplier
        
#         # Корректировка на основе ожидаемых голов
#         expected_btts = 1 - (self.poisson_probability(goal_potential["team1_goals"], 0) * 
#                             self.poisson_probability(goal_potential["team2_goals"], 0))
        
#         # Комбинируем оба подхода
#         final_prob = (both_score_prob * 0.6 + expected_btts * 0.4) * league_coef['btts_bias']
        
#         return min(0.92, max(0.08, final_prob))
    
#     def detect_upset_potential_v2(self, team1: Dict, team2: Dict) -> Dict:
#         """Улучшенный детектор сенсаций"""
        
#         upset_factors = {
#             "strong_attack_vs_weak_defense": False,
#             "motivation_disparity": False,
#             "star_player_impact": False,
#             "recent_form_gap": False,
#             "pressure_situation": False
#         }
        
#         # Сильная атака против слабой защиты (более чувствительно)
#         if (team2["attack_power"] > team1["defense_power"] * 1.3 or 
#             team1["attack_power"] > team2["defense_power"] * 1.3):
#             upset_factors["strong_attack_vs_weak_defense"] = True
        
#         # Разница в мотивации
#         motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
#         if motivation_diff > 0.08:  # было 0.1
#             upset_factors["motivation_disparity"] = True
        
#         # Влияние звездных игроков
#         if (team2.get("top_attackers") and team2["top_attackers"][0] > 0.7) or \
#            (team1.get("top_attackers") and team1["top_attackers"][0] > 0.7):
#             upset_factors["star_player_impact"] = True
        
#         # Разница в форме
#         if team1.get('last_results') and team2.get('last_results'):
#             form1 = sum(team1['last_results']) / len(team1['last_results'])
#             form2 = sum(team2['last_results']) / len(team2['last_results'])
#             if form2 > form1 * 1.3 or form1 > form2 * 1.3:  # было 1.5
#                 upset_factors["recent_form_gap"] = True
        
#         # Ситуация давления
#         pos1, pos2 = team1.get('position_in_league', 10), team2.get('position_in_league', 10)
#         if (pos1 <= 3 and pos2 >= 16) or (pos2 <= 3 and pos1 >= 16):
#             upset_factors["pressure_situation"] = True
        
#         return upset_factors
    
#     def apply_upset_correction(self, goal_potential: Dict, upset_factors: Dict) -> Dict:
#         """Применение корректировок для сенсационных матчей"""
#         correction_factor = 1.0
        
#         # Подсчитываем активные факторы сенсации
#         active_factors = sum(1 for factor in upset_factors.values() if factor)
        
#         if active_factors >= 3:
#             correction_factor = 1.4  # Высокий потенциал сенсации
#         elif active_factors == 2:
#             correction_factor = 1.25  # Средний потенциал
#         elif active_factors == 1:
#             correction_factor = 1.1   # Низкий потенциал
            
#         # Применяем коррекцию к голам
#         return {
#             "team1_goals": goal_potential["team1_goals"] * correction_factor,
#             "team2_goals": goal_potential["team2_goals"] * correction_factor,
#             "total_goals": goal_potential["total_goals"] * correction_factor
#         }
    
#     def calculate_exact_scores_dynamic_v2(self, team1: Dict, team2: Dict, 
#                                         mean_goals_team1: float, mean_goals_team2: float, 
#                                         max_goals=6) -> Dict:
#         """Улучшенный расчет точных счетов"""
        
#         # Гарантируем реалистичные значения
#         mean_goals_team1 = max(0.3, min(4.5, mean_goals_team1))
#         mean_goals_team2 = max(0.3, min(4.5, mean_goals_team2))
        
#         scores = {}
#         total_prob = 0.0
        
#         # Используем расширенный диапазон голов
#         for i in range(max_goals + 1):
#             for j in range(max_goals + 1):
#                 prob = self.poisson_probability(mean_goals_team1, i) * self.poisson_probability(mean_goals_team2, j)
#                 scores[f"{i}-{j}"] = prob
#                 total_prob += prob
        
#         # Нормализуем и возвращаем топ-15 счетов
#         normalized_scores = {score: prob/total_prob for score, prob in scores.items()}
#         top_scores = dict(sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)[:15])
        
#         return top_scores
    
#     def calculate_1x2_from_poisson_v2(self, exact_scores: Dict) -> Dict:
#         """Расчет 1X2 с округлением"""
#         p1 = 0.0
#         draw = 0.0
#         p2 = 0.0
        
#         for score, prob in exact_scores.items():
#             home_goals, away_goals = map(int, score.split('-'))
#             if home_goals > away_goals:
#                 p1 += prob
#             elif home_goals == away_goals:
#                 draw += prob
#             else:
#                 p2 += prob
        
#         # Округляем для лучшей читаемости
#         return {
#             "П1": round(p1, 3),
#             "X": round(draw, 3),
#             "П2": round(p2, 3)
#         }
    
#     def calculate_totals_from_poisson_v2(self, exact_scores: Dict) -> Dict:
#         """Расчет тоталов с дополнительными вариантами"""
#         over_15 = over_25 = over_35 = 0.0
        
#         for score, prob in exact_scores.items():
#             home_goals, away_goals = map(int, score.split('-'))
#             total_goals = home_goals + away_goals
            
#             if total_goals > 1.5:
#                 over_15 += prob
#             if total_goals > 2.5:
#                 over_25 += prob
#             if total_goals > 3.5:
#                 over_35 += prob
        
#         return {
#             ">1.5": round(over_15, 3),
#             "<1.5": round(1 - over_15, 3),
#             ">2.5": round(over_25, 3),
#             "<2.5": round(1 - over_25, 3),
#             ">3.5": round(over_35, 3),
#             "<3.5": round(1 - over_35, 3)
#         }
    
#     def calculate_individual_totals_v2(self, mean_goals_team1: float, mean_goals_team2: float) -> Dict:
#         """Расчет индивидуальных тоталов с большим диапазоном"""
#         # Вероятность, что команда забьет больше 0.5, 1.5, 2.5 голов
#         itb1_05 = 1 - self.poisson_probability(mean_goals_team1, 0)
#         itb1_15 = 1 - (self.poisson_probability(mean_goals_team1, 0) + 
#                        self.poisson_probability(mean_goals_team1, 1))
#         itb1_25 = 1 - (self.poisson_probability(mean_goals_team1, 0) + 
#                        self.poisson_probability(mean_goals_team1, 1) +
#                        self.poisson_probability(mean_goals_team1, 2))
        
#         itb2_05 = 1 - self.poisson_probability(mean_goals_team2, 0)
#         itb2_15 = 1 - (self.poisson_probability(mean_goals_team2, 0) + 
#                        self.poisson_probability(mean_goals_team2, 1))
#         itb2_25 = 1 - (self.poisson_probability(mean_goals_team2, 0) + 
#                        self.poisson_probability(mean_goals_team2, 1) +
#                        self.poisson_probability(mean_goals_team2, 2))
        
#         return {
#             "ИТБ1 0.5": max(0.05, min(0.95, itb1_05)),
#             "ИТМ1 0.5": max(0.05, min(0.95, 1 - itb1_05)),
#             "ИТБ1 1.5": max(0.05, min(0.95, itb1_15)),
#             "ИТМ1 1.5": max(0.05, min(0.95, 1 - itb1_15)),
#             "ИТБ1 2.5": max(0.05, min(0.95, itb1_25)),
#             "ИТМ1 2.5": max(0.05, min(0.95, 1 - itb1_25)),
#             "ИТБ2 0.5": max(0.05, min(0.95, itb2_05)),
#             "ИТМ2 0.5": max(0.05, min(0.95, 1 - itb2_05)),
#             "ИТБ2 1.5": max(0.05, min(0.95, itb2_15)),
#             "ИТМ2 1.5": max(0.05, min(0.95, 1 - itb2_15)),
#             "ИТБ2 2.5": max(0.05, min(0.95, itb2_25)),
#             "ИТМ2 2.5": max(0.05, min(0.95, 1 - itb2_25))
#         }
    
#     def calculate_team_strengths_v2(self, players: List[Dict]) -> Tuple[float, float, float, List[float]]:
#         """Улучшенный расчет силы команды"""
#         if not players:
#             return 0.5, 0.5, 0.5, [0.3]
        
#         goalkeepers = []
#         defenders = []
#         midfielders = []
#         attackers = []
        
#         for player in players:
#             pos = player['position'].lower()
#             readiness = player['readiness']
            
#             if 'вратарь' in pos:
#                 goalkeepers.append(readiness * 1.4)  # усилено влияние вратаря
#             elif 'защитник' in pos:
#                 defenders.append(readiness * 1.0)    # нормализовано
#             elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
#                 attackers.append(readiness * 1.2)    # усилено влияние
#             elif 'полузащитник' in pos or 'хав' in pos:
#                 midfielders.append(readiness * 0.8)  # нормализовано
#                 attackers.append(readiness * 0.3)    # уменьшен вклад в атаку
#             else:
#                 midfielders.append(readiness * 0.7)
        
#         # Расчет общей готовности
#         all_players = goalkeepers + defenders + midfielders + attackers
#         avg_readiness = np.mean(all_players) if all_players else 0.5
        
#         # Улучшенный расчет силы атаки
#         attacking_players = sorted(attackers, reverse=True)[:4]  # берем 4 лучших
#         if midfielders:
#             attacking_players.append(np.mean(sorted(midfielders, reverse=True)[:3]) * 0.5)
#         attack_power = np.mean(attacking_players) if attacking_players else 0.3
        
#         # Улучшенный расчет силы защиты
#         defense_players = []
#         if goalkeepers:
#             defense_players.append(max(goalkeepers))  # берем лучшего вратаря
#         defense_players.extend(sorted(defenders, reverse=True)[:4])  # 4 лучших защитника
#         if midfielders:
#             defense_players.append(np.mean(sorted(midfielders, reverse=True)[:2]) * 0.4)
        
#         defense_power = np.mean(defense_players) if defense_players else 0.5
        
#         # Топ-атакующие (3 лучших)
#         top_attackers = sorted(attackers, reverse=True)[:3]
        
#         return avg_readiness, attack_power, defense_power, top_attackers

#     def analyze_team_characteristics_v2(self, team: Dict) -> Dict:
#         """Улучшенный анализ характеристик команды"""
#         readiness = team["avg_readiness"]
#         attack = team["attack_power"]
#         defense = team["defense_power"]
        
#         characteristics = {
#             "style": "",
#             "attack_level": "",
#             "defense_level": "",
#             "balance": "",
#             "weaknesses": [],
#             "strengths": [],
#             "risk_factors": []
#         }
        
#         # Определение стиля (более чувствительно)
#         attack_ratio = attack / (defense + 0.1)
#         if attack_ratio > 1.4:
#             characteristics["style"] = "атакующая"
#         elif attack_ratio < 0.7:
#             characteristics["style"] = "оборонительная"
#         else:
#             characteristics["style"] = "сбалансированная"
        
#         # Уровень атаки
#         if attack > 0.75:
#             characteristics["attack_level"] = "сильная"
#             characteristics["strengths"].append("эффективная атака")
#         elif attack < 0.35:
#             characteristics["attack_level"] = "слабая"
#             characteristics["weaknesses"].append("проблемы в атаке")
#             characteristics["risk_factors"].append("низкая результативность")
#         else:
#             characteristics["attack_level"] = "средняя"
        
#         # Уровень защиты
#         if defense > 0.75:
#             characteristics["defense_level"] = "надежная"
#             characteristics["strengths"].append("крепкая защита")
#         elif defense < 0.35:
#             characteristics["defense_level"] = "уязвимая"
#             characteristics["weaknesses"].append("слабая оборона")
#             characteristics["risk_factors"].append("пропускает много голов")
#         else:
#             characteristics["defense_level"] = "стабильная"
        
#         # Баланс команды
#         total_power = attack + defense
#         if total_power > 1.5:
#             characteristics["balance"] = "сильная команда"
#         elif total_power < 0.7:
#             characteristics["balance"] = "слабая команда"
#             characteristics["risk_factors"].append("низкий общий уровень")
#         else:
#             characteristics["balance"] = "середняк"
        
#         # Анализ звездных игроков
#         if team.get("top_attackers") and team["top_attackers"][0] > 0.75:
#             characteristics["strengths"].append("есть звездный нападающий")
#         elif team.get("top_attackers") and team["top_attackers"][0] < 0.4:
#             characteristics["weaknesses"].append("отсутствуют лидеры в атаке")
        
#         if readiness < 0.4:
#             characteristics["weaknesses"].append("низкая готовность состава")
#             characteristics["risk_factors"].append("проблемы с готовностью")
        
#         return characteristics

#     def calculate_motivation_v2(self, team: Dict, match_type: str, opponent_strength: float) -> float:
#         """Улучшенный расчет мотивации"""
#         base_motivation = {
#             'вылет': 0.25,      # усилено
#             'еврокубки': 0.18,  # усилено
#             'дерби': 0.15,      # усилено
#             'кубок': 0.12,      # усилено
#             'обычный': 0.05     # усилено
#         }.get(match_type, 0.05)
        
#         position = team.get('position_in_league', 1)
        
#         # Мотивация в зависимости от положения в таблице
#         if position >= 16:
#             base_motivation += 0.15  # борьба за выживание
#         elif position <= 4:
#             base_motivation += 0.12  # борьба за чемпионство/еврокубки
#         elif position <= 6:
#             base_motivation += 0.08
#         elif position <= 8:
#             base_motivation += 0.05
        
#         # Учет силы соперника (больше мотивации против сильных)
#         if opponent_strength > 0.7:
#             base_motivation += 0.08
#         elif opponent_strength < 0.4:
#             base_motivation -= 0.03
        
#         # Учет формы
#         if team.get('last_results'):
#             win_rate = sum(team['last_results']) / len(team['last_results'])
#             if win_rate > 0.6:
#                 base_motivation += 0.06  # уверенность
#             elif win_rate < 0.2:
#                 base_motivation += 0.04  # отчаяние
        
#         return min(0.3, max(0.0, base_motivation))

#     def analyze_matchup_v2(self, team1: Dict, team2: Dict, goal_potential: Dict) -> Dict:
#         """Улучшенный анализ противостояния"""
#         analysis = {
#             "style_matchup": "",
#             "key_advantages": [],
#             "potential_weaknesses": [],
#             "expected_dynamics": "",
#             "betting_insights": [],
#             "risk_factors": []
#         }
        
#         # Анализ стилей
#         style1 = team1["characteristics"]["style"]
#         style2 = team2["characteristics"]["style"]
#         analysis["style_matchup"] = f"{style1} vs {style2}"
        
#         # Ключевые преимущества
#         if team1["attack_power"] > team2["defense_power"] * 1.3:
#             analysis["key_advantages"].append(f"{team1['name']} имеет атакующее преимущество")
#             analysis["betting_insights"].append("ИТБ1 1.5")
            
#         if team2["attack_power"] > team1["defense_power"] * 1.3:
#             analysis["key_advantages"].append(f"{team2['name']} может быть опасна в атаке")
#             analysis["betting_insights"].append("ИТБ2 1.5")
        
#         # Анализ слабостей
#         if team1["defense_power"] < 0.4:
#             analysis["potential_weaknesses"].append(f"У {team1['name']} проблемы в защите")
#             analysis["risk_factors"].append(f"Слабая защита {team1['name']}")
            
#         if team2["defense_power"] < 0.4:
#             analysis["potential_weaknesses"].append(f"У {team2['name']} слабая оборона")
#             analysis["risk_factors"].append(f"Слабая защита {team2['name']}")
        
#         # Ожидаемая динамика матча на основе голевого потенциала
#         total_goals = goal_potential["total_goals"]
#         if total_goals > 3.0:
#             analysis["expected_dynamics"] = "высокоочковый матч с голами"
#             analysis["betting_insights"].append("Тотал больше 2.5")
#             analysis["betting_insights"].append("Обе забьют - Да")
#         elif total_goals > 2.0:
#             analysis["expected_dynamics"] = "атакующий матч"
#             analysis["betting_insights"].append("Тотал больше 1.5")
#         elif total_goals < 1.5:
#             analysis["expected_dynamics"] = "оборонительный матч"
#             analysis["betting_insights"].append("Тотал меньше 2.5")
#         else:
#             analysis["expected_dynamics"] = "уравновешенная игра"
        
#         # Домашнее преимущество
#         if team1["is_home"]:
#             analysis["key_advantages"].append(f"{team1['name']} играет дома")
#         else:
#             analysis["key_advantages"].append(f"{team2['name']} играет в гостях")
        
#         return analysis

#     def load_team_data_v2(self, file_path: str, is_home: bool, position_in_league: int, 
#                          last_goals_scored: Optional[List[int]] = None,
#                          last_results: Optional[List[int]] = None) -> Dict:
#         """Улучшенная загрузка данных команды"""
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 players = json.load(f)
#         except:
#             players = []
        
#         # Расчет основных показателей
#         avg_readiness, attack_power, defense_power, top_attackers = self.calculate_team_strengths_v2(players)
        
#         # Учет формы через забитые голы
#         if last_goals_scored:
#             form_attack_coef = 0.8 + (np.mean(last_goals_scored) * 0.4)
#         else:
#             form_attack_coef = 1.0
            
#         # Учет результатов
#         if last_results:
#             form_result_coef = 0.85 + (sum(last_results) / len(last_results)) * 0.3
#         else:
#             form_result_coef = 1.0
        
#         # Комбинированный коэффициент формы
#         form_coefficient = (form_attack_coef * 0.6 + form_result_coef * 0.4)
        
#         team_data = {
#             'name': file_path.replace('.json', '').replace('output_with_readiness_', 'Команда '),
#             'is_home': is_home,
#             'position_in_league': position_in_league,
#             'last_goals_scored': last_goals_scored or [],
#             'last_results': last_results or [],
#             'players': players,
#             'avg_readiness': avg_readiness,
#             'attack_power': attack_power * form_coefficient,
#             'defense_power': defense_power * form_coefficient,
#             'top_attackers': top_attackers,
#             'form_coefficient': form_coefficient
#         }
        
#         # Добавляем анализ характеристик
#         team_data['characteristics'] = self.analyze_team_characteristics_v2(team_data)
        
#         return team_data

#     def calculate_match_probabilities_v2(self, team1: Dict, team2: Dict, 
#                                        weather: str, match_type: str, 
#                                        league: str = 'premier_league') -> Dict:
#         """Улучшенный расчет вероятностей"""
        
#         if league not in self.league_coefficients:
#             league = self.default_league
        
#         # Расчет мотивации с учетом силы соперника
#         team1_motivation = self.calculate_motivation_v2(team1, match_type, team2["attack_power"])
#         team2_motivation = self.calculate_motivation_v2(team2, match_type, team1["attack_power"])
#         team1['motivation'] = team1_motivation
#         team2['motivation'] = team2_motivation
        
#         # 1. Динамический расчет голевого потенциала
#         goal_potential = self.calculate_goal_efficiency_v2(team1, team2, league)
        
#         # 2. Детектор сенсаций и коррекция
#         upset_potential = self.detect_upset_potential_v2(team1, team2)
#         if any(upset_potential.values()):
#             goal_potential = self.apply_upset_correction(goal_potential, upset_potential)
        
#         # 3. Расчет точных счетов через Пуассон
#         exact_scores = self.calculate_exact_scores_dynamic_v2(
#             team1, team2, 
#             goal_potential["team1_goals"], 
#             goal_potential["team2_goals"]
#         )
        
#         # 4. Основные рынки
#         forecasts = {
#             "1X2": self.calculate_1x2_from_poisson_v2(exact_scores),
#             "Тоталы": self.calculate_totals_from_poisson_v2(exact_scores),
#             "Обе забьют": {
#                 "Да": round(self.calculate_both_teams_to_score_v2(team1, team2, goal_potential, league), 3),
#                 "Нет": round(1 - self.calculate_both_teams_to_score_v2(team1, team2, goal_potential, league), 3)
#             },
#             "Индивидуальные тоталы": self.calculate_individual_totals_v2(
#                 goal_potential["team1_goals"], 
#                 goal_potential["team2_goals"]
#             ),
#             "Точный счет": exact_scores,
#             "Анализ матча": {
#                 **self.analyze_matchup_v2(team1, team2, goal_potential),
#                 "upset_alert": any(upset_potential.values()),
#                 "upset_factors": upset_potential,
#                 "goal_potential": goal_potential,
#                 "motivation_analysis": {
#                     team1['name']: team1_motivation,
#                     team2['name']: team2_motivation
#                 }
#             },
#             "Мета-информация": {
#                 "league": league,
#                 "match_type": match_type,
#                 "calculation_time": datetime.now().isoformat(),
#                 "model_version": "v2.0"
#             }
#         }
        
#         return forecasts

#     def print_detailed_analysis_v2(self, forecast, team1, team2):
#         """Улучшенный детальный анализ"""
#         print(f"\n{'='*70}")
#         print(f"🎯 УЛУЧШЕННЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
#         print(f"{'='*70}")
        
#         print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
#         print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
#         print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
        
#         goal_potential = forecast["Анализ матча"]["goal_potential"]
#         print(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
#         print(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
#         print(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
#         print(f"Общий тотал: {goal_potential['total_goals']:.2f} голов")
        
#         print(f"\n🎯 СТИЛЬ И ХАРАКТЕРИСТИКИ:")
#         chars1 = team1['characteristics']
#         chars2 = team2['characteristics']
#         print(f"{team1['name']}: {chars1['style']} ({chars1['attack_level']} атака, {chars1['defense_level']} защита)")
#         print(f"  Сильные стороны: {', '.join(chars1['strengths']) if chars1['strengths'] else 'нет'}")
#         print(f"  Слабые стороны: {', '.join(chars1['weaknesses']) if chars1['weaknesses'] else 'нет'}")
        
#         print(f"\n{team2['name']}: {chars2['style']} ({chars2['attack_level']} атака, {chars2['defense_level']} защита)")
#         print(f"  Сильные стороны: {', '.join(chars2['strengths']) if chars2['strengths'] else 'нет'}")
#         print(f"  Слабые стороны: {', '.join(chars2['weaknesses']) if chars2['weaknesses'] else 'нет'}")
        
#         print(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
#         analysis = forecast["Анализ матча"]
#         print(f"Стилевое противостояние: {analysis['style_matchup']}")
#         print(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
        
#         # Мотивация
#         motivation = analysis['motivation_analysis']
#         print(f"\n💪 МОТИВАЦИЯ:")
#         print(f"{team1['name']}: {motivation[team1['name']]:.2f}")
#         print(f"{team2['name']}: {motivation[team2['name']]:.2f}")
        
#         if analysis["upset_alert"]:
#             print(f"\n🚨 ВНИМАНИЕ: Высокий потенциал сенсации!")
#             for factor, active in analysis["upset_factors"].items():
#                 if active:
#                     print(f"   • {factor}")
        
#         if analysis["key_advantages"]:
#             print(f"\n✅ ПРЕИМУЩЕСТВА:")
#             for advantage in analysis["key_advantages"]:
#                 print(f"  • {advantage}")
        
#         if analysis["potential_weaknesses"]:
#             print(f"\n⚠️ СЛАБЫЕ СТОРОНЫ:")
#             for weakness in analysis["potential_weaknesses"]:
#                 print(f"  • {weakness}")
                
#         if analysis.get("risk_factors"):
#             print(f"\n🔴 ФАКТОРЫ РИСКА:")
#             for risk in analysis["risk_factors"]:
#                 print(f"  • {risk}")
        
#         if analysis["betting_insights"]:
#             print(f"\n💡 СТАТИСТИЧЕСКИЕ ВЫВОДЫ:")
#             for insight in analysis["betting_insights"]:
#                 print(f"  • {insight}")

#     def print_forecasts_v2(self, forecast):
#         """Улучшенный вывод прогнозов"""
#         print(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
        
#         print(f"\n1X2:")
#         for bet_type, prob in forecast["1X2"].items():
#             print(f"  {bet_type}: {prob:.3f}")
        
#         print(f"\nТОТАЛЫ:")
#         for bet_type, prob in forecast["Тоталы"].items():
#             print(f"  {bet_type}: {prob:.3f}")
        
#         print(f"\nОБЕ ЗАБЬЮТ:")
#         for bet_type, prob in forecast["Обе забьют"].items():
#             print(f"  {bet_type}: {prob:.3f}")
        
#         print(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
#         itotals = forecast["Индивидуальные тоталы"]
#         for i in range(0, len(itotals), 2):
#             bet1, prob1 = list(itotals.items())[i]
#             bet2, prob2 = list(itotals.items())[i+1]
#             print(f"  {bet1}: {prob1:.3f} | {bet2}: {prob2:.3f}")
        
#         print(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
#         for score, prob in list(forecast["Точный счет"].items())[:5]:
#             print(f"  {score}: {prob:.4f}")

# # Пример использования
# if __name__ == "__main__":
#     predictor = AdvancedFootballPredictor()
    
#     # Тестовые данные
#     team1 = predictor.load_team_data_v2(
#         "output_with_readiness_1.json",
#         is_home=True,
#         position_in_league=18,
#         last_goals_scored=[3, 3, 1, 0, 0],  # голы в последних матчах
#         last_results=[1, 0, 0, 0, 0.5]      # результаты (1-победа, 0.5-ничья, 0-поражение)
#     )
    
#     team2 = predictor.load_team_data_v2(
#         "output_with_readiness_2.json", 
#         is_home=False,
#         position_in_league=17,
#         last_goals_scored=[0, 3, 2, 1, 0],
#         last_results=[0, 1, 1, 0, 0]
#     )
    
#     # Расчет прогноза
#     forecast = predictor.calculate_match_probabilities_v2(
#         team1=team1,
#         team2=team2,
#         weather="sunny", 
#         match_type="еврокубки",
#         league="premier_league"
#     )
    
#     # Вывод результатов
#     predictor.print_detailed_analysis_v2(forecast, team1, team2)
#     predictor.print_forecasts_v2(forecast)