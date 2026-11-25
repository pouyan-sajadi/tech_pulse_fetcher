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
- **Daily Market Deep Dive**: One selected news story with cited business analysis and a longer-term outlook.
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
- **AI/ML**: OpenAI-compatible LLM gateway (CheaperInference) for analysis
- **Workflow Orchestration**: `main.py`
- **Automation**: GitHub Actions

## 📋 Prerequisites

- Python 3.12, matching the daily workflow
- Supabase Project
- CheaperInference API key and model
- Product Hunt API token (optional, falls back to RSS)

## 🔧 Installation & Usage

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pouyan-sajadi/tech_pulse_fetcher.git
    cd tech_pulse_fetcher
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
    LLM_API_KEY="your_cheaperinference_api_key"
    LLM_BASE_URL="https://api.cheaperinference.com/v1"
    LLM_MODEL="deepseek-v4-pro"
    PRODUCT_HUNT_TOKEN="your_product_hunt_token" # Optional
    SUPABASE_URL="your_supabase_url"
    SUPABASE_KEY="your_supabase_key"
    ```

    The LLM client uses the OpenAI-compatible API transport, but does not connect to OpenAI directly. Configure the gateway URL, key, and model through the `LLM_*` variables.

### Running the Workflow Manually

To run the entire data fetching and processing pipeline manually, execute the `main.py` script:

```bash
python main.py
```

This will:
1. Fetch data from all sources.
2. Process the data using the `DataProcessor` class.
3. Generate a market deep dive when Last30Days is configured and the evidence supports one.
4. Save the processed snapshot to your Supabase database.

### Daily Market Deep Dive

Pulse asks the LLM to select one market story from today's news using the past week's briefs as context. It runs [Last30Days](https://github.com/mvanhorn/last30days-skill) over a 30-day window using public Hacker News and Reddit results. The LLM uses the original coverage and research to write a one-sentence takeaway, a short sequence of events, the business impact, and a conditional outlook for the next year and the next two to three years.

The snapshot stores this optional brief as `pulse_data.market_deep_dive`. The summary and each point have structured source IDs that resolve to article URLs in the brief's `sources` array. The [HeySignal frontend](https://github.com/pouyan-sajadi/signal-news-frontend) displays those IDs as inline article links. Pulse logs the draft’s validation failures and gives the model one chance to repair them using the same evidence. The regular brief publishes when research is unavailable or neither draft passes.

GitHub Actions checks out the pinned Last30Days revision in [the daily workflow](.github/workflows/daily-pulse.yml) and sets `LAST30DAYS_SCRIPT`. To enable the deep dive locally, check out the same revision and set `LAST30DAYS_SCRIPT` to the absolute path to its `skills/last30days/scripts/last30days.py`. The public research sources use no extra API keys.

### Automated Workflow

The [daily workflow](.github/workflows/daily-pulse.yml) schedules `main.py` every day at 9:30 a.m. Toronto time, including weekends. The schedule follows Toronto’s daylight saving time.

For the automated workflow to function, you must configure the following secrets in your GitHub repository's settings (**Settings > Secrets and variables > Actions**):

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `PRODUCT_HUNT_TOKEN` (optional)
- `SUPABASE_URL`
- `SUPABASE_KEY`

## Project Structure

- `main.py`: The main entry point for the data processing workflow.
- `src/tech_pulse_fetcher.py`: Contains the `TechPulseFetcher` class for fetching data from various sources.
- `src/data_processor.py`: Contains the `DataProcessor` class for processing the fetched data.
- `src/market_deep_dive.py`: Selects and researches a market story, then validates the brief and sources.
- `.github/workflows/daily-pulse.yml`: The GitHub Actions workflow for daily execution.
- `requirements.txt`: A list of the Python dependencies for the project.
- `logs/`: Contains log files for debugging.
