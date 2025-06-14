# scraper/transfermarkt_spider.py
import scrapy
from database import Database
import logging

class TransfermarktSpider(scrapy.Spider):
    name = "transfermarkt"
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 3,
        'LOG_LEVEL': 'ERROR'
    }

    def __init__(self, player_urls):
        self.player_urls = player_urls
        self.db = Database()  # Инициализация подключения к БД

    def start_requests(self):
        for url in self.player_urls:  # Просто итерация по списку URL
            if not url.startswith("http"):
                url = f"https://www.transfermarkt.com{url}"
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        player_id = response.meta['player_id']
        try:
            # Основная информация
            player_name = response.xpath('//h1[@class="data-header__headline-wrapper"]//text()').get().strip()

            # Статистика по турнирам
            tournaments = []
            for row in response.xpath('//table[@class="items"]/tbody/tr'):
                tournament_name = row.xpath('.//td[1]//text()').get()
                matches = row.xpath('.//td[3]/a/text()').get()
                goals = row.xpath('.//td[4]/text()').get()
                assists = row.xpath('.//td[5]/text()').get()

                tournament = {
                    'name': tournament_name.strip() if tournament_name else None,
                    'matches': int(matches) if matches else 0,
                    'goals': int(goals) if goals else 0,
                    'assists': int(assists) if assists else 0
                }
                tournaments.append(tournament)

            # Сохранение статистики в БД
            self.db.save_player_stats(player_id, {'tournaments': tournaments})
            yield {
                "player_id": player_id,
                "player_name": player_name,
                "status": "success"
            }

        except Exception as e:
            yield {
                "error": str(e),
                "url": response.url,
                "status": "failed"
            }

    def closed(self, reason):
        self.db.close()
