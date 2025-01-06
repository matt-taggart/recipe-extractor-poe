# Recipe Extractor Poe bot

A Poe Server Bot written in Python that allows users to extract recipes from a given url and make modifications via a chat interface. Using this code as a baseline should help you develop and deploy a Poe bot with custom server logic on your own (i.e. anything that needs custom functionality such as web search, etc. that can't be done solely with prompt engineering). 

See the docs at [here](https://creator.poe.com/docs/quick-start) for more context on how to create and deploy your own bot. 

NOTE: One big gotcha that I ran into was that once your bot is live, you'll need to explicitly call the settings endpoint for your bot to update the AI model that you want to use (specified by the async `get_settings` method in the code).

## Getting Started

Clone the repo:

`git clone https://github.com/matt-taggart/recipe-extractor-poe.git`

Create virtual environment:

`python -m venv env`

Activate virtual environment:

`source env/bin/activate`

Install dependencies:

`pip install -r requirements.txt`

Run the server:

`POE_API_KEY=supersecretkey python main.py`

The bot server will now be started on [`localhost:8080`](http://localhost:8080). 

## Production Deployment

See the "Quick Start" section in the left-hand navigation menu under Server Bots. I ended up self hosting on Digital Ocean rather than using Modal as a service, but that's likely a good option as well. 

![image](https://github.com/user-attachments/assets/5c13383c-90c4-47ba-8f42-d96428123bf3)


## Built With
* Python
* FastAPI Poe
* beautifulsoup4



https://creator.poe.com/docs/quick-start
