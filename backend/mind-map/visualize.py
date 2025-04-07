#!/usr/bin/env python3
import json
import os
import sys
import argparse
import matplotlib.pyplot as plt
import networkx as nx
import logging
from matplotlib.cm import get_cmap
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_json_file(file_path):
    """Load a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded JSON from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
        return None

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

def visualize_mind_map(visualization_json, output_file=None):
    """
    Visualize the mind map using NetworkX and Matplotlib.
    
    Args:
        visualization_json: The visualization JSON from the mind map
        output_file: Optional path to save the visualization image
    """
    try:
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes with attributes
        for node in visualization_json["nodes"]:
            G.add_node(
                node["id"], 
                label=node["label"], 
                size=node["size"], 
                color=node.get("color", "#4A90E2"),
                highlighted=node.get("highlighted", False),
                type=node.get("type", "topic"),
                relevance=node.get("relevance", 5)
            )
        
        # Add edges with attributes
        for link in visualization_json["links"]:
            G.add_edge(
                link["source"], 
                link["target"], 
                weight=link.get("value", 1),
                dashed=link.get("dashed", False)
            )
        
        # Create figure
        plt.figure(figsize=(16, 12))
        
        # Use different layout algorithms based on the size of the graph
        if len(G.nodes) < 10:
            pos = nx.spring_layout(G, k=0.5, iterations=50)
        else:
            # For larger graphs, use a more spaced-out layout
            pos = nx.kamada_kawai_layout(G)
        
        # Draw nodes
        node_sizes = [G.nodes[node]["size"] * 100 for node in G.nodes]
        node_colors = [G.nodes[node]["color"] for node in G.nodes]
        
        # Draw regular nodes
        nx.draw_networkx_nodes(
            G, pos, 
            node_size=node_sizes,
            node_color=node_colors,
            alpha=0.9
        )
        
        # Draw highlighted nodes with a border
        highlighted_nodes = [node for node in G.nodes if G.nodes[node].get("highlighted", False)]
        if highlighted_nodes:
            nx.draw_networkx_nodes(
                G, pos, 
                nodelist=highlighted_nodes,
                node_size=[G.nodes[node]["size"] * 100 for node in highlighted_nodes],
                node_color=[G.nodes[node]["color"] for node in highlighted_nodes],
                edgecolors='black',
                linewidths=2,
                alpha=0.9
            )
        
        # Draw edges with different styles
        regular_edges = [(u, v) for u, v, d in G.edges(data=True) if not d.get("dashed", False)]
        dashed_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("dashed", False)]
        
        # Draw regular edges
        nx.draw_networkx_edges(
            G, pos,
            edgelist=regular_edges,
            width=[G[u][v].get("weight", 1) * 2 for u, v in regular_edges],
            alpha=0.7,
            arrows=True,
            arrowsize=20,
            node_size=node_sizes  # Important to scale arrows properly
        )
        
        # Draw dashed edges
        nx.draw_networkx_edges(
            G, pos,
            edgelist=dashed_edges,
            width=[G[u][v].get("weight", 1) * 1.5 for u, v in dashed_edges],
            alpha=0.5,
            style="dashed",
            arrows=True,
            arrowsize=15,
            node_size=node_sizes
        )
        
        # Draw labels with different sizes based on node type
        labels = {node: G.nodes[node]["label"] for node in G.nodes}
        nx.draw_networkx_labels(
            G, pos, 
            labels=labels, 
            font_size=10,
            font_weight="bold",
            font_family="sans-serif"
        )
        
        # Add the title
        plt.title(visualization_json.get("title", "Mind Map"), fontsize=16, fontweight="bold")
        plt.axis("off")
        
        # Add a legend
        relevance_legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='High Relevance', 
                      markersize=15, markerfacecolor="#7FBA00"),
            plt.Line2D([0], [0], marker='o', color='w', label='Medium Relevance', 
                      markersize=15, markerfacecolor="#FFBA08"),
            plt.Line2D([0], [0], marker='o', color='w', label='Low Relevance', 
                      markersize=15, markerfacecolor="#E74C3C")
        ]
        
        node_type_legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='Central Topic', 
                      markersize=15, markerfacecolor="#4A90E2"),
            plt.Line2D([0], [0], marker='o', color='w', label='Topic', 
                      markersize=12, markerfacecolor="#7FBA00"),
            plt.Line2D([0], [0], marker='o', color='w', label='Subtopic', 
                      markersize=8, markerfacecolor="#7FBA00")
        ]
        
        # Add legend for highlighted nodes
        if highlighted_nodes:
            highlighted_legend = [
                plt.Line2D([0], [0], marker='o', color='w', label='Highlighted',
                          markeredgecolor='black', markersize=15, 
                          markerfacecolor="white", markeredgewidth=2)
            ]
            plt.legend(handles=relevance_legend_elements + node_type_legend_elements + highlighted_legend, 
                      loc='upper left', bbox_to_anchor=(1, 1))
        else:
            plt.legend(handles=relevance_legend_elements + node_type_legend_elements, 
                      loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        
        # Save or show the plot
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            logger.info(f"Saved visualization to {output_file}")
        else:
            plt.show()
            
        return True
        
    except Exception as e:
        logger.error(f"Error visualizing mind map: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Visualize Mind Map')
    parser.add_argument('--input', type=str, help='Path to visualization JSON file', required=True)
    parser.add_argument('--output', type=str, help='Path to save the visualization image', default=None)
    
    args = parser.parse_args()
    
    # Load the visualization JSON
    viz_json = load_json_file(args.input)
    if not viz_json:
        logger.error("Failed to load visualization JSON")
        sys.exit(1)
    
    # Generate the visualization
    success = visualize_mind_map(viz_json, args.output)
    
    if not success:
        logger.error("Visualization failed")
        sys.exit(1)
    
    logger.info("Visualization complete")
    sys.exit(0)

if __name__ == "__main__":
    main() 