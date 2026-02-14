import json
import numpy as np
import os
import sys
from pathlib import Path
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from datetime import datetime

###############################################################################
# МАТЕМАТИЧЕСКИЕ ФУНКЦИИ
###############################################################################

def poisson_probability(mean, goals):
    """
    Расчет вероятности по распределению Пуассона
    Формула: P(k) = (λ^k * e^{-λ}) / k!
    где λ - среднее количество событий, k - количество событий
    """
    return (mean ** goals) * exp(-mean) / factorial(goals)


###############################################################################
# РАСЧЕТ СИЛЫ КОМАНД НА ОСНОВЕ ИГРОКОВ
###############################################################################

def calculate_team_strengths(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
    """
    Расчет силы команды на основе готовности игроков по позициям
    
    Позиционные коэффициенты:
    - Вратари: ×1.3 (важнейшая позиция для защиты)
    - Защитники: ×0.9 (ключевые для обороны)
    - Нападающие: ×1.1 (основные для атаки)
    - Полузащитники: ×0.7 для защиты + ×0.4 для атаки (двунаправленное влияние)
    
    Returns: (средняя_готовность, сила_атаки, сила_защиты, топ_3_нападающих)
    """
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
            # Вратари сильно влияют на защиту
            goalkeepers.append(readiness * 1.3)
        elif 'защитник' in pos:
            # Защитники - основа обороны
            defenders.append(readiness * 0.9)
        elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
            # Нападающие - ключевые для атаки
            attackers.append(readiness * 1.1)
        elif 'полузащитник' in pos or 'хав' in pos:
            # Полузащитники влияют и на атаку, и на защиту
            midfielders.append(readiness * 0.7)  # для защиты
            attackers.append(readiness * 0.4)    # для атаки
        else:
            # Остальные позиции считаем как полузащитников
            midfielders.append(readiness * 0.6)
            attackers.append(readiness * 0.4)
    
    # 1. Расчет средней готовности команды
    all_players = goalkeepers + defenders + midfielders + attackers
    avg_readiness = np.mean(all_players) if all_players else 0.5
    
    # 2. Расчет силы атаки
    attacking_players = sorted(attackers, reverse=True)[:3]  # Топ-3 нападающих
    if midfielders:
        # Добавляем вклад полузащиты (60% от средней готовности полузащитников)
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    # 3. Расчет силы защиты
    defense_players = goalkeepers + defenders  # Вратари + защитники
    if midfielders:
        # Добавляем вклад полузащиты в защиту (40% от средней готовности)
        defense_players.append(np.mean(midfielders) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    # 4. Топ-3 атакующих игрока (для учета звездных игроков)
    top_attackers = sorted(attackers, reverse=True)[:3]
    
    return avg_readiness, attack_power, defense_power, top_attackers


###############################################################################
# РАСЧЕТ С УЧЕТОМ СТАТИСТИКИ ГОЛОВ
###############################################################################

def calculate_team_stats_from_scoring(team_data: Dict, is_home: bool) -> Tuple[float, float]:
    """
    Расчет силы атаки и защиты на основе реальной статистики голов
    
    Использует данные из scoring_stats:
    - home.avg_scored: средние голы дома
    - home.avg_conceded: средние пропущенные дома  
    - away.avg_scored: средние голы в гостях
    - away.avg_conceded: средние пропущенные в гостях
    
    Преобразует статистику в диапазон 0.3-0.9 для совместимости с моделью
    
    Returns: (attack_power, defense_power)
    """
    scoring_stats = team_data.get("scoring_stats", {})
    
    if not scoring_stats:
        # Если статистики нет, возвращаем средние значения
        return 0.5, 0.5
    
    if is_home:
        avg_scored = scoring_stats.get("home", {}).get("avg_scored", 0.5)
        avg_conceded = scoring_stats.get("home", {}).get("avg_conceded", 1.0)
    else:
        avg_scored = scoring_stats.get("away", {}).get("avg_scored", 0.5)
        avg_conceded = scoring_stats.get("away", {}).get("avg_conceded", 1.0)
    
    # Преобразуем статистику голов в силу атаки (0.3-0.9)
    # Базовое предположение: 1 гол за матч = 0.5 силы атаки
    attack_power = 0.3 + (avg_scored * 0.2)  # 0 гол = 0.3, 3 гола = 0.9
    attack_power = max(0.3, min(0.9, attack_power))
    
    # Преобразуем статистику пропущенных голов в силу защиты (0.3-0.9)
    # Базовое предположение: 1 гол пропущен = 0.5 силы защиты
    defense_power = 0.9 - (avg_conceded * 0.2)  # 0 пропущенных = 0.9, 3 пропущенных = 0.3
    defense_power = max(0.3, min(0.9, defense_power))
    
    return attack_power, defense_power


###############################################################################
# ДИНАМИЧЕСКИЙ РАСЧЕТ АТАКИ С УЧЕТОМ СОПЕРНИКА
###############################################################################

def calculate_dynamic_attack(team: Dict, opponent: Dict) -> float:
    """
    Динамический расчет атаки команды с учетом силы защиты соперника
    
    Формула: атака = базовая_атака × множитель_защиты × буст_формы × буст_мотивации
    
    Множитель защиты: усиливаем атаку против слабой защиты
    Буст формы: учитываем последние результаты (1-победа, 0.5-ничья, 0-поражение)
    Буст мотивации: учитывает важность матча и положение в таблице
    """
    base_attack = team["attack_power"]
    
    # 1. Усиление атаки против слабой защиты
    # Чем слабее защита соперника, тем больше множитель
    defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
    # 2. Учет формы команды (последние 5 матчей)
    form_boost = 1.0
    if team.get('last_results'):
        # Считаем средний результат (1-победа, 0.5-ничья, 0-поражение)
        recent_performance = sum(team['last_results']) / len(team['last_results'])
        # Хорошая форма (0.7+) дает буст до 1.12, плохая (0.3-) снижает до 0.92
        form_boost = 0.8 + (recent_performance * 0.4)
    
    # 3. Учет мотивации команды
    motivation_boost = 1.0 + team.get('motivation', 0) * 2
    
    # Итоговый расчет
    return base_attack * defense_multiplier * form_boost * motivation_boost


###############################################################################
# РАСЧЕТ ГОЛЕВОГО ПОТЕНЦИАЛА
###############################################################################

def calculate_goal_efficiency(team1: Dict, team2: Dict) -> Dict:
    """
    Расчет ожидаемого количества голов для каждой команды
    
    Основные факторы:
    1. Динамическая сила атаки против конкретной защиты
    2. Домашнее преимущество (хозяева +30%, гости -10%)
    3. Наличие звездных игроков (топ-нападающие с готовностью >0.7)
    4. Гарантия минимальной продуктивности (не менее 0.3 гола)
    """
    # 1. Динамическая сила атаки с учетом соперника
    team1_goal_potential = calculate_dynamic_attack(team1, team2)
    team2_goal_potential = calculate_dynamic_attack(team2, team1)
    
    # 2. Корректировка на домашнее поле
    if team1["is_home"]:
        team1_goal_potential *= 1.3  # Хозяева +30%
        team2_goal_potential *= 0.9  # Гости -10%
    else:
        team1_goal_potential *= 0.9  # Гости -10%
        team2_goal_potential *= 1.3  # Хозяева +30%
    
    # 3. Учет звездных игроков
    # Если есть нападающий с готовностью >0.7, увеличиваем голевой потенциал на 25%
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        team1_goal_potential *= 1.25
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        team2_goal_potential *= 1.25
    
    # 4. Гарантия минимальной продуктивности и ограничение максимума
    return {
        "team1_goals": max(0.3, min(4.0, team1_goal_potential)),
        "team2_goals": max(0.3, min(4.0, team2_goal_potential))
    }


###############################################################################
# РАСЧЕТ ВЕРОЯТНОСТЕЙ ДЛЯ РАЗНЫХ ТИПОВ СТАВОК
###############################################################################

def calculate_both_teams_to_score(team1: Dict, team2: Dict) -> float:
    """
    Расчет вероятности того, что обе команды забьют (Обе забьют - ДА)
    
    Формула: (вероятность_забить_1 × вероятность_забить_2) × 1.2
    
    Корректировки:
    - Обе атакующие команды: +30%
    - Обе оборонительные команды: -30%
    - Ограничение диапазона: 15%-85%
    """
    # Вероятность, что команда 1 забьет команде 2
    team1_scores = team1["attack_power"] * (1.3 - team2["defense_power"])
    
    # Вероятность, что команда 2 забьет команде 1  
    team2_scores = team2["attack_power"] * (1.3 - team1["defense_power"])
    
    # Общая вероятность, что обе забьют
    both_score_prob = team1_scores * team2_scores * 1.2
    
    # Корректировка на стиль команд
    if team1["characteristics"]["style"] == "атакующая" and team2["characteristics"]["style"] == "атакующая":
        both_score_prob *= 1.3  # Обе атакующие → больше голов
    elif team1["characteristics"]["style"] == "оборонительная" and team2["characteristics"]["style"] == "оборонительная":
        both_score_prob *= 0.7  # Обе оборонительные → меньше голов
    
    # Ограничиваем вероятности реалистичными значениями
    return min(0.85, max(0.15, both_score_prob))


def detect_upset_potential(team1: Dict, team2: Dict) -> Dict:
    """
    Обнаружение потенциала для неожиданного результата (сенсации)
    
    Анализирует факторы, которые могут привести к неожиданному результату:
    1. Сильная атака против слабой защиты
    2. Разница в мотивации команд
    3. Наличие звездных игроков у аутсайдера
    4. Большая разница в форме команд
    """
    upset_factors = {
        "strong_attack_vs_weak_defense": False,
        "motivation_disparity": False,
        "star_player_impact": False,
        "recent_form_gap": False
    }
    
    # 1. Сильная атака против слабой защиты
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        upset_factors["strong_attack_vs_weak_defense"] = True
    
    # 2. Разница в мотивации
    motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
    if motivation_diff > 0.1:
        upset_factors["motivation_disparity"] = True
    
    # 3. Влияние звездных игроков
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.75:
        upset_factors["star_player_impact"] = True
    
    # 4. Разница в форме
    if team1.get('last_results') and team2.get('last_results'):
        form1 = sum(team1['last_results']) / len(team1['last_results'])
        form2 = sum(team2['last_results']) / len(team2['last_results'])
        if form2 > form1 * 1.5:
            upset_factors["recent_form_gap"] = True
    
    return upset_factors


def calculate_exact_scores_dynamic(team1: Dict, team2: Dict, 
                                   mean_goals_team1: float, 
                                   mean_goals_team2: float, 
                                   max_goals=5) -> Dict:
    """
    Расчет вероятностей точных счетов на основе распределения Пуассона
    
    Использует среднее количество голов для каждой команды
    Рассчитывает вероятности всех комбинаций от 0-0 до max_goals-max_goals
    
    Args:
        mean_goals_team1: среднее ожидаемое количество голов команды 1
        mean_goals_team2: среднее ожидаемое количество голов команды 2
        max_goals: максимальное количество голов для расчета (по умолчанию 5)
    
    Returns: словарь {счет: вероятность}
    """
    # Гарантируем реалистичные значения
    mean_goals_team1 = max(0.4, mean_goals_team1)
    mean_goals_team2 = max(0.4, mean_goals_team2)
    
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_goals_team1, i) * poisson_probability(mean_goals_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    # Нормализуем вероятности (сумма = 1)
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}


###############################################################################
# РАСЧЕТ РАЗЛИЧНЫХ ТИПОВ СТАВОК
###############################################################################

def calculate_1x2_from_poisson(exact_scores: Dict) -> Dict:
    """
    Расчет вероятностей исходов (П1, Х, П2) на основе точных счетов
    
    П1: домашняя команда забила больше голов
    Х:  обе команды забили одинаковое количество голов
    П2: гостевая команда забила больше голов
    """
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
    """
    Расчет вероятностей тоталов голов
    
    Рассчитывает:
    - Тотал больше/меньше 1.5 голов
    - Тотал больше/меньше 2.5 голов
    - Тотал больше/меньше 3.5 голов
    
    Использует накопленные вероятности из точных счетов
    """
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
        ">1.5": over_15,
        "<1.5": 1 - over_15,
        ">2.5": over_25,
        "<2.5": 1 - over_25,
        ">3.5": over_35,
        "<3.5": 1 - over_35
    }


