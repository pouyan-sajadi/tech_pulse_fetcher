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

- **Automated Daily Updates**: Fresh data every morning
- **AI-Powered Analysis**: LLMs extract insights, not just data
- **Interactive Visualizations**:
  - Programming language trends (GitHub)
  - Product category flows (Product Hunt)
  - News word clouds and hot topics
  - Prediction market sentiment analysis
- **Cross-Source Intelligence**: See connections between what's being built and what's launching
- **Zero Maintenance**: Fully automated pipeline

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI
- **Data Fetching**: TechPulseFetcher (included)
- **AI/ML**: OpenAI GPT-4 for analysis
- **Frontend**: React, D3.js, Chart.js
- **Styling**: Tailwind CSS
- **Deployment**: Docker-ready

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- OpenAI API key
- Product Hunt API token (optional, falls back to RSS)

## Current Implementation Status

This section outlines the progress made on the data fetching and processing pipeline.

### Data Fetching (`src/tech_pulse_fetcher.py`)
- **Product Hunt**: Fetches top products using the GraphQL API (with RSS fallback).
- **GitHub Trending**: Scrapes trending repositories, including accurate star counts.
- **RSS Feeds**: Aggregates articles from curated tech news sources.
- **Manifold Markets**: Fetches prediction market data with filtering for tech-related and active markets.
- **File Organization**: All raw fetched data is now saved to the `fetched_data/` directory.

### Data Processing (`src/data_processor.py`)
- **GitHub Trending Analysis**: Processes raw GitHub data to generate language distribution, including total stars and stars gained today, saved to `processed_data/github_language_distribution.json`.
- **RSS Feed Analysis (Word Cloud & Hot Topics)**: Aggregates text, performs local word frequency counting (with stop word removal), and then uses an LLM to extract important keywords and hot topics, saved to `processed_data/news_word_cloud.json`.
- **Product Hunt Tag Analysis (Sankey Diagram)**: Reads Product Hunt data, uses an LLM to map product topics to predefined core categories, and generates Sankey diagram nodes and links based on co-occurrence, saved to `processed_data/product_hunt_tag_connections.json`.
- **Manifold Markets Analysis (Bubble Plot)**: Processes Manifold data, uses an LLM to extract sentiment and categorize predictions, and formats the data for a 2D bubble plot, saved to `processed_data/manifold_predictions_bubble_plot.json`.
- **File Organization**: All processed data is saved to the `processed_data/` directory.

## 🔧 Installation

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/pouyan-sajadi/tech_pulse_fetcher.git
cd tech-pulse-fetcher

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```