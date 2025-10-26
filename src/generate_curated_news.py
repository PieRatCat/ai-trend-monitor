"""
Generate Curated News Content
Runs after pipeline to create curated news sections and save to Azure Blob Storage
"""
import os
import sys
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag_chatbot import RAGChatbot

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_curated_content(section_type, chatbot):
    """Generate curated content using RAG chatbot"""
    logging.info(f"Generating curated content for: {section_type}")
    
    ai_search_override = "GPT ChatGPT Claude LLM model OpenAI Anthropic machine learning neural network deep learning generative AI"
    
    if section_type == "products":
        query = """What are the most recent AI SOFTWARE and MODEL developments mentioned in the articles?

STRICT RULES - Only include if it's about:
- AI models (GPT-5, Claude 4, Gemini updates, new LLMs, model releases)
- AI/ML software tools (ChatGPT features, API updates, ML libraries, frameworks)
- Generative AI applications (image/video/audio generation tools)
- AI development platforms (ML platforms, AI SDKs, developer tools)
- AI model capabilities (new features, performance improvements, fine-tuning)

DO NOT include:
- General business news or company announcements without product details
- AI hardware or chips (save for industry section)
- Funding or investment news without product specifics
- Regulatory or policy news
- Generic tech products

List 5 SOFTWARE/MODEL items in this format:
<li><strong>Product/Model Name:</strong> Brief description of the software or model update</li>

Focus on practical AI tools and models that developers and practitioners use."""
    else:  # industry
        query = """What are the most recent AI INDUSTRY developments mentioned in the articles?

STRICT RULES - Only include if it's about:
- AI company news (OpenAI, Anthropic, Google AI, DeepMind, etc.)
- AI startup funding, acquisitions, or launches
- AI research breakthroughs or academic papers
- AI regulation, policy, or ethics discussions
- AI chip/hardware manufacturers (NVIDIA, AMD, specialized AI chips)
- Major AI partnerships or collaborations

DO NOT include:
- Specific software or model releases (save for products section)
- General tech news unrelated to AI
- Consumer electronics or vehicles
- Business news from non-AI companies

List 5 INDUSTRY items in this format:
<li><strong>Company/Topic:</strong> Brief description of the industry development</li>

Focus on the AI ecosystem: who's doing what, funding, regulations, and research."""
    
    result = chatbot.chat(query, top_k=15, temperature=0.5, search_override=ai_search_override)
    answer = result["answer"]
    
    # Clean up response
    unwanted_phrases = [
        "Based on the provided articles,",
        "here are 5", "here are five", "Here are 5", "Here are five",
        "Based on the articles,", "According to the articles,",
        "```html", "```"
    ]
    for phrase in unwanted_phrases:
        answer = answer.replace(phrase, "")
    
    # Remove citations
    answer = re.sub(r'\s*\[\d+\](\[\d+\])*', '', answer)
    
    # Convert markdown lists to HTML
    lines = answer.strip().split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            if line.startswith('-') or line.startswith('*'):
                line = line[1:].strip()
                if not line.startswith('<li>'):
                    line = f'<li>{line}</li>'
            cleaned_lines.append(line)
    
    answer = '\n'.join(cleaned_lines)
    
    # Wrap in <ul> tags
    if '<li>' in answer and not answer.strip().startswith('<ul>'):
        answer = f'<ul style="margin-top: 0.5rem; color: #2D2D2D;">\n{answer}\n</ul>'
    
    return answer.strip()

def save_to_blob(section_type, content):
    """Save generated content to Azure Blob Storage"""
    try:
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            logging.error("AZURE_STORAGE_CONNECTION_STRING not found")
            return False
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "curated-content"
        
        # Ensure container exists
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_client.create_container()
            logging.info(f"Created container: {container_name}")
        except Exception as e:
            if "ContainerAlreadyExists" not in str(e):
                logging.warning(f"Container creation: {e}")
        
        # Save content with timestamp
        blob_name = f"curated_{section_type}.json"
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        
        data = {
            'content': content,
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'timestamp': datetime.now().isoformat(),
            'section_type': section_type
        }
        
        blob_client.upload_blob(json.dumps(data, indent=2), overwrite=True)
        logging.info(f"Saved {section_type} content to blob: {blob_name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to save to blob: {e}")
        return False

def main():
    """Generate and save curated news content"""
    logging.info("Starting curated news generation...")
    
    try:
        # Initialize chatbot
        chatbot = RAGChatbot()
        logging.info("RAG Chatbot initialized")
        
        # Generate products section
        products_content = generate_curated_content("products", chatbot)
        if products_content:
            save_to_blob("products", products_content)
            logging.info("✓ Products section generated and saved")
        else:
            logging.warning("Failed to generate products content")
        
        # Generate industry section
        industry_content = generate_curated_content("industry", chatbot)
        if industry_content:
            save_to_blob("industry", industry_content)
            logging.info("✓ Industry section generated and saved")
        else:
            logging.warning("Failed to generate industry content")
        
        logging.info("Curated news generation complete!")
        
    except Exception as e:
        logging.error(f"Failed to generate curated news: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