def calculate_individual_totals(mean_goals_team1: float, mean_goals_team2: float) -> Dict:
    """
    Расчет индивидуальных тоталов команд
    
    Индивидуальный тотал - количество голов конкретной команды
    
    Рассчитывает:
    - ИТБ/ИТМ 1.5: команда забьет больше/меньше 1.5 голов
    """
    # Вероятность, что команда забьет больше 1.5 голов
    itb1_15 = 1 - (poisson_probability(mean_goals_team1, 0) + 
                   poisson_probability(mean_goals_team1, 1))
    itb2_15 = 1 - (poisson_probability(mean_goals_team2, 0) + 
                   poisson_probability(mean_goals_team2, 1))
    
    return {
        "ИТБ1 1.5": max(0.05, min(0.95, itb1_15)),
        "ИТМ1 1.5": max(0.05, min(0.95, 1 - itb1_15)),
        "ИТБ2 1.5": max(0.05, min(0.95, itb2_15)),
        "ИТМ2 1.5": max(0.05, min(0.95, 1 - itb2_15))
    }


###############################################################################
# АНАЛИЗ ХАРАКТЕРИСТИК КОМАНД
###############################################################################

def analyze_team_characteristics(team: Dict) -> Dict:
    """
    Анализ стиля и характеристик команды на основе силы атаки и защиты
    
    Определяет:
    - Стиль игры (атакующая, оборонительная, сбалансированная)
    - Уровень атаки и защиты
    - Общую силу команды
    - Сильные и слабые стороны
    """
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
    
    # 1. Определение стиля игры
    attack_ratio = attack / (defense + 0.1)  # +0.1 чтобы избежать деления на 0
    if attack_ratio > 1.3:
        characteristics["style"] = "атакующая"
    elif attack_ratio < 0.8:
        characteristics["style"] = "оборонительная"
    else:
        characteristics["style"] = "сбалансированная"
    
    # 2. Уровень атаки
    if attack > 0.7:
        characteristics["attack_level"] = "сильная"
        characteristics["strengths"].append("эффективная атака")
    elif attack < 0.4:
        characteristics["attack_level"] = "слабая"
        characteristics["weaknesses"].append("проблемы в атаке")
    else:
        characteristics["attack_level"] = "средняя"
    
    # 3. Уровень защиты
    if defense > 0.7:
        characteristics["defense_level"] = "надежная"
        characteristics["strengths"].append("крепкая защита")
    elif defense < 0.4:
        characteristics["defense_level"] = "уязвимая"
        characteristics["weaknesses"].append("слабая оборона")
    else:
        characteristics["defense_level"] = "стабильная"
    
    # 4. Общая сила команды
    total_power = attack + defense
    if total_power > 1.4:
        characteristics["balance"] = "сильная команда"
    elif total_power < 0.8:
        characteristics["balance"] = "слабая команда"
        characteristics["weaknesses"].append("низкий общий уровень")
    else:
        characteristics["balance"] = "середняк"
    
    # 5. Анализ звездных игроков
    if team["top_attackers"] and team["top_attackers"][0] > 0.7:
        characteristics["strengths"].append("есть звездный игрок")
    
    # 6. Учет общей готовности
    if readiness < 0.4:
        characteristics["weaknesses"].append("низкая готовность состава")
    
    return characteristics


