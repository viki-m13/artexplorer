import random
import requests
import os
import logging
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# Set up logging (for debugging in Colab or Actions)
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# Credentials (use env vars in production/GitHub secrets)
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
SESSION_FILE = 'session.json'

# Function to handle login with session
def login_user():
    cl = Client()
    login_via_session = False
    login_via_pw = False
    if os.path.exists(SESSION_FILE):
        logger.info("Session file found—trying to load it.")
        try:
            session = cl.load_settings(SESSION_FILE)
            cl.set_settings(session)
            cl.login(IG_USERNAME, IG_PASSWORD)
            # Check if session is valid
            try:
                cl.get_timeline_feed()
                login_via_session = True
                logger.info("Logged in via session successfully.")
            except LoginRequired:
                logger.info("Session invalid, falling back to password login.")
                old_session = cl.get_settings()
                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])
                cl.login(IG_USERNAME, IG_PASSWORD)
                logger.info("Fallback login successful—saving new session.")
                cl.dump_settings(SESSION_FILE)
                login_via_pw = True
        except Exception as e:
            logger.error(f"Error loading session: {e}")
    if not login_via_session:
        try:
            logger.info(f"Logging in with username: {IG_USERNAME}")
            if cl.login(IG_USERNAME, IG_PASSWORD):
                login_via_pw = True
                logger.info("Password login successful—saving session.")
                cl.dump_settings(SESSION_FILE)
        except Exception as e:
            logger.error(f"Error during password login: {e}")
    # Force save session at the end if login succeeded
    if login_via_pw or login_via_session:
        try:
            logger.info("Forcing session save at the end.")
            cl.dump_settings(SESSION_FILE)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    if not login_via_pw and not login_via_session:
        raise Exception("Login failed.")
    return cl

# Function to call DeepSeek API
def call_deepseek_api(prompt):
    if not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API key not set.")
    url = 'https://api.deepseek.com/chat/completions'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
    }
    data = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant specializing in art history and valuation.'},
            {'role': 'user', 'content': prompt}
        ],
        'stream': False
    }
    try:
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        return result['choices'][0]['message']['content'].strip() or 'No information available.'
    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        raise Exception("Error generating content.")

# Function to convert data to details string
def data_to_details(data):
    return (
        f"Title: {data.get('title', 'Untitled')}\n"
        f"Artist: {data.get('artistDisplayName', 'Unknown Artist')}\n"
        f"Date: {data.get('objectDate', 'Unknown')}\n"
        f"Medium: {data.get('medium', 'Unknown')}\n"
        f"Culture: {data.get('culture', 'Unknown')}\n"
        f"Classification: {data.get('classification', 'Unknown')}\n"
        f"Dimensions: {data.get('dimensions', 'Unknown')}\n"
        f"Period: {data.get('period', 'Unknown')}\n"
        f"Dynasty: {data.get('dynasty', 'Unknown')}\n"
        f"Reign: {data.get('reign', 'Unknown')}\n"
        f"Portfolio: {data.get('portfolio', 'Unknown')}\n"
        f"Constituent ID: {data.get('constituentID', 'Unknown')}\n"
        f"Artist Role: {data.get('artistRole', 'Unknown')}\n"
        f"Artist Prefix: {data.get('artistPrefix', 'Unknown')}\n"
        f"Artist Display Bio: {data.get('artistDisplayBio', 'Unknown')}\n"
        f"Artist Suffix: {data.get('artistSuffix', 'Unknown')}\n"
        f"Artist Alpha Sort: {data.get('artistAlphaSort', 'Unknown')}\n"
        f"Artist Nationality: {data.get('artistNationality', 'Unknown')}\n"
        f"Artist Begin Date: {data.get('artistBeginDate', 'Unknown')}\n"
        f"Artist End Date: {data.get('artistEndDate', 'Unknown')}\n"
        f"Artist Gender: {data.get('artistGender', 'Unknown')}\n"
        f"Artist Wikidata URL: {data.get('artistWikidataURL', 'Unknown')}\n"
        f"Artist ULAN URL: {data.get('artistULANURL', 'Unknown')}\n"
        f"Object Name: {data.get('objectName', 'Unknown')}\n"
        f"Object Begin Date: {data.get('objectBeginDate', 'Unknown')}\n"
        f"Object End Date: {data.get('objectEndDate', 'Unknown')}\n"
        f"Credit Line: {data.get('creditLine', 'Unknown')}\n"
        f"Geography Type: {data.get('geographyType', 'Unknown')}\n"
        f"City: {data.get('city', 'Unknown')}\n"
        f"State: {data.get('state', 'Unknown')}\n"
        f"County: {data.get('county', 'Unknown')}\n"
        f"Country: {data.get('country', 'Unknown')}\n"
        f"Region: {data.get('region', 'Unknown')}\n"
        f"Subregion: {data.get('subregion', 'Unknown')}\n"
        f"Locale: {data.get('locale', 'Unknown')}\n"
        f"Locus: {data.get('locus', 'Unknown')}\n"
        f"Excavation: {data.get('excavation', 'Unknown')}\n"
        f"River: {data.get('river', 'Unknown')}\n"
        f"Rights and Reproduction: {data.get('rightsAndReproduction', 'Unknown')}\n"
        f"Link Resource: {data.get('linkResource', 'Unknown')}\n"
        f"Object Wikidata URL: {data.get('objectWikidataURL', 'Unknown')}\n"
        f"Metadata Date: {data.get('metadataDate', 'Unknown')}\n"
        f"Repository: {data.get('repository', 'Unknown')}\n"
        f"Tags: {', '.join([tag['term'] for tag in data.get('tags', [])]) if data.get('tags') else 'None'}"
    ).strip()

