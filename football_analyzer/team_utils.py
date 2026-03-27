import json
import numpy as np
import os
from typing import Dict, List, Tuple

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
    
    all_players = goalkeepers + defenders + midfielders + attackers
    avg_readiness = np.mean(all_players) if all_players else 0.5
    
    attacking_players = sorted(attackers, reverse=True)[:3]
    if midfielders:
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    defense_players = goalkeepers + defenders
    if midfielders:
        defense_players.append(np.mean(midfielders) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    top_attackers = sorted(attackers, reverse=True)[:3]
    
    return avg_readiness, attack_power, defense_power, top_attackers

def analyze_team_characteristics(team: Dict) -> Dict:
    """Анализ характеристик команды"""
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
    
    attack_ratio = attack / (defense + 0.1)
    if attack_ratio > 1.3:
        characteristics["style"] = "атакующая"
    elif attack_ratio < 0.8:
        characteristics["style"] = "оборонительная"
    else:
        characteristics["style"] = "сбалансированная"
    
    if attack > 0.7:
        characteristics["attack_level"] = "сильная"
        characteristics["strengths"].append("эффективная атака")
    elif attack < 0.4:
        characteristics["attack_level"] = "слабая"
        characteristics["weaknesses"].append("проблемы в атаке")
    else:
        characteristics["attack_level"] = "средняя"
    
    if defense > 0.7:
        characteristics["defense_level"] = "надежная"
        characteristics["strengths"].append("крепкая защита")
    elif defense < 0.4:
        characteristics["defense_level"] = "уязвимая"
        characteristics["weaknesses"].append("слабая оборона")
    else:
        characteristics["defense_level"] = "стабильная"
    
    total_power = attack + defense
    if total_power > 1.4:
        characteristics["balance"] = "сильная команда"
    elif total_power < 0.8:
        characteristics["balance"] = "слабая команда"
    else:
        characteristics["balance"] = "середняк"
    
    if team["top_attackers"] and team["top_attackers"][0] > 0.7:
        characteristics["strengths"].append("есть звездный игрок")
    
    if team.get("avg_readiness", 0.5) < 0.4:
        characteristics["weaknesses"].append("низкая готовность")
    
    return characteristics

def load_team_data_from_analysis(team_data: Dict, is_home: bool, team_name: str) -> Dict:
    """Загрузка данных команды из анализа матча"""
    try:
        position_in_league = team_data.get("position_in_league", 10)
        last_results = team_data.get("last_results", [])
        
        players = []
        avg_readiness = 0.5
        attack_power = 0.5
        defense_power = 0.5
        top_attackers = [0.5]
        
        if last_results:
            form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
        else:
            form_coefficient = 1.0
        
        position_factor = 1.0 - (position_in_league / 20) * 0.3
        
        attack_power = 0.5 * position_factor * form_coefficient
        defense_power = 0.5 * position_factor * form_coefficient
        
        scoring_stats = team_data.get("scoring_stats", {})
        if scoring_stats:
            home_avg_scored = scoring_stats.get("home", {}).get("avg_scored", 0.5)
            away_avg_scored = scoring_stats.get("away", {}).get("avg_scored", 0.5)
            
            if is_home:
                attack_power = min(0.9, max(0.3, home_avg_scored / 3.0))
            else:
                attack_power = min(0.9, max(0.3, away_avg_scored / 3.0))
            
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
        
        team_data_dict['characteristics'] = analyze_team_characteristics(team_data_dict)
        
        return team_data_dict
        
    except Exception as e:
        print(f"Ошибка загрузки данных команды {team_name}: {e}")
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
        if os.path.exists(res_file_path):
            with open(res_file_path, 'r', encoding='utf-8') as f:
                players = json.load(f)
        else:
            players = []
            print(f"⚠️ Файл с игроками не найден: {res_file_path}")
        
        avg_readiness, attack_power, defense_power, top_attackers = calculate_team_strengths(players)
        
        position_in_league = team_data.get("position_in_league", 10)
        last_results = team_data.get("last_results", [])
        
        if last_results:
            form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
        else:
            form_coefficient = 1.0
        
        scoring_stats = team_data.get("scoring_stats", {})
        if scoring_stats and players:
            home_avg_scored = scoring_stats.get("home", {}).get("avg_scored", 0.5)
            away_avg_scored = scoring_stats.get("away", {}).get("avg_scored", 0.5)
            
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
        
        team_data_dict['characteristics'] = analyze_team_characteristics(team_data_dict)
        
        return team_data_dict
        
    except Exception as e:
        print(f"❌ Ошибка загрузки команды {team_name} с игроками: {e}")
        return load_team_data_from_analysis(team_data, is_home, team_name)