# Signal App: Tech Pulse Dashboard Integration Guide

**Objective:** Integrate the daily tech-pulse data from our Supabase database into the Signal App frontend to create a dynamic, interactive, and visually appealing dashboard.

---

## 1. Connecting to Supabase in Your Next.js App

First, you need to enable your Next.js backend to securely communicate with Supabase.

### 1.1. Install Supabase Client

In your Signal App project terminal, install the official Supabase client library:

```bash
npm install @supabase/supabase-js
```

### 1.2. Set Up Environment Variables

Create or update your `.env.local` file in the root of your Signal App project. You will need the **URL** and the **Service Role Key** from your Supabase project dashboard (**Project Settings > API**).

**Important:** The `SERVICE_ROLE_KEY` is highly sensitive and should ONLY be used in server-side code (like API routes). It bypasses all Row Level Security policies.

```env
# .env.local

# Publicly available URL for your Supabase project
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url

# Secret key for server-side operations (DO NOT EXPOSE TO CLIENT)
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

---

## 2. Creating the API Endpoint to Fetch Data

We will create a server-side API route that fetches the most recent data entry from our `tech_pulses` table.

Create a new file at: `src/app/api/tech-pulse/latest/route.ts`

```typescript
// src/app/api/tech-pulse/latest/route.ts

import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

// It's safe to use these env vars here because this code ONLY runs on the server.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

// Create a Supabase client for server-side operations
const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey);

