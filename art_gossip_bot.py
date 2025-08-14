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

FIREBASE_URL = 'https://art-gossip-cache-default-rtdb.firebaseio.com/artworks'
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

# Function to get a random cached artwork ID and data from Firebase
def get_random_cached_artwork():
    # Fetch all cached artworks
    fb_resp = requests.get(f'{FIREBASE_URL}.json')
    all_cached = fb_resp.json()
    
    if not all_cached:
        raise ValueError("No cached artworks found in Firebase.")
    
    # Pick random ID
    rand_id = random.choice(list(all_cached.keys()))
    cached_data = all_cached[rand_id]
    
    return rand_id, cached_data

# Main bot logic
def post_to_instagram():
    rand_id, cached_data = get_random_cached_artwork()
    
    # Fetch Met data for image and basics
    met_resp = requests.get(f'https://collectionapi.metmuseum.org/public/collection/v1/objects/{rand_id}')
    met_data = met_resp.json()
    
    if not met_data.get('primaryImage'):
        print(f"No image for ID {rand_id}, skipping.")
        return  # Or retry with another random
    
    title = met_data.get('title', 'Untitled')
    artist = met_data.get('artistDisplayName', 'Unknown Artist')
    medium = met_data.get('medium', 'N/A')
    image_url = met_data['primaryImage']
    
    # Use cached data
    short_desc = cached_data['shortDesc']
    price_estimate = cached_data['rawSingle']
    
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