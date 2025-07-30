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