// This setting tells Next.js to not cache this route, ensuring fresh data on every request.
// You can also use time-based revalidation if preferred, e.g., export const revalidate = 3600;
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const { data, error } = await supabaseAdmin
      .from('tech_pulses')
      .select('pulse_data, created_at')
      .order('created_at', { ascending: false }) // Get the newest first
      .limit(1)  // We only want the most recent one
      .single(); // Expect a single row response, which is more efficient

    if (error) {
      // If .single() finds no rows, it returns a specific error code.
      if (error.code === 'PGRST116') {
        return NextResponse.json({ message: 'No tech pulse data found.' }, { status: 404 });
      }
      // For other errors, re-throw to be caught by the catch block
      throw error;
    }

    // The `pulse_data` is stored as a JSON string, so we parse it before sending.
    // Note: Supabase client libraries often auto-parse JSONB, but it's good practice to ensure it's an object.
    const responseData = {
        ...data,
        pulse_data: typeof data.pulse_data === 'string' ? JSON.parse(data.pulse_data) : data.pulse_data
    };

    return NextResponse.json(responseData);

  } catch (err: any) {
    console.error('Error fetching latest tech pulse:', err);
    return NextResponse.json(
      { message: 'Error fetching latest tech pulse', error: err.message },
      { status: 500 }
    );
  }
}
```

You can now fetch the data from your frontend components by calling `fetch('/api/tech-pulse/latest')`.

---

## 3. Understanding the Data Structure

The API will return a JSON object with two top-level keys: `created_at` and `pulse_data`. The `pulse_data` contains all the processed information for your dashboard.

### Example `pulse_data` Object:

Here is a real example of the `pulse_data` object you will receive:

```json
{
  "github_language_distribution": {
    "labels": ["Python", "HTML", "TypeScript", "Go", "C++"],
    "datasets": [{
      "label": "GitHub Trending Languages",
      "data": [2, 1, 4, 1, 2],
      "backgroundColor": ["#3572A5", "#F1E05A", "#00ADD8", "#DEA584", "#89E051", "#B07219", "#CCCCCC"],
      "hoverData": [{
        "total_stars": 22421,
        "stars_today": 2065,
        "repositories": [{
          "title": "OpenPipe/ART",
          "description": "Agent Reinforcement Trainer...",
          "url": "https://github.com/OpenPipe/ART",
          "stars": 4613,
          "stars_today": 397
        }, {
          "title": "9001/copyparty",
          "description": "Portable file server...",
          "url": "https://github.com/9001/copyparty",
          "stars": 17808,
          "stars_today": 1668
        }]
      },
      { "total_stars": 6796, "stars_today": 38, "repositories": [...] },
      { "total_stars": 97955, "stars_today": 647, "repositories": [...] },
      { "total_stars": 16337, "stars_today": 46, "repositories": [...] },
      { "total_stars": 12001, "stars_today": 282, "repositories": [...] }
      ]
    }]
  },
  "news_word_cloud": {
    "keywords": [
      { "text": "tesla", "value": 80 },
      { "text": "autopilot", "value": 75 },
      { "text": "damages", "value": 70 }
    ],
    "hot_topics": [{
      "topic": "Tesla Autopilot Legal Issues",
      "summary": "A jury finds Tesla partly liable for damages involving its autopilot technology.",
      "trend": "rising"
    }, {
      "topic": "Tech Company Leadership",
      "summary": "Discussion around CEOs of major tech companies like Apple and Tesla.",
      "trend": "stable"
    }]
  },
  "product_hunt_tag_connections": {
    "nodes": [
      { "node": 0, "name": "AI/ML" },
      { "node": 1, "name": "Developer Tools" },
      { "node": 2, "name": "Productivity" }
    ],
    "links": []
  },
  "manifold_predictions_bubble_plot": {
    "datasets": [{
      "label": "Manifold Predictions",
      "data": [{
        "x": 0.01003,
        "y": 269741.52,
        "label": "Will Ukraine and Russia reach a ceasefire...?",
        "category": "Politics/Society",
        "url": "https://manifold.markets/Moscow25/will-ukraine-and-russia-reach-a-cea"
      }, {
        "x": 0.9221,
        "y": 118182.99,
        "label": "Will Trump sign a deal with Ukraine...?",
        "category": "Politics/Society",
        "url": "https://manifold.markets/TimothyJohnson5c16/will-trump-sign-a-deal-with-ukraine"
      }]
    }],
    "categories": ["AI", "Blockchain/Crypto", "Science/Research", "Politics/Society", "Economics/Finance", "Technology (General)", "Health", "Other"]
  }
}
```

---

## 4. Dashboard Implementation Ideas

Here are some suggestions for creating a visually creative and interactive dashboard. We recommend using a library like **Chart.js** (with `react-chartjs-2`), **Recharts**, or for more custom visualizations, **D3.js**.

### 4.1. GitHub Trending: Interactive Donut Chart

-   **Data:** `github_language_distribution`
-   **Visualization:** A **Donut Chart** is perfect here. The `labels` and `datasets[0].data` map directly to the chart's labels and data.
-   **Interactivity:**
    -   On hover over a slice (e.g., "Python"), display a tooltip showing the detailed `hoverData` for that language: total stars, stars gained today.
    -   On click, you could display the list of repositories for that language in a modal or a separate card, linking to their GitHub pages.

### 4.2. Tech News: Word Cloud & Hot Topics Ticker

-   **Data:** `news_word_cloud`
-   **Visualization:**
    -   **Keywords:** Use a word cloud library (e.g., `react-wordcloud`) to display the `keywords`. The `value` field can determine the font size of each `text`.
    -   **Hot Topics:** Display these in a dynamic "ticker" or a carousel. Each item should show the `topic`, `summary`, and an icon representing the `trend` (e.g., an upward arrow for "rising").
-   **Interactivity:** Clicking a keyword could filter a list of news articles (if we decide to store them later).

### 4.3. Product Hunt Connections: Sankey or Chord Diagram

-   **Data:** `product_hunt_tag_connections`
-   **Visualization:** This data is structured for a **Sankey Diagram** or a **Chord Diagram**. These are more advanced charts and might require a library like D3.js or a specialized React component. The `nodes` represent the categories, and the `links` (with their `value`) represent the strength of the connection between them.
-   **Interactivity:** Hovering over a link could highlight the two connected categories and show the exact number of co-occurrences.

### 4.4. Prediction Markets: Bubble Plot

-   **Data:** `manifold_predictions_bubble_plot`
-   **Visualization:** A **Bubble Plot** is ideal. The `datasets[0].data` array contains the points.
    -   `x`: Probability (0 to 1)
    -   `y`: Trading Volume (determines the bubble's vertical position)
    -   The bubble's **size** should also be proportional to the `y` (volume) to give it more visual weight.
    -   The bubble's **color** should be based on its `category`.
-   **Interactivity:**
    -   On hover, display a tooltip with the full `label` (the prediction question) and its exact probability and volume.
    -   On click, open the prediction `url` in a new tab.
    -   Add filters to the UI to show/hide different `categories`.

Good luck with the implementation!
