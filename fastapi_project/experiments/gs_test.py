from serpapi import GoogleSearch
from pprint import pprint

params = {
    "q": "총든페페",
    "tbm": "isch",
    "ijn": "0",
    "api_key": "6f0ffe6bb042ec7cd3d76fec0efe700789ebcdf0e42c9cc7ae9446dc9b094bed",
}

search = GoogleSearch(params)
results = search.get_dict()
images_results = results["images_results"]
pprint(images_results)

suggested_searches = results["suggested_searches"]
pprint(suggested_searches)

for suggested_searche in suggested_searches:
    print(suggested_searche["name"])