###############################################################################
# РАСЧЕТ МОТИВАЦИИ КОМАНД
###############################################################################

def calculate_motivation(team: Dict, match_type: str) -> float:
    """
    Расчет мотивации команды для конкретного матча
    
    Учитывает:
    1. Важность матча (вылет, еврокубки, дерби, кубок, обычный)
    2. Положение в турнирной таблице
    3. Текущую форму команды
    
    Returns: коэффициент мотивации от 0.0 до 0.25
    """
    # Базовая мотивация в зависимости от типа матча
    base_motivation = {
        'вылет': 0.20,      # Борьба за выживание
        'еврокубки': 0.15,  # Борьба за еврокубки
        'дерби': 0.12,      # Принципиальное противостояние
        'кубок': 0.10,      # Кубковый матч
        'обычный': 0.03     # Обычный матч
    }.get(match_type, 0.03)
    
    position = team.get('position_in_league', 1)
    
    # Мотивация в зависимости от положения в таблице
    if position >= 16:
        base_motivation += 0.12  # Борьба за выживание
    elif position <= 4:
        base_motivation += 0.10  # Борьба за чемпионство/еврокубки
    elif position <= 6:
        base_motivation += 0.07
    elif position <= 8:
        base_motivation += 0.04
    
    # Учет формы команды
    if team.get('last_results'):
        win_rate = sum(team['last_results']) / len(team['last_results'])
        if win_rate > 0.6:
            base_motivation += 0.04  # Хорошая форма повышает мотивацию
        elif win_rate < 0.2:
            base_motivation -= 0.03  # Плохая форма снижает мотивацию
    
    # Ограничиваем мотивацию разумными пределами
    return min(0.25, max(0.0, base_motivation))


