
import json
import scrapy
import random
import stem.process
from scrapy.exceptions import CloseSpider
from fake_useragent import UserAgent
from urllib.parse import urljoin
from scrapy import Request

class TransfermarktSpider(scrapy.Spider):
    """Парсер статистики игроков с Transfermarkt с переключением на Tor при 503 ошибках"""
    
    name = "transfermarkt_spider"
    
    custom_settings = {
        'FEEDS': {
            'output2.json': {
                'format': 'json',
                'encoding': 'utf-8',
                'indent': 4,
                'overwrite': True
            }
        },
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': random.uniform(25, 40), 
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.transfermarkt.world/'
        },
        'USER_AGENT': UserAgent().random,
        'RETRY_TIMES': 1,  # Только одна попытка перед переключением на Tor
        'RETRY_HTTP_CODES': [503],
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        }
    }

    def __init__(self, *args, **kwargs):
        super(TransfermarktSpider, self).__init__(*args, **kwargs)
        self.ua = UserAgent()
        self.tor_process = None
        self.use_tor = False  # Флаг для отслеживания использования Tor
        self.start_tor()

    def start_tor(self):
        """Улучшенная версия с проверкой подключения"""
        try:
            self.tor_process = stem.process.launch_tor_with_config(
                config={
                    'SocksPort': '9050',
                    'ControlPort': '9051',
                    'HTTPTunnelPort': '9080',  # Добавляем HTTP-прокси
                    'ExitNodes': '{us},{de}',  # Указываем конкретные страны
                    'StrictNodes': '1',  # Строго соблюдать выбор узлов
                },
                take_ownership=True,
                timeout=30  # Увеличиваем таймаут
            )
            
            # Проверка работоспособности
            if not self.check_tor_connection():
                raise ConnectionError("Tor не подключился")
                
            self.logger.info("Tor успешно запущен")
        except Exception as e:
            self.logger.error(f"Ошибка запуска Tor: {str(e)}")
            self.tor_process = None

    def check_tor_connection(self):
        """Проверка работоспособности Tor"""
        try:
            import requests
            session = requests.session()
            session.proxies = {
                'http': 'socks5h://localhost:9050',
                'https': 'socks5h://localhost:9050'
            }
            response = session.get('https://check.torproject.org/', timeout=10)
            return 'Congratulations' in response.text
        except Exception:
            return False

    def close_spider(self, spider):
        """Остановка Tor процесса при завершении работы паука"""
        if self.tor_process:
            self.tor_process.terminate()
            self.logger.info("Tor процесс остановлен")

    def start_requests(self):
        """Загрузка URL из JSON-файла"""
        try:
            with open('output.json', 'r', encoding='utf-8') as f:
                urls = json.load(f)
                for url in urls:
                    yield Request(
                        url=url,
                        callback=self.parse,
                        errback=self.errback_tor_fallback,
                        headers={'User-Agent': self.ua.random},
                        meta={
                            'dont_redirect': True,
                            'proxy': None,  # Первый запрос без прокси
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

    def errback_tor_fallback(self, failure):
        """Обработка ошибки 503 с переключением на Tor"""
        request = failure.request
        retry_count = request.meta.get('retry_count', 0)
        
        if retry_count >= 1 and not self.use_tor and self.tor_process:
            # Переключаемся на Tor
            self.use_tor = True
            self.logger.info("Переключаемся на Tor после ошибки 503")
            
            new_request = request.copy()
            new_request.meta['proxy'] = 'http://localhost:9050'  # Tor proxy
            new_request.meta['retry_count'] = retry_count + 1
            new_request.headers['User-Agent'] = self.ua.random
            new_request.dont_filter = True
            
            return new_request
        else:
            self.logger.error(f"Не удалось получить данные для {request.url} даже через Tor")
            return

    def parse(self, response):
        """Обработка страницы игрока"""
        if response.status != 200:
            self.logger.error(f"Ошибка {response.status}: {response.url}")
            return

        try:
            player_data = {
                'name': self.parse_player_name(response),
                'position': self.parse_player_position(response),
                'stats': self.parse_player_stats(response),
                'url': response.url,
                'via_tor': self.use_tor  # Добавляем информацию о способе доступа
            }
            yield player_data
            
            # После успешного запроса через Tor, продолжаем использовать его
            if self.use_tor:
                self.logger.info("Успешно получили данные через Tor, продолжаем использовать его")
            else:
                self.use_tor = False  # Возвращаемся к обычному режиму

        except Exception as e:
            self.logger.error(f"Ошибка парсинга {response.url}: {str(e)}")

    # Все остальные методы парсера остаются без изменений
    def parse_player_name(self, response):
        """Извлечение имени игрока"""
        name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
        return ' '.join([name.strip() for name in name_parts if name.strip()])

    # ... остальные методы parse_player_position, parse_player_stats и т.д. ...

    # Все остальные методы парсера остаются без изменений
    def parse_player_name(self, response):
        """Извлечение имени игрока"""
        name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
        return ' '.join([name.strip() for name in name_parts if name.strip()])

    def parse_player_position(self, response):
        """Извлечение позиции игрока"""
        return response.xpath('//li[contains(., "Амплуа:")]/span[@class="data-header__content"]/text()').get(default='').strip()

    def parse_player_stats(self, response):
        """Сбор всей статистики игрока"""
        position = self.parse_player_position(response)
        table = response.xpath('//div[@class="box"][.//h2[contains(., "Статистика выступлений")]]//table')
        
        if not table:
            self.logger.warning(f"Не найдена таблица статистики для {response.url}")
            return self.empty_stats(position)
        
        headers = self.parse_table_headers(table)
        seasons = [self.parse_season_row(row, headers, position) 
                  for row in table.xpath('.//tbody/tr') if self.parse_season_row(row, headers, position)]
        
        total_stats = self.parse_total_stats(table, position, headers)
        total_stats['seasons'] = seasons
        
        return total_stats

    def empty_stats(self, position):
        """Возвращает пустую статистику"""
        return {
            'matches': 0,
            'minutes': 0,
            'position_specific': self.init_position_stats(position),
            'cards': {'yellow': 0, 'yellow_red': 0, 'red': 0},
            'substitutions': {'in': 0, 'out': 0},
            'own_goals': 0,
            'seasons': []
        }

    def parse_table_headers(self, table):
        """Парсинг заголовков таблицы"""
        headers = {}
        for i, header in enumerate(table.xpath('.//thead/tr/th')):
            title = header.xpath('.//@title').get() or header.xpath('.//text()').get()
            if title and title.strip():
                headers[title.strip()] = i
        return headers

    def parse_season_row(self, row, headers, position):
        """Парсинг строки с данными сезона"""
        tournament_name = row.xpath('.//td[2]//a/text()').get(default='').strip()
        if not tournament_name:
            return None
            
        stats = {
            'name': tournament_name,
            'matches': self.parse_int(row.xpath(f'.//td[{headers.get("Матчи", 3)+1}]/text()').get()),
            'minutes': self.parse_minutes(row.xpath(f'.//td[{headers.get("Сыграно минут", -1)+1}]/text()').get()),
            'position_specific': self.init_position_stats(position),
            'cards': {
                'yellow': self.parse_int(row.xpath(f'.//td[{headers.get("Желтые карточки", -1)+1}]/text()').get()),
                'yellow_red': self.parse_int(row.xpath(f'.//td[{headers.get("Желтые/красные карточки", -1)+1}]/text()').get()),
                'red': self.parse_int(row.xpath(f'.//td[{headers.get("Красные карточки", -1)+1}]/text()').get())
            },
            'substitutions': {
                'in': self.parse_int(row.xpath(f'.//td[{headers.get("Вышел на замену", -1)+1}]/text()').get()),
                'out': self.parse_int(row.xpath(f'.//td[{headers.get("Заменен", -1)+1}]/text()').get())
            },
            'own_goals': self.parse_int(row.xpath(f'.//td[{headers.get("автоголы", -1)+1}]/text()').get())
        }
        
        self.update_position_stats(stats['position_specific'], row, headers, position)
        return stats

    def parse_total_stats(self, table, position, headers):
        """Парсинг итоговой статистики"""
        footer = table.xpath('.//tfoot/tr')
        
        stats = {
            'matches': self.parse_int(footer.xpath(f'.//td[{headers.get("Матчи", 3)+1}]/text()').get()),
            'minutes': self.parse_minutes(footer.xpath(f'.//td[{headers.get("Сыграно минут", -1)+1}]/text()').get()),
            'position_specific': self.init_position_stats(position),
            'cards': {
                'yellow': self.parse_int(footer.xpath(f'.//td[{headers.get("Желтые карточки", -1)+1}]/text()').get()),
                'yellow_red': self.parse_int(footer.xpath(f'.//td[{headers.get("Желтые/красные карточки", -1)+1}]/text()').get()),
                'red': self.parse_int(footer.xpath(f'.//td[{headers.get("Красные карточки", -1)+1}]/text()').get())
            },
            'substitutions': {
                'in': self.parse_int(footer.xpath(f'.//td[{headers.get("Вышел на замену", -1)+1}]/text()').get()),
                'out': self.parse_int(footer.xpath(f'.//td[{headers.get("Заменен", -1)+1}]/text()').get())
            },
            'own_goals': self.parse_int(footer.xpath(f'.//td[{headers.get("автоголы", -1)+1}]/text()').get())
        }
        
        self.update_position_stats(stats['position_specific'], footer, headers, position)
        return stats

    def init_position_stats(self, position):
        """Инициализация статистики по позиции"""
        if 'вратарь' in position.lower():
            return {'пропущенные_голы': 0, 'сухие_матчи': 0}
        return {'голы': 0, 'голевые_передачи': 0}

    def update_position_stats(self, stats, row, headers, position):
        """Обновление статистики по позиции"""
        if 'вратарь' in position.lower():
            stats['пропущенные_голы'] = self.parse_int(
                row.xpath(f'.//td[{headers.get("Пропущенные голы", -1)+1}]/text()').get())
            stats['сухие_матчи'] = self.parse_int(
                row.xpath(f'.//td[{headers.get("Матчи без пропущенных голов", -1)+1}]/text()').get())
        else:
            stats['голы'] = self.parse_int(
                row.xpath(f'.//td[{headers.get("Голы", -1)+1}]/text()').get())
            stats['голевые_передачи'] = self.parse_int(
                row.xpath(f'.//td[{headers.get("Голевые передачи", -1)+1}]/text()').get())

    def parse_minutes(self, value):
        """Парсинг минут (удаление апострофов)"""
        try:
            return int(value.replace("'", "").strip()) if value else 0
        except (ValueError, AttributeError):
            return 0

    def parse_int(self, value):
        """Преобразование в целое число"""
        try:
            return int(value.strip().replace('-', '0')) if value else 0
        except (ValueError, AttributeError):
            return 0


# 2222222222222222222222222
# import json
# import scrapy
# import random
# import stem.process
# from scrapy.exceptions import CloseSpider
# from fake_useragent import UserAgent
# from urllib.parse import urljoin
# from scrapy import Request

# class TransfermarktSpider(scrapy.Spider):
#     """Парсер статистики игроков с Transfermarkt с переключением на Tor при 503 ошибках"""
    
#     name = "transfermarkt_spider"
    
#     custom_settings = {
#         'FEEDS': {
#             'output2.json': {
#                 'format': 'json',
#                 'encoding': 'utf-8',
#                 'indent': 4,
#                 'overwrite': True
#             }
#         },
#         'ROBOTSTXT_OBEY': False,
#         'CONCURRENT_REQUESTS': 1,
#         'DOWNLOAD_DELAY': random.uniform(5, 15),
#         'DEFAULT_REQUEST_HEADERS': {
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Referer': 'https://www.transfermarkt.world/'
#         },
#         'USER_AGENT': UserAgent().random,
#         'RETRY_TIMES': 1,  # Только одна попытка перед переключением на Tor
#         'RETRY_HTTP_CODES': [503],
#         'DOWNLOADER_MIDDLEWARES': {
#             'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
#             'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
#         }
#     }

#     def __init__(self, *args, **kwargs):
#         super(TransfermarktSpider, self).__init__(*args, **kwargs)
#         self.ua = UserAgent()
#         self.tor_process = None
#         self.use_tor = False  # Флаг для отслеживания использования Tor
#         self.start_tor()

#     def start_tor(self):
#         """Запуск Tor процесса"""
#         try:
#             self.tor_process = stem.process.launch_tor_with_config(
#                 config={
#                     'SocksPort': '9050',
#                     'ControlPort': '9051',
#                 },
#                 take_ownership=True,
#             )
#             self.logger.info("Tor процесс успешно запущен")
#         except Exception as e:
#             self.logger.error(f"Ошибка запуска Tor: {str(e)}")
#             self.tor_process = None

#     def close_spider(self, spider):
#         """Остановка Tor процесса при завершении работы паука"""
#         if self.tor_process:
#             self.tor_process.terminate()
#             self.logger.info("Tor процесс остановлен")

#     def start_requests(self):
#         """Загрузка URL из JSON-файла"""
#         try:
#             with open('output.json', 'r', encoding='utf-8') as f:
#                 urls = json.load(f)
#                 for url in urls:
#                     yield Request(
#                         url=url,
#                         callback=self.parse,
#                         errback=self.errback_tor_fallback,
#                         headers={'User-Agent': self.ua.random},
#                         meta={
#                             'dont_redirect': True,
#                             'proxy': None,  # Первый запрос без прокси
#                             'retry_count': 0,
#                             'original_url': url
#                         }
#                     )
#         except FileNotFoundError:
#             self.logger.error("Файл output.json не найден")
#             raise CloseSpider('Файл с URL не найден')
#         except Exception as e:
#             self.logger.error(f"Ошибка загрузки URL: {str(e)}")
#             raise CloseSpider('Ошибка в стартовых URL')

#     def errback_tor_fallback(self, failure):
#         """Обработка ошибки 503 с переключением на Tor"""
#         request = failure.request
#         retry_count = request.meta.get('retry_count', 0)
        
#         if retry_count >= 1 and not self.use_tor and self.tor_process:
#             # Переключаемся на Tor
#             self.use_tor = True
#             self.logger.info("Переключаемся на Tor после ошибки 503")
            
#             new_request = request.copy()
#             new_request.meta['proxy'] = 'http://localhost:9050'  # Tor proxy
#             new_request.meta['retry_count'] = retry_count + 1
#             new_request.headers['User-Agent'] = self.ua.random
#             new_request.dont_filter = True
            
#             return new_request
#         else:
#             self.logger.error(f"Не удалось получить данные для {request.url} даже через Tor")
#             return

#     def parse(self, response):
#         """Обработка страницы игрока"""
#         if response.status != 200:
#             self.logger.error(f"Ошибка {response.status}: {response.url}")
#             return

#         try:
#             player_data = {
#                 'name': self.parse_player_name(response),
#                 'position': self.parse_player_position(response),
#                 'stats': self.parse_player_stats(response),
#                 'url': response.url,
#                 'via_tor': self.use_tor  # Добавляем информацию о способе доступа
#             }
#             yield player_data
            
#             # После успешного запроса через Tor, продолжаем использовать его
#             if self.use_tor:
#                 self.logger.info("Успешно получили данные через Tor, продолжаем использовать его")
#             else:
#                 self.use_tor = False  # Возвращаемся к обычному режиму

#         except Exception as e:
#             self.logger.error(f"Ошибка парсинга {response.url}: {str(e)}")

#     # Все остальные методы парсера остаются без изменений
#     def parse_player_name(self, response):
#         """Извлечение имени игрока"""
#         name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
#         return ' '.join([name.strip() for name in name_parts if name.strip()])

#     # ... остальные методы parse_player_position, parse_player_stats и т.д. ...

#     # Все остальные методы парсера остаются без изменений
#     def parse_player_name(self, response):
#         """Извлечение имени игрока"""
#         name_parts = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').getall()
#         return ' '.join([name.strip() for name in name_parts if name.strip()])

#     def parse_player_position(self, response):
#         """Извлечение позиции игрока"""
#         return response.xpath('//li[contains(., "Амплуа:")]/span[@class="data-header__content"]/text()').get(default='').strip()

#     def parse_player_stats(self, response):
#         """Сбор всей статистики игрока"""
#         position = self.parse_player_position(response)
#         table = response.xpath('//div[@class="box"][.//h2[contains(., "Статистика выступлений")]]//table')
        
#         if not table:
#             self.logger.warning(f"Не найдена таблица статистики для {response.url}")
#             return self.empty_stats(position)
        
#         headers = self.parse_table_headers(table)
#         seasons = [self.parse_season_row(row, headers, position) 
#                   for row in table.xpath('.//tbody/tr') if self.parse_season_row(row, headers, position)]
        
#         total_stats = self.parse_total_stats(table, position, headers)
#         total_stats['seasons'] = seasons
        
#         return total_stats

#     def empty_stats(self, position):
#         """Возвращает пустую статистику"""
#         return {
#             'matches': 0,
#             'minutes': 0,
#             'position_specific': self.init_position_stats(position),
#             'cards': {'yellow': 0, 'yellow_red': 0, 'red': 0},
#             'substitutions': {'in': 0, 'out': 0},
#             'own_goals': 0,
#             'seasons': []
#         }

#     def parse_table_headers(self, table):
#         """Парсинг заголовков таблицы"""
#         headers = {}
#         for i, header in enumerate(table.xpath('.//thead/tr/th')):
#             title = header.xpath('.//@title').get() or header.xpath('.//text()').get()
#             if title and title.strip():
#                 headers[title.strip()] = i
#         return headers

#     def parse_season_row(self, row, headers, position):
#         """Парсинг строки с данными сезона"""
#         tournament_name = row.xpath('.//td[2]//a/text()').get(default='').strip()
#         if not tournament_name:
#             return None
            
#         stats = {
#             'name': tournament_name,
#             'matches': self.parse_int(row.xpath(f'.//td[{headers.get("Матчи", 3)+1}]/text()').get()),
#             'minutes': self.parse_minutes(row.xpath(f'.//td[{headers.get("Сыграно минут", -1)+1}]/text()').get()),
#             'position_specific': self.init_position_stats(position),
#             'cards': {
#                 'yellow': self.parse_int(row.xpath(f'.//td[{headers.get("Желтые карточки", -1)+1}]/text()').get()),
#                 'yellow_red': self.parse_int(row.xpath(f'.//td[{headers.get("Желтые/красные карточки", -1)+1}]/text()').get()),
#                 'red': self.parse_int(row.xpath(f'.//td[{headers.get("Красные карточки", -1)+1}]/text()').get())
#             },
#             'substitutions': {
#                 'in': self.parse_int(row.xpath(f'.//td[{headers.get("Вышел на замену", -1)+1}]/text()').get()),
#                 'out': self.parse_int(row.xpath(f'.//td[{headers.get("Заменен", -1)+1}]/text()').get())
#             },
#             'own_goals': self.parse_int(row.xpath(f'.//td[{headers.get("автоголы", -1)+1}]/text()').get())
#         }
        
#         self.update_position_stats(stats['position_specific'], row, headers, position)
#         return stats

#     def parse_total_stats(self, table, position, headers):
#         """Парсинг итоговой статистики"""
#         footer = table.xpath('.//tfoot/tr')
        
#         stats = {
#             'matches': self.parse_int(footer.xpath(f'.//td[{headers.get("Матчи", 3)+1}]/text()').get()),
#             'minutes': self.parse_minutes(footer.xpath(f'.//td[{headers.get("Сыграно минут", -1)+1}]/text()').get()),
#             'position_specific': self.init_position_stats(position),
#             'cards': {
#                 'yellow': self.parse_int(footer.xpath(f'.//td[{headers.get("Желтые карточки", -1)+1}]/text()').get()),
#                 'yellow_red': self.parse_int(footer.xpath(f'.//td[{headers.get("Желтые/красные карточки", -1)+1}]/text()').get()),
#                 'red': self.parse_int(footer.xpath(f'.//td[{headers.get("Красные карточки", -1)+1}]/text()').get())
#             },
#             'substitutions': {
#                 'in': self.parse_int(footer.xpath(f'.//td[{headers.get("Вышел на замену", -1)+1}]/text()').get()),
#                 'out': self.parse_int(footer.xpath(f'.//td[{headers.get("Заменен", -1)+1}]/text()').get())
#             },
#             'own_goals': self.parse_int(footer.xpath(f'.//td[{headers.get("автоголы", -1)+1}]/text()').get())
#         }
        
#         self.update_position_stats(stats['position_specific'], footer, headers, position)
#         return stats

#     def init_position_stats(self, position):
#         """Инициализация статистики по позиции"""
#         if 'вратарь' in position.lower():
#             return {'пропущенные_голы': 0, 'сухие_матчи': 0}
#         return {'голы': 0, 'голевые_передачи': 0}

#     def update_position_stats(self, stats, row, headers, position):
#         """Обновление статистики по позиции"""
#         if 'вратарь' in position.lower():
#             stats['пропущенные_голы'] = self.parse_int(
#                 row.xpath(f'.//td[{headers.get("Пропущенные голы", -1)+1}]/text()').get())
#             stats['сухие_матчи'] = self.parse_int(
#                 row.xpath(f'.//td[{headers.get("Матчи без пропущенных голов", -1)+1}]/text()').get())
#         else:
#             stats['голы'] = self.parse_int(
#                 row.xpath(f'.//td[{headers.get("Голы", -1)+1}]/text()').get())
#             stats['голевые_передачи'] = self.parse_int(
#                 row.xpath(f'.//td[{headers.get("Голевые передачи", -1)+1}]/text()').get())

#     def parse_minutes(self, value):
#         """Парсинг минут (удаление апострофов)"""
#         try:
#             return int(value.replace("'", "").strip()) if value else 0
#         except (ValueError, AttributeError):
#             return 0

#     def parse_int(self, value):
#         """Преобразование в целое число"""
#         try:
#             return int(value.strip().replace('-', '0')) if value else 0
#         except (ValueError, AttributeError):
#             return 0
