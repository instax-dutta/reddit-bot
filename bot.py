import requests
import base64
import os
import json
import time
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RedditStoryBot')

# Placeholder for Reddit and Mistral API Configuration
# These should be set using environment variables or a secure method
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USERNAME = os.getenv('REDDIT_USERNAME')
REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD')
USER_AGENT = "YourBotUserAgent"

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_AGENT_ID = os.getenv('MISTRAL_AGENT_ID')
MISTRAL_URL = "https://api.mistral.ai/v1/agents/completions"

PROFILE_LINK = f"https://www.reddit.com/user/{REDDIT_USERNAME}/"

def generate_token(client_id, client_secret, username, password):
    """Generates a Reddit API access token."""
    try:
        auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_string}",
            "User-Agent": USER_AGENT
        }
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "read,submit"
        }
        response = requests.post("https://www.reddit.com/api/v1/access_token", headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        logger.error(f"Token generation failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response: {e}")
        return None

def get_token(client_id, client_secret, username, password):
    """Gets the access token, either from a file or by generating a new one."""
    token_file = "token.txt"
    if os.path.exists(token_file):
        try:
            with open(token_file, "r") as f:
                token = f.read().strip()
                if token:
                    return token
        except Exception as e:
            logger.error(f"Error reading token from file: {e}")

    # Generate a new token
    token = generate_token(client_id, client_secret, username, password)
    if token:
        try:
            with open(token_file, "w") as f:
                f.write(token)
            logger.info("New token generated and saved to token.txt")
            return token
        except Exception as e:
            logger.error(f"Error writing token to file: {e}")
    return None

def clean_text(text):
    """Removes unwanted characters, markdown syntax, and prefixes from the text."""
    # Remove markdown bold/italic symbols
    text = re.sub(r'[*_~]', '', text)
    # Remove any other unwanted characters or patterns
    text = re.sub(r'[\[\]\(\)#]', '', text)  # Remove brackets and hashtags
    # Remove common prefixes like "Title:", "Story:", and "### "
    text = re.sub(r'^[Tt]itle[:\s]*', '', text)
    text = re.sub(r'^[Ss]tory[:\s]*', '', text)
    text = re.sub(r'^###\s*', '', text)
    text = text.strip()  # Remove leading/trailing whitespace
    return text

def generate_story_with_mistral(api_key, agent_id):
    """Generates a horror story and title using the Mistral AI agent."""
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": "Generate a short horror story with a title."
                }
            ],
            "max_tokens": 500,
            "agent_id": agent_id
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(MISTRAL_URL, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            story_content = data['choices'][0]['message']['content']
            # Assuming the title is the first line of the content
            lines = story_content.split('\n', 1)
            title = clean_text(lines[0].strip())
            story = clean_text(lines[1].strip()) if len(lines) > 1 else ""
            return title, story
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None, None

def post_story_line_to_reddit(client_id, client_secret, username, password, api_key, agent_id):
    profile_name = f"u_{username}"

    # Get the access token
    access_token = get_token(client_id, client_secret, username, password)

    if not access_token:
        logger.error("Failed to get access token. Please check your credentials and try again.")
        return

    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    while True:
        # Generate a new horror story and title using Mistral AI
        title, story_line = generate_story_with_mistral(api_key, agent_id)
        if not story_line or not title:
            logger.error("Failed to generate a story. Retrying in 1 hour.")
            time.sleep(3600)
            continue

        # Ensure the story does not start with "Story:"
        story_line = re.sub(r'^[Ss]tory[:\s]*', '', story_line).strip()

        post_text = f"{story_line}\n\nLiked the story? Stay tuned and follow {PROFILE_LINK}"

        logger.info(f"Posting story line to Reddit profile ({profile_name}): {title}")

        # Submit the text post to your Reddit profile
        post_data = {
            'sr': profile_name,
            'title': title,
            'kind': 'self',
            'text': post_text
        }
        response = make_request("https://oauth.reddit.com/api/submit", headers=headers, data=post_data)

        if response:
            logger.info(f"Reddit response: {response.text}")
        else:
            logger.error("Failed to post to Reddit.")

        # Wait for 1 hour before posting the next story
        time.sleep(3600)

def make_request(url, headers, data):
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

# Example usage:
# post_story_line_to_reddit(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, MISTRAL_API_KEY, MISTRAL_AGENT_ID)
