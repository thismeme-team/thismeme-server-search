import os
from dotenv import load_dotenv, find_dotenv
import openai


load_dotenv(find_dotenv("secrets/.env"))

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_openai_categorizing(categories, tag):
    PROMPT = """
    You are a helpful tagging and categorizing assistant. 
    We had {categories} categories. 
    Please recommend me which category the tag for {tag} belongs to. 
    Don't add anything else, just say the word that corresponds to the category name.
    """

    PROMPT = PROMPT.format(categories=categories, tag=tag)

    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    temperature=0.0,
    messages=[
            {"role": "system", "content": PROMPT},
        ]
    )

    response = completion.choices[0].message.content
    return response

