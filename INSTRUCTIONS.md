# Tech Pulse Dashboard - Complete Implementation Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Tech Stack](#architecture--tech-stack)
3. [Data Processing Pipeline](#data-processing-pipeline)
4. [Implementation Guide](#implementation-guide)
   - [GitHub Trending Analysis](#1-github-trending-analysis)
   - [Product Hunt Tag Analysis](#2-product-hunt-tag-analysis)
   - [News Article Analysis](#3-news-article-analysis)
   - [Manifold Markets Analysis](#4-manifold-markets-analysis)
5. [Frontend Integration](#frontend-integration)
6. [Deployment & Daily Operations](#deployment--daily-operations)

---

## Project Overview

### Why This Project Exists
The tech ecosystem moves fast. Developers, investors, and tech enthusiasts need to track multiple sources daily to understand what's happening. This dashboard solves that problem by creating a single, intelligent view that connects the dots between:
- What's being built (GitHub)
- What's launching (Product Hunt)  
- What's being discussed (News)
- What's being predicted (Markets)

### What Makes This Different
- **Automated Intelligence**: LLMs extract meaning, not just data
- **Cross-Source Insights**: See connections between GitHub trends and Product Hunt launches
- **Visual First**: Complex data becomes simple visuals
- **Daily Habit**: Designed for a 5-minute morning check

### Success Metrics
- Users visit daily (high retention)
- Time to insight < 30 seconds
- Zero manual maintenance required
- Surfaces 1-2 "aha" moments per week

---

## Architecture & Tech Stack

### System Architecture
- **Data Layer**: Existing backend fetches daily data from 4 sources
- **Processing Layer**: Python scripts transform and analyze data
- **Intelligence Layer**: LLM APIs extract insights and categories
- **API Layer**: FastAPI serves processed data to frontend
- **Presentation Layer**: React/Vue app with interactive visualizations

### Technology Choices
- **Backend**: Python (existing), FastAPI (new)
- **LLM**: OpenAI GPT-4 for analysis
- **Database**: Simple JSON storage (no complex DB needed)
- **Frontend**: React with D3.js and Chart.js
- **Deployment**: Docker container on cloud provider

### Data Flow
1. Cron job triggers daily fetch (existing)
2. Processing pipeline runs on new data
3. Results cached as JSON files
4. API serves cached results
5. Frontend polls API and renders

---

## Data Processing Pipeline

### Overall Pipeline Design
Each data source follows the same pattern:
1. **Ingest**: Read raw JSON data
2. **Clean**: Handle missing values, normalize formats
3. **Analyze**: Extract insights via LLM
4. **Transform**: Convert to visualization format
5. **Cache**: Store results for API serving

### Pipeline Implementation Steps
- [ ] Create main pipeline orchestrator
- [ ] Set up error handling and logging
- [ ] Implement retry logic for LLM calls
- [ ] Add data validation at each step
- [ ] Create health check endpoint
- [ ] Set up monitoring and alerts

---

## Implementation Guide

## 1. GitHub Trending Analysis

### Goal
Show programming language distribution as a pie chart to understand what technologies developers are focusing on.

### Backend Implementation Tasks

**Data Processing Module**
- [ ] Create function to read GitHub trending JSON data
- [ ] Count repositories by programming language
- [ ] Handle edge cases (null language = "Other")
- [ ] Calculate total stars per language
- [ ] Implement threshold logic (languages <2% become "Other")
- [ ] Sort languages by popularity
- [ ] Calculate percentages for each language

**Enhancement Features**
- [ ] Add "momentum score" (stars per repo)
- [ ] Identify "rising" languages (high stars, few repos)
- [ ] Create language color mapping
- [ ] Add daily comparison (if historical data exists)

**Output Structure**
- [ ] Design JSON schema for pie chart data
- [ ] Include metadata (timestamp, total repos)
- [ ] Add language details (count, percentage, stars)
- [ ] Validate output format

### Frontend Implementation Tasks

**Pie Chart Component**
- [ ] Create React component for GitHub visualization
- [ ] Integrate Chart.js for pie chart
- [ ] Set up responsive sizing
- [ ] Define color scheme for top languages

**Interactivity**
- [ ] Implement hover tooltips showing details
- [ ] Add click handler to filter by language
- [ ] Create legend with toggle functionality
- [ ] Add animation on data load

---

## 2. Product Hunt Tag Analysis

### Goal
Create Sankey diagram showing how product categories flow and connect, revealing market trends and gaps.

### Backend Implementation Tasks

**Tag Extraction Pipeline**
- [ ] Set up OpenAI API connection
- [ ] Create prompt template for tag extraction
- [ ] Implement batch processing for all products
- [ ] Add tag normalization (AI vs Artificial Intelligence)
- [ ] Handle API rate limits gracefully
- [ ] Cache extracted tags to avoid re-processing

**Relationship Analysis**
- [ ] Track tag co-occurrences within products
- [ ] Build connection matrix between tags
- [ ] Calculate connection strengths
- [ ] Filter weak connections (threshold: 2+ occurrences)
- [ ] Identify tag clusters

**Sankey Data Preparation**
- [ ] Create nodes array with unique tags
- [ ] Build links array with connections
- [ ] Calculate flow widths based on frequency
- [ ] Optimize for visual clarity (limit tags)
- [ ] Add source product references

### Frontend Implementation Tasks

**Sankey Diagram Component**
- [ ] Set up D3.js Sankey layout
- [ ] Create React wrapper component
- [ ] Implement responsive scaling
- [ ] Define color scheme for flows

**Interactive Features**
- [ ] Add hover highlighting for paths
- [ ] Show connection details on hover
- [ ] Click tag to see product list
- [ ] Add flow animation
- [ ] Create tag filter controls

---

## 3. News Article Analysis

### Goal
Generate word cloud of key tech terms and identify the hottest topics being discussed across tech media.

### Backend Implementation Tasks

**Text Processing**
- [ ] Aggregate all article titles and descriptions
- [ ] Implement text cleaning (remove punctuation, lowercase)
- [ ] Create stop words list for tech articles
- [ ] Extract company names and technologies
- [ ] Combine similar terms (AI, A.I., artificial intelligence)

**LLM Analysis**
- [ ] Design prompt for keyword extraction
- [ ] Request importance scores (1-10) for each keyword
- [ ] Get keyword categories from LLM
- [ ] Extract top 3 "hot topics" with summaries
- [ ] Generate topic trend indicators

**Word Cloud Data**
- [ ] Map keywords to sizes (based on frequency + importance)
- [ ] Assign colors by category
- [ ] Limit to top 40 words for clarity
- [ ] Include metadata for interactions
- [ ] Create topic summary cards data

### Frontend Implementation Tasks

**Word Cloud Visualization**
- [ ] Integrate word cloud library
- [ ] Create responsive container
- [ ] Implement custom color scheme
- [ ] Optimize word placement algorithm

**Hot Topics Section**
- [ ] Design topic cards component
- [ ] Add article count badges
- [ ] Create expandable details view
- [ ] Link to source articles

**Interactivity**
- [ ] Click word to filter articles
- [ ] Hover to show frequency
- [ ] Topic card expansion animation
- [ ] Search/filter functionality

---

## 4. Manifold Markets Analysis

### Goal
Extract 5-10 most critical predictions and visualize them on a 2D plot showing sentiment (X-axis) and categories (Y-axis), with bubble size representing investment volume.

### Backend Implementation Tasks

**Prediction Filtering**
- [ ] Sort predictions by pool size (top 50)
- [ ] Filter for tech-related predictions only
- [ ] Remove duplicate or similar predictions
- [ ] Ensure minimum betting activity threshold

**LLM Analysis per Prediction**
- [ ] Create comprehensive prompt including all prediction data
- [ ] Extract sentiment score (-1 bearish to +1 bullish)
- [ ] Categorize into tech verticals (AI, Robotics, Crypto, etc.)
- [ ] Generate importance score based on pool size and activity
- [ ] Write one-line insight about why it matters
- [ ] Select final 5-10 most insightful predictions

**Data Structuring**
- [ ] Create 2D plot data structure
- [ ] Map categories to Y-axis positions
- [ ] Calculate X position from sentiment
- [ ] Set bubble size from pool total
- [ ] Include hover data (title, probability, insight)
- [ ] Add color coding by probability ranges

### Frontend Implementation Tasks

**2D Bubble Plot Component**
- [ ] Create scatter plot with D3.js or Chart.js
- [ ] Set up X-axis (bearish -1 to bullish +1)
- [ ] Set up Y-axis (category positions)
- [ ] Implement bubble sizing logic

**Visual Enhancements**
- [ ] Color bubbles by probability (red to green gradient)
- [ ] Add subtle animations on load
- [ ] Create axis labels and grid
- [ ] Add category labels on Y-axis

**Interactivity**
- [ ] Hover to show prediction details
- [ ] Click to open Manifold market page
- [ ] Add zoom/pan capabilities
- [ ] Filter by category option

---

## Frontend Integration

### Dashboard Layout
- [ ] Create main dashboard container
- [ ] Implement 2x2 grid layout for four visualizations
- [ ] Add responsive breakpoints for mobile
- [ ] Create loading states for each component
- [ ] Add error handling UI

### Data Fetching
- [ ] Set up API client with base URL configuration
- [ ] Implement data fetching for each endpoint
- [ ] Add caching to prevent unnecessary API calls
- [ ] Create refresh mechanism
- [ ] Handle API errors gracefully

### Navigation & Controls
- [ ] Add date selector (if historical data available)
- [ ] Create refresh button
- [ ] Add export functionality (image/data)
- [ ] Implement fullscreen mode for each viz
- [ ] Add help/info tooltips

### Performance Optimization
- [ ] Lazy load visualization libraries
- [ ] Implement virtual scrolling for lists
- [ ] Optimize re-renders with memoization
- [ ] Add progressive loading for large datasets
- [ ] Compress and minify assets

---

## Deployment & Daily Operations

### Deployment Setup
- [ ] Create Dockerfile for backend service
- [ ] Set up environment variables management
- [ ] Configure API endpoints for production
- [ ] Set up SSL certificates
- [ ] Implement CI/CD pipeline

### Daily Operations
- [ ] Set up cron job for daily data fetch
- [ ] Create data processing trigger
- [ ] Implement cache invalidation strategy
- [ ] Add logging for all operations
- [ ] Set up error alerting

### Monitoring
- [ ] Track API response times
- [ ] Monitor LLM API usage and costs
- [ ] Log user engagement metrics
- [ ] Track visualization load times
- [ ] Set up uptime monitoring

### Maintenance Tasks
- [ ] Create data backup strategy
- [ ] Plan for LLM prompt updates
- [ ] Document all API endpoints
- [ ] Create admin dashboard for monitoring
- [ ] Set up automated testing

### Future Enhancements
- [ ] Add historical trend analysis
- [ ] Implement user customization options
- [ ] Create mobile app version
- [ ] Add email digest option
- [ ] Integrate more data sources