###############################################################################
# АНАЛИЗ ПРОТИВОСТОЯНИЯ КОМАНД
###############################################################################

def analyze_matchup(team1: Dict, team2: Dict) -> Dict:
    """
    Анализ тактического противостояния команд
    
    Определяет:
    - Сочетание стилей команд
    - Ключевые преимущества каждой команды
    - Потенциальные слабости
    - Ожидаемую динамику матча
    - Статистические выводы для ставок
    """
    analysis = {
        "style_matchup": "",
        "key_advantages": [],
        "potential_weaknesses": [],
        "expected_dynamics": "",
        "betting_insights": []
    }
    
    # 1. Анализ стилей команд
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    analysis["style_matchup"] = f"{style1} vs {style2}"
    
    # 2. Ключевые преимущества
    # Атакующее преимущество (сильная атака против слабой защиты)
    if team1["attack_power"] > team2["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team1['name']} имеет атакующее преимущество")
        analysis["betting_insights"].append("ИТБ1 1.5")
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team2['name']} может быть опасна в атаке")
        analysis["betting_insights"].append("ИТБ2 1.5")
    
    # 3. Анализ слабостей
    if team1["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team1['name']} проблемы в защите")
    
    if team2["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team2['name']} слабая оборона")
    
    # 4. Ожидаемая динамика матча на основе силы атак
    total_attack = team1["attack_power"] + team2["attack_power"]
    if total_attack > 1.2:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif total_attack < 0.8:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    # 5. Домашнее преимущество
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    return analysis


