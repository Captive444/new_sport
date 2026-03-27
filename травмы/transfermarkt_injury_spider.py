# scraper/transfermarkt_injury_spider.py

import json
import scrapy
import random
import os
from scrapy.exceptions import CloseSpider
from fake_useragent import UserAgent
from scrapy import Request

class TransfermarktInjurySpider(scrapy.Spider):
    """Парсер истории травм игроков с Transfermarkt"""
    
    name = "transfermarkt_injury_spider"
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': random.uniform(15, 30),
        'DOWNLOAD_TIMEOUT': 30,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 400, 403, 404, 408],
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.transfermarkt.world/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        },
        'USER_AGENT': UserAgent().random,
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': False,
    }
    
    def __init__(self, team_name=None, match_folder=None, *args, **kwargs):
        super(TransfermarktInjurySpider, self).__init__(*args, **kwargs)
        self.team_name = team_name 
        self.match_folder = match_folder
        self.ua = UserAgent()
        self.logger.info(f"Паук травм инициализирован для команды: {team_name}")
        self.logger.info(f"Папка для сохранения: {match_folder}")

    def start_requests(self):
        """Загрузка URL из JSON-файла"""
        try:
            with open('output_injuries.json', 'r', encoding='utf-8') as f:
                urls = json.load(f)
                self.logger.info(f"Загружено URL для парсинга травм: {len(urls)}")
                
                for i, url in enumerate(urls, 1):
                    self.logger.info(f"{i}/{len(urls)}: {url}")
                    yield Request(
                        url=url,
                        callback=self.parse,
                        headers={'User-Agent': self.ua.random},
                        meta={
                            'dont_redirect': True,
                            'retry_count': 0,
                            'original_url': url
                        }
                    )
                    
        except FileNotFoundError:
            self.logger.error("Файл output_injuries.json не найден")
            raise CloseSpider('Файл с URL не найден')
        except Exception as e:
            self.logger.error(f"Ошибка загрузки URL: {str(e)}")
            raise CloseSpider('Ошибка в стартовых URL')

    def parse(self, response):
        """Обработка страницы травм игрока"""
        if response.status != 200:
            self.logger.error(f"Ошибка {response.status}: {response.url}")
            return

        try:
            self.logger.info(f"Парсим травмы игрока: {response.url}")
            
            # Извлекаем ID игрока из URL
            player_id = response.url.split('/')[-1].split('?')[0]
            
            injury_data = {
                'player_name': self.parse_player_name(response),
                'player_id': player_id,
                'player_url': response.url.replace('/verletzungen/', '/profil/spieler/'),
                'injuries': self.parse_injuries(response),
                'total_injuries': self.get_total_injuries_count(response),
                'total_days_lost': self.get_total_days_lost(response),
                'total_matches_missed': self.get_total_matches_missed(response),
                'team': self.team_name
            }

            self.save_injury_data(injury_data)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга травм {response.url}: {str(e)}")

    def parse_player_name(self, response):
        """Извлечение имени игрока"""
        name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
        name = ' '.join([name.strip() for name in name_parts if name.strip()])
        return name if name else "Неизвестно"

    def parse_injuries(self, response):
        """Парсинг таблицы с травмами"""
        injuries = []
        
        # Находим таблицу с травмами
        injury_rows = response.xpath('//table[@class="items"]/tbody/tr')
        
        for row in injury_rows:
            injury = {
                'season': self.parse_season(row),
                'injury_type': self.parse_injury_type(row),
                'from_date': self.parse_from_date(row),
                'to_date': self.parse_to_date(row),
                'days': self.parse_days(row),
                'matches_missed': self.parse_matches_missed(row),
                'clubs': self.parse_clubs(row)
            }
            
            # Добавляем только если есть данные
            if injury['injury_type']:
                injuries.append(injury)
        
        return injuries

    def parse_season(self, row):
        """Парсинг сезона"""
        season = row.xpath('.//td[1]//text()').get()
        return season.strip() if season else None

    def parse_injury_type(self, row):
        """Парсинг типа травмы"""
        injury = row.xpath('.//td[2]//text()').get()
        return injury.strip() if injury else None

    def parse_from_date(self, row):
        """Парсинг даты начала травмы"""
        date = row.xpath('.//td[3]//text()').get()
        return date.strip() if date else None

    def parse_to_date(self, row):
        """Парсинг даты окончания травмы"""
        date = row.xpath('.//td[4]//text()').get()
        return date.strip() if date else None

    def parse_days(self, row):
        """Парсинг количества дней"""
        days_text = row.xpath('.//td[5]//text()').get()
        if days_text:
            try:
                # Извлекаем число из строки вида "16 дней"
                days = ''.join(filter(str.isdigit, days_text))
                return int(days) if days else 0
            except:
                return 0
        return 0

    def parse_matches_missed(self, row):
        """Парсинг количества пропущенных матчей"""
        matches = row.xpath('.//td[6]//span/text()').get()
        if matches:
            try:
                return int(matches)
            except:
                pass
        
        # Альтернативный способ - ищем число после иконок
        matches_text = row.xpath('.//td[6]//text()').getall()
        for text in matches_text:
            if text.strip().isdigit():
                return int(text.strip())
        return 0

    def parse_clubs(self, row):
        """Парсинг клубов, которые игрок пропустил"""
        clubs = []
        club_links = row.xpath('.//td[6]//a')
        
        for link in club_links:
            club_name = link.xpath('.//@title').get()
            club_url = link.xpath('.//@href').get()
            club_img = link.xpath('.//img/@src').get()
            
            if club_name:
                clubs.append({
                    'name': club_name,
                    'url': f"https://www.transfermarkt.world{club_url}" if club_url else None,
                    'logo': club_img
                })
        
        return clubs

    def get_total_injuries_count(self, response):
        """Получение общего количества травм"""
        injuries = self.parse_injuries(response)
        return len(injuries)

    def get_total_days_lost(self, response):
        """Подсчет общего количества пропущенных дней"""
        injuries = self.parse_injuries(response)
        return sum(injury.get('days', 0) for injury in injuries)

    def get_total_matches_missed(self, response):
        """Подсчет общего количества пропущенных матчей"""
        injuries = self.parse_injuries(response)
        return sum(injury.get('matches_missed', 0) for injury in injuries)

    def save_injury_data(self, injury_data):
        """Сохранение данных о травмах в папку матча"""
        file_name = os.path.join(self.match_folder, f"{self.team_name}_injuries.json")
        
        try:
            # Читаем существующие данные
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except FileNotFoundError:
                existing_data = []

            # Проверяем, есть ли уже такой игрок
            player_exists = False
            for i, existing_player in enumerate(existing_data):
                if existing_player.get('player_id') == injury_data['player_id']:
                    existing_data[i] = injury_data
                    player_exists = True
                    break

            # Если игрок не существует, добавляем его
            if not player_exists:
                existing_data.append(injury_data)

            # Сохраняем данные
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

            self.logger.info(f"Данные о травмах сохранены в: {file_name}")
            self.logger.info(f"  Всего травм: {injury_data['total_injuries']}")
            self.logger.info(f"  Пропущено дней: {injury_data['total_days_lost']}")
            self.logger.info(f"  Пропущено матчей: {injury_data['total_matches_missed']}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения в {file_name}: {str(e)}")