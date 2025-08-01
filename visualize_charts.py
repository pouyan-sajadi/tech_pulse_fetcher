import json
import matplotlib.pyplot as plt
import os
import numpy as np

def visualize_github_pie_chart():
    try:
        with open('processed_data/github_language_distribution.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: processed_data/github_language_distribution.json not found. Please run data_processor.py first.")
        return

    labels = data['labels']
    sizes = data['datasets'][0]['data']
    colors = data['datasets'][0]['backgroundColor']

    # Create pie chart
    fig1, ax1 = plt.subplots(figsize=(10, 10))
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax1.set_title('GitHub Trending Language Distribution')

    # Save the chart
    output_dir = 'visualizations'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'github_language_pie_chart.png'))
    print(f"Saved GitHub Language Pie Chart to {os.path.join(output_dir, 'github_language_pie_chart.png')}")

    plt.close(fig1) # Close the plot to free memory

def visualize_news_keywords_bar_chart():
    try:
        with open('processed_data/news_word_cloud.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: processed_data/news_word_cloud.json not found. Please run data_processor.py first.")
        return

    keywords = data.get('word_cloud', [])
    if not keywords:
        print("No keywords found in news_word_cloud.json.")
        return

    # Sort keywords by value (importance) in descending order
    keywords.sort(key=lambda x: x.get('value', 0), reverse=True)

    # Take top N keywords for the bar chart
    top_n = 20 # You can adjust this number
    display_keywords = keywords[:top_n]

    labels = [k['text'] for k in display_keywords]
    values = [k['value'] for k in display_keywords]

    # Create horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(labels, values, color='skyblue')
    ax.set_xlabel('Importance Score (1-100)')
    ax.set_ylabel('Keyword')
    ax.set_title(f'Top {top_n} News Keywords by Importance')
    ax.invert_yaxis() # Display highest value at the top

    # Save the chart
    output_dir = 'visualizations'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'news_keywords_bar_chart.png'))
    print(f"Saved News Keywords Bar Chart to {os.path.join(output_dir, 'news_keywords_bar_chart.png')}")

    plt.close(fig)

def visualize_product_hunt_heatmap():
    try:
        with open('processed_data/product_hunt_tag_connections.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: processed_data/product_hunt_tag_connections.json not found. Please run data_processor.py first.")
        return

    nodes = data.get('nodes', [])
    links = data.get('links', [])

    if not nodes or not links:
        print("No data for Product Hunt heatmap.")
        return

    num_nodes = len(nodes)
    matrix = np.zeros((num_nodes, num_nodes))
    
    for link in links:
        source_id = link['source']
        target_id = link['target']
        value = link['value']
        matrix[source_id, target_id] = value
        matrix[target_id, source_id] = value # For undirected connections

    fig, ax = plt.subplots(figsize=(12, 12))
    cax = ax.matshow(matrix, cmap='viridis')
    fig.colorbar(cax)

    node_names = [node['name'] for node in nodes]
    ax.set_xticks(np.arange(num_nodes))
    ax.set_yticks(np.arange(num_nodes))
    ax.set_xticklabels(node_names, rotation=90)
    ax.set_yticklabels(node_names)

    ax.set_title('Product Hunt Category Co-occurrence Heatmap')
    
    output_dir = 'visualizations'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'product_hunt_heatmap.png'))
    print(f"Saved Product Hunt Heatmap to {os.path.join(output_dir, 'product_hunt_heatmap.png')}")
    plt.close(fig)

def visualize_manifold_scatter_plot():
    try:
        with open('processed_data/manifold_predictions_bubble_plot.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: processed_data/manifold_predictions_bubble_plot.json not found. Please run data_processor.py first.")
        return

    dataset = data.get('datasets', [{}])[0].get('data', [])
    categories = data.get('categories', [])

    if not dataset:
        print("No data for Manifold scatter plot.")
        return

    # Group data by category for coloring
    grouped_data = {}
    for item in dataset:
        cat = item['category']
        if cat not in grouped_data:
            grouped_data[cat] = {'x': [], 'y': []}
        grouped_data[cat]['x'].append(item['x'])
        grouped_data[cat]['y'].append(item['y'])

    fig, ax = plt.subplots(figsize=(14, 10))

    # Define a color map for categories
    color_map = plt.get_cmap('viridis', len(categories))
    category_colors = {cat: color_map(i) for i, cat in enumerate(categories)}

    for i, category in enumerate(categories):
        if category in grouped_data:
            ax.scatter(grouped_data[category]['x'], grouped_data[category]['y'], 
                       color=category_colors[category], label=category, alpha=0.7, edgecolors='w', s=100)

    ax.set_xlabel('Probability (0% to 100%)')
    ax.set_ylabel('Trading Volume ($)')
    ax.set_title('Manifold Markets: Probability vs. Volume by Category')
    ax.legend(title='Categories')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Format y-axis to be more readable
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'${int(y):,}'))

    output_dir = 'visualizations'
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'manifold_scatter_plot.png'))
    print(f"Saved Manifold Scatter Plot to {os.path.join(output_dir, 'manifold_scatter_plot.png')}")
    plt.close(fig)


if __name__ == '__main__':
    visualize_github_pie_chart()
    visualize_news_keywords_bar_chart()
    visualize_product_hunt_heatmap()
    visualize_manifold_scatter_plot()
