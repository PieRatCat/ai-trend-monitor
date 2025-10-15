# AI Trend Monitor - Streamlit App

This directory contains the Streamlit web application for the AI Trend Monitor project.

## Running Locally

1. Activate the conda environment:
```bash
conda activate trend-monitor
```

2. Install dependencies (if not already installed):
```bash
pip install -r ../requirements.txt
```

3. Make sure your `.env` file is in the project root with:
```
SEARCH_ENDPOINT=your_search_endpoint
SEARCH_KEY=your_search_key
```

4. Run the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

- **🔍 Search Page**: Search and filter AI articles by keywords, source, and sentiment
- **📈 Analytics Page**: Interactive visualizations of sentiment distribution, source breakdown, and top topics
- **ℹ️ About Page**: Project information and technical details

## Deployment

This app can be deployed to:
- Azure App Service
- Azure Static Web Apps + Azure Functions
- Streamlit Community Cloud
- Other cloud platforms supporting Python web apps

## Structure

```
streamlit_app/
├── app.py                    # Main application file
├── .streamlit/
│   └── config.toml          # Streamlit configuration
└── README.md                # This file
```
