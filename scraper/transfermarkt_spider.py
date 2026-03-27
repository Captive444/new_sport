import json
import scrapy
import random
import os
from scrapy.exceptions import CloseSpider
from fake_useragent import UserAgent
from scrapy import Request

class TransfermarktSpider(scrapy.Spider):
    """Парсер статистики игроков с Transfermarkt"""
    
    name = "transfermarkt_spider"
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': random.uniform(15, 30),  # Увеличили задержку
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
        super(TransfermarktSpider, self).__init__(*args, **kwargs)
        self.team_name = team_name 
        self.match_folder = match_folder
        self.ua = UserAgent()
        self.logger.info(f"Паук инициализирован для команды: {team_name}")
        self.logger.info(f"Папка для сохранения: {match_folder}")

    def start_requests(self):
        """Загрузка URL из JSON-файла"""
        try:
            with open('output.json', 'r', encoding='utf-8') as f:
                urls = json.load(f)
                self.logger.info(f"Загружено URL для парсинга: {len(urls)}")
                
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
            self.logger.error("Файл output.json не найден")
            raise CloseSpider('Файл с URL не найден')
        except Exception as e:
            self.logger.error(f"Ошибка загрузки URL: {str(e)}")
            raise CloseSpider('Ошибка в стартовых URL')

    def parse(self, response):
        """Обработка страницы игрока"""
        if response.status != 200:
            self.logger.error(f"Ошибка {response.status}: {response.url}")
            return

        try:
            self.logger.info(f"Парсим игрока: {response.url}")
            
            position = self.parse_player_position(response)
            is_goalkeeper = 'вратарь' in position.lower()
            
            player_data = {
                'name': self.parse_player_name(response),
                'position': position,
                'age': self.parse_player_age(response),
                'height': self.parse_player_height(response),
                'stats': self.parse_player_stats(response, is_goalkeeper),
                'url': response.url,
                'team': self.team_name 
            }

            self.save_player_data(player_data)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга {response.url}: {str(e)}")

    def save_player_data(self, player_data):
        """Сохранение данных игрока в папку матча"""
        file_name = os.path.join(self.match_folder, f"{self.team_name}.json")
        
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
                if existing_player.get('url') == player_data['url']:
                    existing_data[i] = player_data
                    player_exists = True
                    break

            # Если игрок не существует, добавляем его
            if not player_exists:
                existing_data.append(player_data)

            # Сохраняем данные
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

            self.logger.info(f"Сохранено в: {file_name}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения в {file_name}: {str(e)}")

    # Остальные методы парсинга остаются без изменений
    def parse_player_name(self, response):
        """Извлечение имени игрока"""
        name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
        name = ' '.join([name.strip() for name in name_parts if name.strip()])
        return name if name else "Неизвестно"

    def parse_player_position(self, response):
        """Извлечение позиции игрока"""
        position = response.xpath('//li[contains(., "Амплуа:")]/span[@class="data-header__content"]/text()').get(default='').strip()
        return position if position else "Не указано"

    def parse_player_age(self, response):
        """Извлечение возраста игрока"""
        age_text = response.xpath('//span[@itemprop="birthDate"]/text()').get()
        if age_text:
            try:
                age = age_text.split('(')[-1].replace(')', '').strip()
                return int(age) if age.isdigit() else None
            except:
                return None
        return None

    def parse_player_height(self, response):
        """Извлечение роста игрока в см"""
        height_text = response.xpath('//span[@itemprop="height"]/text()').get()
        if height_text:
            try:
                height = height_text.replace(' м', '').replace(',', '.')
                return int(float(height) * 100)
            except:
                return None
        return None

    def parse_player_stats(self, response, is_goalkeeper):
        """Сбор статистики из подвала таблицы"""
        stats = {
            'seasons': [],
            'total_stats': self.parse_total_stats(response, is_goalkeeper)
        }
        return stats

    def parse_total_stats(self, response, is_goalkeeper):
        """Парсинг общей статистики"""
        try:
            table = response.xpath('//table[@class="items"]')
            if not table:
                return self.get_default_stats()

            footer = table.xpath('.//tfoot/tr')
            if not footer:
                return self.get_default_stats()

            if is_goalkeeper:
                total_stats = {
                    'total_matches': self.parse_int(footer.xpath('.//td[3]//text()').get()),
                    'total_goals': self.parse_int(footer.xpath('.//td[4]//text()').get()),
                    'total_own_goals': self.parse_int(footer.xpath('.//td[5]//text()').get()),
                    'total_substitutions_in': self.parse_int(footer.xpath('.//td[6]//text()').get()),
                    'total_substitutions_out': self.parse_int(footer.xpath('.//td[7]//text()').get()),
                    'total_yellow_cards': self.parse_int(footer.xpath('.//td[8]//text()').get()),
                    'total_yellow_red_cards': self.parse_int(footer.xpath('.//td[9]//text()').get()),
                    'total_red_cards': self.parse_int(footer.xpath('.//td[10]//text()').get()),
                    'total_goals_conceded': self.parse_int(footer.xpath('.//td[11]//text()').get()),
                    'total_clean_sheets': self.parse_int(footer.xpath('.//td[12]//text()').get()),
                    'total_minutes_played': self.parse_minutes(footer.xpath('.//td[13]//text()').get())
                }
            else:
                total_stats = {
                    'total_matches': self.parse_int(footer.xpath('.//td[3]//text()').get()),
                    'total_goals': self.parse_int(footer.xpath('.//td[4]//text()').get()),
                    'total_assists': self.parse_int(footer.xpath('.//td[5]//text()').get()),
                    'total_own_goals': self.parse_int(footer.xpath('.//td[6]//text()').get()),
                    'total_substitutions_in': self.parse_int(footer.xpath('.//td[7]//text()').get()),
                    'total_substitutions_out': self.parse_int(footer.xpath('.//td[8]//text()').get()),
                    'total_yellow_cards': self.parse_int(footer.xpath('.//td[9]//text()').get()),
                    'total_yellow_red_cards': self.parse_int(footer.xpath('.//td[10]//text()').get()),
                    'total_red_cards': self.parse_int(footer.xpath('.//td[11]//text()').get()),
                    'total_penalty_goals': self.parse_int(footer.xpath('.//td[12]//text()').get()),
                    'total_minutes_played': self.parse_minutes(footer.xpath('.//td[14]//text()').get())
                }

            return total_stats

        except Exception as e:
            self.logger.error(f"Ошибка парсинга статистики: {e}")
            return self.get_default_stats()

    def get_default_stats(self):
        """Статистика по умолчанию"""
        return {
            'total_matches': 0, 'total_goals': 0, 'total_assists': 0,
            'total_own_goals': 0, 'total_substitutions_in': 0, 'total_substitutions_out': 0,
            'total_yellow_cards': 0, 'total_yellow_red_cards': 0, 'total_red_cards': 0,
            'total_penalty_goals': 0, 'total_goals_conceded': 0, 'total_clean_sheets': 0,
            'total_minutes_played': 0
        }

    def parse_int(self, value):
        """Преобразование в целое число"""
        try:
            if value and value.strip() == '-':
                return 0
            return int(value.strip()) if value else 0
        except:
            return 0

    def parse_minutes(self, value):
        """Парсинг минут"""
        try:
            if value and value.strip() == '-':
                return 0
            cleaned_value = value.replace("'", "").replace(" ", "").strip()
            return int(cleaned_value) if cleaned_value else 0
        except:
            return 0