###############################################################################
# ЗАГРУЗКА ДАННЫХ КОМАНД
###############################################################################

def load_team_data_from_analysis(team_data: Dict, is_home: bool, team_name: str, 
                                players: List[Dict] = None) -> Dict:
    """
    Загрузка и подготовка данных команды для анализа
    
    Объединяет:
    1. Статистику из analysis.json (голы, форма, положение)
    2. Данные игроков из *_res.json (если доступны)
    3. Расчетные показатели (сила атаки/защиты)
    
    Args:
        team_data: данные из analysis.json
        is_home: играет ли команда дома
        team_name: название команды
        players: список игроков (если None, будет использована статистика голов)
    
    Returns: подготовленный словарь с данными команды
    """
    try:
        # Базовые данные из анализа
        position_in_league = team_data.get("position_in_league", 10)
        last_results = team_data.get("last_results", [])
        
        # Учет формы команды
        if last_results:
            form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
        else:
            form_coefficient = 1.0
        
        # Если есть данные игроков, используем расчет на их основе
        if players and len(players) > 0:
            avg_readiness, attack_power, defense_power, top_attackers = calculate_team_strengths(players)
            
            # Корректируем на основе статистики голов
            stats_attack, stats_defense = calculate_team_stats_from_scoring(team_data, is_home)
            
            # Комбинируем расчет игроков и статистику (70% игроки, 30% статистика)
            attack_power = (attack_power * 0.7 + stats_attack * 0.3) * form_coefficient
            defense_power = (defense_power * 0.7 + stats_defense * 0.3) * form_coefficient
            
        else:
            # Если нет данных игроков, используем только статистику голов
            attack_power, defense_power = calculate_team_stats_from_scoring(team_data, is_home)
            attack_power *= form_coefficient
            defense_power *= form_coefficient
            avg_readiness = 0.5
            top_attackers = [0.5]
        
        team_data_dict = {
            'name': team_name,
            'is_home': is_home,
            'position_in_league': position_in_league,
            'last_results': last_results,
            'players': players or [],
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
        print(f"❌ Ошибка загрузки данных команды {team_name}: {e}")
        # Возвращаем базовые данные в случае ошибки
        return {
            'name': team_name,
            'is_home': is_home,
            'position_in_league': team_data.get("position_in_league", 10),
            'last_results': team_data.get("last_results", []),
            'players': players or [],
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


###############################################################################
# ОСНОВНОЙ РАСЧЕТ ПРОГНОЗОВ
###############################################################################

def calculate_match_probabilities(team1: Dict, team2: Dict, 
                                 weather: str = "sunny", 
                                 match_type: str = "обычный") -> Dict:
    """
    Основная функция расчета всех прогнозов на матч
    
    Процесс:
    1. Расчет мотивации команд
    2. Расчет голевого потенциала
    3. Детектор сенсаций
    4. Расчет точных счетов (Пуассон)
    5. Расчет всех типов ставок
    
    Returns: словарь со всеми прогнозами и аналитикой
    """
    # 1. Расчет мотивации команд
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    team1['motivation'] = team1_motivation
    team2['motivation'] = team2_motivation
    
    # 2. Динамический расчет голевого потенциала
    goal_potential = calculate_goal_efficiency(team1, team2)
    
    # 3. Детектор сенсаций
    upset_potential = detect_upset_potential(team1, team2)
    
    # 4. Расчет точных счетов через распределение Пуассона
    exact_scores = calculate_exact_scores_dynamic(
        team1, team2, 
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
    # 5. Расчет всех типов ставок
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
            "goal_potential": goal_potential,
            "motivation_analysis": {
                team1['name']: team1_motivation,
                team2['name']: team2_motivation
            }
        }
    }
    
    return forecasts


###############################################################################
# ВЫВОД РЕЗУЛЬТАТОВ
###############################################################################

def get_detailed_analysis_str(forecast, team1, team2) -> str:
    """Формирование строки с детальным анализом матча"""
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
    """Формирование строки с прогнозами на матч"""
    lines = []
    lines.append(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    lines.append(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        lines.append(f"  {bet_type}: {prob:.3f}")
    
    lines.append(f"\nТОТАЛЫ:")
    totals = forecast["Тоталы"]
    lines.append(f"  >1.5: {totals['>1.5']:.3f} | <1.5: {totals['<1.5']:.3f}")
    lines.append(f"  >2.5: {totals['>2.5']:.3f} | <2.5: {totals['<2.5']:.3f}")
    lines.append(f"  >3.5: {totals['>3.5']:.3f} | <3.5: {totals['<3.5']:.3f}")
    
    lines.append(f"\nОБЕ ЗАБЬЮТ:")
    btts = forecast["Обе забьют"]
    lines.append(f"  Да: {btts['Да']:.3f} | Нет: {btts['Нет']:.3f}")
    
    lines.append(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    itotals = forecast["Индивидуальные тоталы"]
    lines.append(f"  ИТБ1 1.5: {itotals['ИТБ1 1.5']:.3f} | ИТМ1 1.5: {itotals['ИТМ1 1.5']:.3f}")
    lines.append(f"  ИТБ2 1.5: {itotals['ИТБ2 1.5']:.3f} | ИТМ2 1.5: {itotals['ИТМ2 1.5']:.3f}")
    
    lines.append(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        lines.append(f"  {score}: {prob:.4f}")
    
    return "\n".join(lines)


###############################################################################
# ОБРАБОТКА ВСЕХ МАТЧЕЙ
###############################################################################

def process_all_matches(commands_dir: str = "commands") -> None:
    """
    Обработка всех матчей в указанной директории
    
    Процесс:
    1. Поиск всех папок с матчами
    2. Загрузка данных из analysis.json
    3. Загрузка данных игроков из *_res.json (если есть)
    4. Расчет прогнозов для каждого матча
    5. Сохранение результатов в файл
    """
    print(f"🔍 Поиск матчей в папке: {commands_dir}")
    
    # Находим все папки с матчами
    match_folders = []
    for root, dirs, files in os.walk(commands_dir):
        for file in files:
            if file.endswith("_analysis.json"):
                match_folders.append(root)
                break
    
    print(f"📁 Найдено папок с матчами: {len(match_folders)}")
    
    if not match_folders:
        print("❌ Не найдены папки с матчами!")
        return
    
    # Файл для сохранения результатов
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"all_matches_forecast_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"📊 СВОДКА ПРОГНОЗОВ НА ВСЕ МАТЧИ\n")
        f.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Использована статистика голов из analysis.json\n")
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
                
                # Загружаем данные игроков (если есть)
                home_players = []
                away_players = []
                
                home_res_file = os.path.join(match_folder, f"{home_team_name}_res.json")
                away_res_file = os.path.join(match_folder, f"{away_team_name}_res.json")
                
                if os.path.exists(home_res_file):
                    try:
                        with open(home_res_file, 'r', encoding='utf-8') as hf:
                            home_players = json.load(hf)
                    except Exception as e:
                        print(f"   ⚠️ Ошибка загрузки игроков домашней команды: {e}")
                
                if os.path.exists(away_res_file):
                    try:
                        with open(away_res_file, 'r', encoding='utf-8') as af:
                            away_players = json.load(af)
                    except Exception as e:
                        print(f"   ⚠️ Ошибка загрузки игроков гостевой команды: {e}")
                
                # Загружаем данные команд (с учетом доступных данных)
                team1 = load_team_data_from_analysis(home_data, True, home_team_name, home_players)
                team2 = load_team_data_from_analysis(away_data, False, away_team_name, away_players)
                
                # Определяем тип матча
                match_type = "обычный"
                league = match_data.get("league", "").lower()
                if "вылет" in league or "нижн" in league:
                    match_type = "вылет"
                elif "евро" in league or "лига чемпионов" in league or "лига европы" in league:
                    match_type = "еврокубки"
                elif "дерби" in match_name.lower():
                    match_type = "дерби"
                elif "кубок" in league:
                    match_type = "кубок"
                
                # Рассчитываем прогноз
                forecast = calculate_match_probabilities(
                    team1=team1,
                    team2=team2,
                    weather="sunny",
                    match_type=match_type
                )
                
                # Формируем вывод
                analysis_str = get_detailed_analysis_str(forecast, team1, team2)
                forecasts_str = get_forecasts_str(forecast)
                
                # Записываем в файл
                f.write(f"\n🎯 МАТЧ: {match_name}\n")
                f.write(f"📅 Дата: {match_data.get('date_time', 'Неизвестно')}\n")
                f.write(f"🏆 Лига: {match_data.get('league', 'Неизвестно')}\n")
                f.write(f"📊 Тип матча: {match_type}\n")
                f.write("-"*60 + "\n")
                
                # Добавляем статистику голов
                if home_data.get("scoring_stats") and away_data.get("scoring_stats"):
                    f.write(f"\n📈 СТАТИСТИКА ГОЛОВ:\n")
                    f.write(f"{home_team_name}: дома {home_data['scoring_stats']['home']['avg_scored']:.1f}-{home_data['scoring_stats']['home']['avg_conceded']:.1f}, ")
                    f.write(f"в гостях {home_data['scoring_stats']['away']['avg_scored']:.1f}-{home_data['scoring_stats']['away']['avg_conceded']:.1f}\n")
                    f.write(f"{away_team_name}: дома {away_data['scoring_stats']['home']['avg_scored']:.1f}-{away_data['scoring_stats']['home']['avg_conceded']:.1f}, ")
                    f.write(f"в гостях {away_data['scoring_stats']['away']['avg_scored']:.1f}-{away_data['scoring_stats']['away']['avg_conceded']:.1f}\n")
                
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
        f.write(f"Использована статистика: средние голы за матч\n")
        f.write(f"Тоталы рассчитаны: 1.5, 2.5, 3.5 голов\n")


###############################################################################
# ГЛАВНАЯ ФУНКЦИЯ
###############################################################################

if __name__ == "__main__":
    print("="*60)
    print("🏆 АНАЛИЗАТОР ФУТБОЛЬНЫХ МАТЧЕЙ V2.0")
    print("="*60)
    print("✨ Особенности версии 2.0:")
    print("• Использование реальной статистики голов")
    print("• Комбинированный расчет (игроки + статистика)")
    print("• Улучшенные тоталы: 1.5, 2.5, 3.5 голов")
    print("• Детектор сенсаций")
    print("• Анализ мотивации команд")
    print("="*60)
    
    # Обработка всех матчей в папке commands
    process_all_matches("commands")