# Function to generate short description with AI
def generate_short_description_with_ai(data):
    details = data_to_details(data)
    prompt = (
        f"Based on the following metadata about an artwork, write a conversational, interesting, and story-like short paragraph (2-4 sentences) that is easy to read. "
        f"Make it professional and polite, incorporating interesting facts and highlighting aspects like history, creation, or trivia. "
        f"Strictly keep the entire paragraph under 400 characters. Do not mention that it is part of The Met’s collection. "
        f"Do not include any character count, length note, or meta information. Do not use any special formatting like bold, italics, asterisks, or phrases that reference this prompt. "
        f"Use plain text only, but emojis are allowed if appropriate:\n\n{details}"
    )
    return call_deepseek_api(prompt)

# Function to get estimated range with AI
def get_estimated_range_with_ai(data):
    details = data_to_details(data)
    prompt = (
        f"Based on the following metadata about an artwork, output ONLY the estimated market value range (e.g., $10,000 - $50,000). "
        f"Use the details to identify the artwork accurately and base your estimate on known sales of similar works, artist reputation, rarity, condition, and market trends. "
        f"You must provide a range, even if approximate; if very little is known, give a broad range based on comparable items. "
        f"Do not include any explanation or additional text:\n\n{details}"
    )
    return call_deepseek_api(prompt)

# Function to get single price with AI
def get_single_price_with_ai(data, range_estimate):
    details = data_to_details(data)
    prompt = (
        f"Given the estimated value range of {range_estimate} for the artwork with the following metadata, "
        f"output ONLY a single estimated market value that is strictly within this range (e.g., if range is $10,000 - $50,000, something like $25,000). "
        f"Choose a reasonable point based on factors like artist reputation, rarity, etc., not necessarily the exact midpoint. "
        f"Do not include any explanation or additional text:\n\n{details}"
    )
    return call_deepseek_api(prompt)

# Function to fetch all object IDs from Met API
def fetch_object_ids():
    resp = requests.get('https://collectionapi.metmuseum.org/public/collection/v1/objects')
    data = resp.json()
    if 'objectIDs' not in data:
        raise ValueError("No object IDs found.")
    return data['objectIDs']

# Main bot logic
def post_to_instagram():
    object_ids = fetch_object_ids()
    
    while True:
        rand_id = random.choice(object_ids)
        met_resp = requests.get(f'https://collectionapi.metmuseum.org/public/collection/v1/objects/{rand_id}')
        met_data = met_resp.json()
        if met_data.get('primaryImage'):
            break
        else:
            print(f"No image for ID {rand_id}, skipping.")
    
    title = met_data.get('title', 'Untitled')
    artist = met_data.get('artistDisplayName', 'Unknown Artist')
    image_url = met_data['primaryImage']
    
    # Generate data using DeepSeek
    short_desc = generate_short_description_with_ai(met_data)
    range_estimate = get_estimated_range_with_ai(met_data)
    price_estimate = get_single_price_with_ai(met_data, range_estimate)
    
    # Catchy caption with extra spacing and full URL
    caption = (
        f"if we really had to price it: {price_estimate} 💰\n\n"
        f"🎨 {title} by {artist}\n\n"
        f"fun fact: {short_desc}\n\n"
        f"dive deeper into art history and more price estimates:\n"
        f"👉 https://art-gossip.com\n\n"
        "#ArtGossip #ArtHistory #MetMuseum #ArtTrivia"
    )
    # Download image
    img_path = 'temp_art.jpg'
    img_data = requests.get(image_url).content
    with open(img_path, 'wb') as f:
        f.write(img_data)
    
    # Post to Instagram using the session-handled client
    cl = login_user()
    cl.photo_upload(img_path, caption=caption)
    
    # Cleanup
    os.remove(img_path)
    
    print(f"Posted: {title} by {artist} (ID: {rand_id})")

# Run the bot
if __name__ == '__main__':
    post_to_instagram()
