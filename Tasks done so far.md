# Tasks Done So Far

This document summarizes the completed tasks in the Tech Pulse Dashboard project.

## Data Fetching and Organization
- Created `fetched_data/` directory for raw data.
- Modified `src/tech_pulse_fetcher.py` to:
  - Correctly fetch GitHub trending repository stars.
  - Save all raw data JSON files into the `fetched_data/` directory.

## Data Processing Pipeline
- Created `processed_data/` directory for processed data.
- Created `src/data_processor.py` to handle data transformations.
- Implemented `process_github_trending()` in `src/data_processor.py`:
  - Reads `fetched_data/github_trending_data.json`.
  - Calculates language distribution, total stars, and stars gained today.
  - Saves processed data to `processed_data/github_language_distribution.json`.
- Implemented `process_rss_feeds_for_wordcloud()` in `src/data_processor.py`:
  - Reads `fetched_data/rss_feeds_data.json`.
  - Aggregates text, performs word frequency counting and stop word removal.
  - Uses LLM to extract important keywords and hot topics.
  - Saves processed data to `processed_data/news_word_cloud.json`.
- Implemented `process_product_hunt_for_sankey()` in `src/data_processor.py`:
  - Reads `fetched_data/product_hunt_data.json`.
  - Uses LLM to map product topics to predefined core categories.
  - Generates Sankey diagram nodes and links based on co-occurrence.
  - Saves processed data to `processed_data/product_hunt_tag_connections.json`.
- Implemented `process_manifold_predictions_for_bubble_plot()` in `src/data_processor.py`:
  - Reads `fetched_data/predictions_data.json`.
  - Uses LLM to extract sentiment and categorize predictions.
  - Formats data for a 2D bubble plot.
  - Saves processed data to `processed_data/manifold_predictions_bubble_plot.json`.
- Enhanced processed data structures to include more details for richer, more interactive frontend visualizations.

## Data Visualization
- Created `visualize_charts.py` to generate charts from processed data for testing and validation.
- Implemented functions to create and save the following visualizations in the `visualizations/` directory:
  - **GitHub Language Distribution:** A pie chart showing the breakdown of programming languages in trending repositories.
  - **Top News Keywords:** A bar chart displaying the most important keywords from tech news.
  - **Product Hunt Category Connections:** A heatmap showing co-occurrence between product categories.
  - **Manifold Markets Predictions:** A scatter plot visualizing prediction probabilities against trading volumes.

## Environment Setup
- Ensured `OPENAI_API_KEY` is loaded from `.env` file using `python-dotenv`.
- Removed `.env` from Git history using `git filter-repo` and force pushed changes.