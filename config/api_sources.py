API_SOURCES = {
    'guardian': {
        'url': 'https://content.guardianapis.com/search',
        'params': {
            'q': '"generative AI" OR "large language model" OR "AI assistant" OR Copilot OR ChatGPT OR "AI ethics"',
            'show-fields': 'body'
        }
    },
    'hacker_news': {
        'url': 'https://hacker-news.firebaseio.com/v0/topstories.json'
    }
}