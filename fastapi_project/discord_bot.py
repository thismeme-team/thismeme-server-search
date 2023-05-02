import os
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import ButtonStyle
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import urllib.request

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

load_dotenv(dotenv_path="./secrets/.env")

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
print(DISCORD_TOKEN)

AWS_ACCESS_KEY = os.environ.get("AWS_ES_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_ES_SECRET_KEY")
AWS_REGION = os.environ.get("AWS_ES_REGION")
AWS_SERVICE = os.environ.get("AWS_ES_SERVICE")

HOST = os.environ.get("ES_HOST")

awsauth = AWS4Auth(
    AWS_ACCESS_KEY,
    AWS_SECRET_KEY,
    AWS_REGION,
    AWS_SERVICE,
)

es = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=30,
    max_retries=10,
    retry_on_timeout=True,
)

def get_search_sholud_query(keyword):
    should_query = [{"match": {"name": {"query": keyword, "operator": "and", "boost": 3}}},
                    {"match": {"tags": {"query": keyword, "operator": "and", "boost": 3}}},
                    {"match": {"name": {"query": keyword, "operator": "or"}}},
                    {"match": {"tags": {"query": keyword, "operator": "or"}}},
                    {"match_phrase": {"name.ngram": keyword}},
                    {"match_phrase": {"tags.ngram": keyword}},
                    {
                        "bool": {
                            "should": [
                                {"match": {"translator": "Constance Garnett"}},
                                {"match": {"translator": "Louise Maude"}},
                            ]
                        }
                    }]

    return should_query

@bot.event
async def on_ready():
    print('Bot: {}'.format(bot.user))

class MyButton(discord.ui.Button):
    def __init__(self, image_url, **kwargs):
        with urllib.request.urlopen(image_url) as url:
            image_data = url.read()
        image = discord.File(image_data, filename="./tagged_mudo/(노홍철,짜증)#짜증난 노홍철.jpg")
        super().__init__(**kwargs, emoji=None, style=discord.ButtonStyle.secondary, label='', custom_id='my_button')
        self.set_image(image)

@bot.command(aliases=['그밈', '그 밈', '밈'])
async def search(ctx, *keyword):
    full_keyword = " ".join(keyword)
    print(full_keyword)

    _index = "meme"  # index name

    doc = {
        "query": {
            "bool": {
                "should": get_search_sholud_query(full_keyword),
                "minimum_should_match": 1,
                "filter": {
                    "exists" : {"field" : "images"}
                }
            }
        },
        "from": 0,
        "size": 10,
        "sort": [{"_score": "desc"}],
    }

    res = es.search(index=_index, body=doc)
    datas = res["hits"]["hits"]
    # print(datas)

    view = View()
    for data in datas:
        button = Button(label=data['_source']['name'])
        async def make_callback(data):
            async def _callback(interaction):
                await interaction.response.send_message(f"https://app.thismeme.me/memes/{data['_id']}")
            return _callback
        _callback = await make_callback(data)
        button.callback = _callback
        view.add_item(button)

    await ctx.send(embed=discord.Embed(title="밈 선택하기"), view=view)


bot.run(DISCORD_TOKEN)
