from __future__ import annotations

import os

from typing import AsyncIterable, Optional
import fastapi_poe as fp
import requests
from bs4 import BeautifulSoup
import re

from dotenv import load_dotenv
load_dotenv() 


def is_valid_url(url: str) -> bool:
    # Regular expression to validate URLs
    regex = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})'  # domain
        r'(:[0-9]{1,5})?'  # optional port
        r'(/.*)?$'  # path
    )
    return re.match(regex, url) is not None

def fetch_and_extract_text_from_url(url: str) -> str:
    if not is_valid_url(url):
        return ""
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator="\n")
        return text.strip()
    except requests.RequestException as e:
        return f"Error fetching the URL: {e}"
    except Exception as e:
        return f"Error parsing the content: {e}"

def process_recipe_request(parsedText):
    return f"""
    ## Context: You are Recipe Extractor bot, a helpful AI assistant that helps users extract recipe details from a given URL. Can you please extract the recipe from the following text and display it in a clean, organized Markdown format? \n {parsedText}. Don't use a preamble when returning results.

    ### Instructions

    The recipe name, ingredients, instructions, and modifications should be returned as Markdown separated into three sections (four if returning a modification):

    1. Recipe name
    2. Ingredients
    3. Instructions
    4. Modifications (If applicable) 

    Here is an example of how it should be formatted:

    ### Chicken Alfredo

    ### Ingredients
    * 4oz of chicken breast
    * 1 can of alfredo sauce
    * 1 stick of butter
    * 1 sprig of parsley

    ### Instructions
    1. Cook the chicken
    2. Add the sauce
    3. Add the butter
    4. Add the parsley

    If the user requests modifications to the recipe, explain why recipe was modified separately from instructions. If the user's query doesn't make sense, the content isn't recipe-related, or the url isn't valid, tell the user: 'This URL doesn't look like it's valid. Can you please try again?'
    """

def process_modification_request(modification_text, last_recipe_text):
    return f"""
    ## Context: You are Recipe Extractor bot, a helpful AI assistant that helps users modify recipes. Based on the following recipe, can you please apply the requested modification and display it in a clean, organized Markdown format? \n Recipe: {last_recipe_text} \n Modification: {modification_text}.

    ### Instructions

    The recipe name, ingredients, instructions, and modifications should be returned as Markdown separated into three sections (four if returning a modification):

    1. Recipe name
    2. Ingredients
    3. Instructions
    4. Modifications (If applicable) 
    """

class RecipeExtractorBot(fp.PoeBot):
    def __init__(self):
        self.initial_message = """
        Hi there! I'm Recipe Extractor bot. I can help you extract recipe details from a given URL.
        Just send me a URL and I'll do my best to provide a clean, organized Markdown format of the recipe.
        """
        self.last_url: Optional[str] = None
        self.last_recipe_text: Optional[str] = None

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_input = request.text.strip()

        # Check if the input contains a URL
        url_match = re.search(r'(https?://[^\s]+)', user_input)
        if url_match:
            url = url_match.group(0)
            self.last_url = url
            extracted_text = fetch_and_extract_text_from_url(url)
            if not extracted_text:
                yield fp.PartialResponse(model_copy={"text": "This URL doesn't look like it's valid. Can you please try again?"})
                return
            response_text = process_recipe_request(extracted_text)
            self.last_recipe_text = extracted_text
            yield fp.PartialResponse(model_copy={"text": response_text})
        else:
            if self.last_recipe_text:
                # If there's a previously stored recipe, assume this is a modification request
                response_text = process_modification_request(user_input, self.last_recipe_text)
                yield fp.PartialResponse(model_copy={"text": response_text})
            else:
                # If no URL has been provided yet and no last recipe is stored, prompt the user to enter a URL
                yield fp.PartialResponse(model_copy={"text": "Please provide a URL to extract a recipe from."})

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"GPT-4o": 1},
            enable_multi_bot_chat_prompting=True,
            allow_attachments=True,
            enable_image_comprehension=True,
            enforce_author_role_alternation=True  # Optional, based on your needs
        )


if __name__ == "__main__":
    fp.run(RecipeExtractorBot(), access_key=os.environ["POE_API_KEY"])

