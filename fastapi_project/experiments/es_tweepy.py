import tweepy
import time
from konlpy.tag import Okt
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv
import os


load_dotenv()


class JJMemeTweepy:
    def __init__(self, target_screen_name) -> None:
        self.target_screen_name = target_screen_name
        self.consumer_key = os.environ.get("CONSUMER_KEY")
        self.consumer_secret = os.environ.get("CONSUMER_SECRET")
        self.access_token = os.environ.get("ACCESS_TOKEN")
        self.access_token_secret = os.environ.get("ACCESS_TOKEN_SECRET")
        self.bearer_token = os.environ.get("BEARER_TOKEN")

    def connect_api(self):
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(auth)
        return api

    def get_tweets(self, api):
        tweets = api.user_timeline(screen_name=self.target_screen_name)
        return tweets

    def get_client(self):
        client = tweepy.Client(bearer_token=self.bearer_token)
        return client

    def get_id(self, screen_name):
        client = self.get_client()
        while True:
            try:
                t_id = client.get_user(username=screen_name).data.id
                break
            except:
                time.sleep(60 * 15)
        return t_id


if __name__ == "__main__":
    okt = Okt()
    print(okt.pos("자연스ㄷ 무한ㄷ"))
    # jj_meme = JJMemeTweepy("짤주워오는계정")
    # client = jj_meme.get_client()
    # t_id = jj_meme.get_id(screen_name='WkfxjfrP')

    # tweets = client.get_users_tweets(
    #     t_id,
    #     expansions='attachments.media_keys',
    #     media_fields=['duration_ms', 'height','media_key', 'preview_image_url', 'type', 'url', 'width', 'alt_text'],
    #     max_results = 100
    # )

    # medias = {}
    # for m in tweets.includes['media']:
    #     medias[m['media_key']] = m['url']

    # okt = Okt()
    # for tweet in tweets.data:
    #     _id = tweet.id
    #     text = tweet.text
    #     media_keys = tweet.attachments['media_keys'] if tweet.attachments else None
    #     if not media_keys:
    #         continue

    #     image_urls = list(map(lambda x: medias[x], media_keys))
    #     print(f"id = {_id}, text = {text}, okt_pos = {okt.pos(text, norm=True, stem=True, join=True)}, image_urls = {image_urls}")

    #     tags = okt.nouns(text)
    #     for image_url in image_urls:
    #         doc = {
    #             "id": _id,
    #             "description": text,
    #             "title": text,
    #             "tags": tags,
    #             "image_url": image_url
    #         }
    #         es.index(index=_index, doc_type="_doc", body=doc)
