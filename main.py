import logging
import json
import os
from src.tech_pulse_fetcher import TechPulseFetcher
from src.data_processor import DataProcessor
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def save_data_to_supabase(data: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.error("Supabase URL or Key not found in environment variables. Cannot save data.")
        return

    try:
        logging.info("Connecting to Supabase...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Connection to Supabase successful.")

        table_name = 'tech_pulses'
        logging.info(f"Inserting data into '{table_name}' table...")
        
        # We pass the JSON data as a string. Postgres will handle the conversion to JSONB.
        response = supabase.table(table_name).insert({"pulse_data": json.dumps(data)}).execute()
        
        logging.info("Data successfully saved to the database.")

    except Exception as e:
        logging.error(f"Error saving data to Supabase: {e}")
        raise

def main():
    logging.info("Starting the Tech Pulse workflow...")

    # Initialize Fetcher and Processor
    fetcher = TechPulseFetcher()
    processor = DataProcessor()

    # Fetch data
    fetched_data = fetcher.fetch_all()

    # Process data
    processed_data = {}
    if fetched_data.get('github_trending'):
        processed_data['github_language_distribution'] = processor.process_github_trending(fetched_data['github_trending'])
    if fetched_data.get('rss_articles'):
        processed_data['news_word_cloud'] = processor.process_rss_feeds_for_wordcloud(fetched_data['rss_articles'])
    if fetched_data.get('product_hunt'):
        processed_data['product_hunt_tag_connections'] = processor.process_product_hunt_for_sankey(fetched_data['product_hunt'])
    if fetched_data.get('predictions'):
        processed_data['manifold_predictions_bubble_plot'] = processor.process_manifold_predictions_for_bubble_plot(fetched_data['predictions'])

    # Save processed data to a local JSON file
    if processed_data:
        # Ensure the directory exists
        os.makedirs("processed_data", exist_ok=True)
        
        # Generate a unique filename with a timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"processed_data/tech_pulse_processed_{timestamp}.json"
        
        with open(file_path, 'w') as f:
            json.dump(processed_data, f, indent=4)
        logging.info(f"Processed data saved to {file_path}")

    # Save processed data to Supabase
    if processed_data:
        save_data_to_supabase(processed_data)
    
    logging.info("Workflow complete.")

if __name__ == "__main__":
    main()
