# MUN Delegate Analysis Tool

This tool analyzes Model UN position papers to identify how delegates approach their country assignments and topics. Rather than training a model on previous papers, it generates multiple approach templates for comparison and uses linguistic analysis to identify which approaches the delegate most closely aligns with.

## Features

- **Automatic Approach Detection**: Identifies how a delegate approaches their country assignment by comparing their writing to multiple generated templates
- **Linguistic Analysis**: Uses perplexity, burstiness, sentiment, and keyword analysis to understand writing styles
- **Multiple Interfaces**: Command-line, interactive mode, and web interface options
- **Visualization**: Creates radar charts and bar graphs to visualize the delegate's approach "fingerprint"
- **Configurable**: Easy customization via JSON configuration files

## Installation

### Prerequisites

- Python 3.8 or higher
- PyTorch
- Transformers (Hugging Face)
- NLTK
- Matplotlib
- Streamlit (for web interface)

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/mun-delegate-analyzer.git
   cd mun-delegate-analyzer
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Download NLTK resources:
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   nltk.download('vader_lexicon')
   ```

## Usage

### Command Line Interface

Create a configuration file:

```
python main.py config --topic "Climate Change Mitigation" --country "Sweden" --committee "UNEP"
```

List available configurations:

```
python main.py list
```

Analyze a delegate paper:

```
python main.py analyze --config configs/sweden_unep.json --paper delegate_paper.txt --output-dir results
```

Run in interactive mode:

```
python main.py interactive
```

### Web Interface

Run the web interface:

```
streamlit run web_interface.py
```

This will open a web browser with an interactive interface for configuring and running analyses.

## How It Works

The analysis approach involves several key components:

1. **Approach Templates**: The tool generates different approach templates based on the country and topic, representing various ways a delegate might approach their assignment:
   - Highlighting positive achievements
   - Focusing on regional cooperation
   - Emphasizing economic aspects
   - Humanitarian concerns
   - Diplomatic/neutral stance
   - Historical context
   - Sovereignty issues
   - Legal frameworks

2. **Linguistic Analysis**: The delegate's paper is analyzed using:
   - **Perplexity**: Measures text complexity and unpredictability
   - **Burstiness**: Assesses variance in sentence structure and length
   - **Keyword Extraction**: Identifies key terms and concepts
   - **Sentiment Analysis**: Determines emotional tone

3. **Similarity Calculation**: The delegate's paper is compared to each approach template based on these linguistic features, creating a similarity score.

4. **Fingerprint Creation**: The results are visualized as a "fingerprint" showing the delegate's approach preferences.

## Configuration

The tool is configured via JSON files with the following structure:

```json
{
  "topic": "Climate Change Mitigation",
  "country": "Sweden",
  "committee": "UNEP",
  "document_type": "position_paper",
  "output_format": "all",
  "analysis_settings": {
    "perplexity_weight": 0.25,
    "burstiness_weight": 0.25,
    "keywords_weight": 0.3,
    "sentiment_weight": 0.2
  }
}
```

## Project Structure

- `mun_delegate_analyzer.py`: Core analysis engine
- `config_handler.py`: Manages configuration files
- `main.py`: Command-line interface
- `web_interface.py`: Streamlit web interface
- `configs/`: Directory for saved configurations
- `results/`: Default directory for analysis results

## Extending the Tool

### Adding New Approaches

To add a new approach template, edit the `approach_types` list in `MUNDelegateAnalyzer.__init__()` and add a corresponding prompt in the `generate_prompt()` method.

### Customizing Analysis

Adjust the weights in the configuration file to prioritize different linguistic features in the analysis.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on research on perplexity and burstiness as indicators of writing styles
- Uses Hugging Face Transformers for language modeling
- NLTK for linguistic analysis

## Citation

If you use this tool in your research, please cite it as:

```
Author, A. (2025). MUN Delegate Analysis Tool: Identifying Approach Patterns in Model UN Position Papers. GitHub Repository. https://github.com/yourusername/mun-delegate-analyzer
```
