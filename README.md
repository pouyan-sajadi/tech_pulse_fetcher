# Tech Pulse Dashboard

An intelligent daily dashboard that transforms raw tech data into actionable insights through AI-powered analysis and beautiful visualizations.

## 🚀 Overview

Tech Pulse Dashboard aggregates data from multiple sources to provide a comprehensive view of the technology ecosystem:

- **GitHub Trending**: What developers are building
- **Product Hunt**: What's launching and gaining traction
- **Tech News**: What's making headlines
- **Prediction Markets**: Where the industry is heading

Instead of checking multiple sources daily, get everything in one intelligent, visual dashboard that connects the dots across the tech landscape.

## ✨ Features

- **Automated Daily Updates**: Fresh data every morning via GitHub Actions.
- **AI-Powered Analysis**: LLMs extract insights, not just data.
- **Centralized Data Storage**: Processed data is stored in a Supabase PostgreSQL database.
- **Interactive Visualizations**:
  - Programming language trends (GitHub)
  - Product category flows (Product Hunt)
  - News word clouds and hot topics
  - Prediction market sentiment analysis
- **Cross-Source Intelligence**: See connections between what's being built and what's launching.
- **Zero Maintenance**: Fully automated pipeline.

## 🛠️ Tech Stack

- **Backend**: Python
- **Data Fetching**: `TechPulseFetcher` class
- **Data Processing**: `DataProcessor` class
- **Database**: Supabase (PostgreSQL)
- **AI/ML**: OpenAI GPT-4 for analysis
- **Workflow Orchestration**: `main.py`
- **Automation**: GitHub Actions

## 📋 Prerequisites

- Python 3.9+
- Supabase Project
- OpenAI API key
- Product Hunt API token (optional, falls back to RSS)

## 🔧 Installation & Usage

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pouyan-sajadi/tech_pulse_fetcher.git
    cd tech-pulse-fetcher
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your API keys and Supabase credentials:
    ```
    OPENAI_API_KEY="your_openai_api_key"
    PRODUCT_HUNT_TOKEN="your_product_hunt_token" # Optional
    SUPABASE_URL="your_supabase_url"
    SUPABASE_KEY="your_supabase_key"
    ```

### Running the Workflow Manually

To run the entire data fetching and processing pipeline manually, execute the `main.py` script:

```bash
python main.py
```

This will:
1. Fetch data from all sources.
2. Process the data using the `DataProcessor` class.
3. Save the final, processed data to your Supabase database.

### Automated Workflow

This project uses a GitHub Actions workflow defined in `.github/workflows/daily-pulse.yml` to run the `main.py` script automatically every day at 1 AM UTC.

For the automated workflow to function, you must configure the following secrets in your GitHub repository's settings (**Settings > Secrets and variables > Actions**):

- `OPENAI_API_KEY`
- `PRODUCT_HUNT_TOKEN` (optional)
- `SUPABASE_URL`
- `SUPABASE_KEY`

## Project Structure

- `main.py`: The main entry point for the data processing workflow.
- `src/tech_pulse_fetcher.py`: Contains the `TechPulseFetcher` class for fetching data from various sources.
- `src/data_processor.py`: Contains the `DataProcessor` class for processing the fetched data.
- `.github/workflows/daily-pulse.yml`: The GitHub Actions workflow for daily execution.
- `requirements.txt`: A list of the Python dependencies for the project.
- `logs/`: Contains log files for debugging.
