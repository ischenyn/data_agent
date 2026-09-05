import asyncio
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    def __init__(self, es_config: ESConfig):
        self.es_config = es_config
        self.client: Optional[AsyncElasticsearch] = None

    def _get_url(self):
        return f"http://{self.es_config.host}:{self.es_config.port}"

    def init(self):
        self.client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self):
        if self.client:
            await self.client.close()


es_client_manager = ESClientManager(app_config.es)

if __name__ == '__main__':
    es_client_manager.init()


    async def test():
        client = es_client_manager.client

        index_name = "cooking_blog"
        mappings = {
            "title": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "description": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "author": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "date": {
                "type": "date",
                "format": "yyyy-MM-dd"
            },
            "category": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "tags": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "rating": {
                "type": "float"
            }
        }

        await client.indices.create(
            index=index_name,
            mappings={
                "properties": mappings
            }
        )

        resp = await client.bulk(
            index="cooking_blog",
            refresh="wait_for",
            operations=[
                {
                    "index": {
                        "_id": "1"
                    }
                },
                {
                    "title": "Perfect Pancakes: A Fluffy Breakfast Delight",
                    "description": "Learn the secrets to making the fluffiest pancakes, so amazing you won't believe your tastebuds. This recipe uses buttermilk and a special folding technique to create light, airy pancakes that are perfect for lazy Sunday mornings.",
                    "author": "Maria Rodriguez",
                    "date": "2023-05-01",
                    "category": "Breakfast",
                    "tags": [
                        "pancakes",
                        "breakfast",
                        "easy recipes"
                    ],
                    "rating": 4.8
                },
                {
                    "index": {
                        "_id": "2"
                    }
                },
                {
                    "title": "Spicy Thai Green Curry: A Vegetarian Adventure",
                    "description": "Dive into the flavors of Thailand with this vibrant green curry. Packed with vegetables and aromatic herbs, this dish is both healthy and satisfying. Don't worry about the heat - you can easily adjust the spice level to your liking.",
                    "author": "Liam Chen",
                    "date": "2023-05-05",
                    "category": "Main Course",
                    "tags": [
                        "thai",
                        "vegetarian",
                        "curry",
                        "spicy"
                    ],
                    "rating": 4.6
                },
                {
                    "index": {
                        "_id": "3"
                    }
                },
                {
                    "title": "Classic Beef Stroganoff: A Creamy Comfort Food",
                    "description": "Indulge in this rich and creamy beef stroganoff. Tender strips of beef in a savory mushroom sauce, served over a bed of egg noodles. It's the ultimate comfort food for chilly evenings.",
                    "author": "Emma Watson",
                    "date": "2023-05-10",
                    "category": "Main Course",
                    "tags": [
                        "beef",
                        "pasta",
                        "comfort food"
                    ],
                    "rating": 4.7
                },
                {
                    "index": {
                        "_id": "4"
                    }
                },
                {
                    "title": "Vegan Chocolate Avocado Mousse",
                    "description": "Discover the magic of avocado in this rich, vegan chocolate mousse. Creamy, indulgent, and secretly healthy, it's the perfect guilt-free dessert for chocolate lovers.",
                    "author": "Alex Green",
                    "date": "2023-05-15",
                    "category": "Dessert",
                    "tags": [
                        "vegan",
                        "chocolate",
                        "avocado",
                        "healthy dessert"
                    ],
                    "rating": 4.5
                },
                {
                    "index": {
                        "_id": "5"
                    }
                },
                {
                    "title": "Crispy Oven-Fried Chicken",
                    "description": "Get that perfect crunch without the deep fryer! This oven-fried chicken recipe delivers crispy, juicy results every time. A healthier take on the classic comfort food.",
                    "author": "Maria Rodriguez",
                    "date": "2023-05-20",
                    "category": "Main Course",
                    "tags": [
                        "chicken",
                        "oven-fried",
                        "healthy"
                    ],
                    "rating": 4.9
                }
            ],
        )
        print(resp)

        resp = await client.search(
            index="cooking_blog",
            query={
                "match": {
                    "description": {
                        "query": "fluffy pancakes"
                    }
                }
            },
        )
        print(resp)

        await es_client_manager.close()

    asyncio.run(test())