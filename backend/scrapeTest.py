from scrapling import Fetcher
import threading
import os
import requests
import dotenv
from scrapingbee import ScrapingBeeClient
import time


dotenv.load_dotenv()

fetcher = Fetcher(auto_match=False)

def search(query, searching_logo_callback):

    start_time = time.time()

    search_url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.getenv("GOOGLE_SEARCH_API_KEY"), 
        "cx": os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID"),
        "q": query,
    }

    response = requests.get(search_url, params=params)
    search_output = f"Query: {query}\n\n"
    if response.status_code == 200:
        search_results = response.json()

        # print("SEARCH RESULTS: ", search_results)

        # Extract URLs and logos from search results
        urls = []
        for item in search_results.get('items', [])[:5]:
            url = item.get('link')
            urls.append(url)

            domainURL = (url.split('/')[2])
            logo = f"https://www.google.com/s2/favicons?sz=64&domain_url={domainURL}"
            if searching_logo_callback:
                searching_logo_callback(logo)
            
        print("URLS: ", urls)
        
        # Start of Selection
        # Create list to store threads
        threads = []
        # Dictionary to store results from each thread
        results = {}
        
        def fetch_url(url):
            try:
                page = fetcher.get(url)
                # Extract main content from the page using a specific selector
                main_content = page.css_first('main')  # Adjust the selector based on the website's structure
                if main_content:
                    text = main_content.get_all_text(ignore_tags=('script', 'style'))
                else:
                    # Fallback to extracting all text if main content is not found
                    text = page.get_all_text(ignore_tags=('script', 'style'))
                results[url] = text
            except Exception as e:
                print(f"Error fetching {url}: {str(e)}")
                results[url] = None
        
        # Start all threads
        for url in urls:
            thread = threading.Thread(target=fetch_url, args=(url,))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Add results to search output
        for url in urls:
            text = results.get(url, "Error fetching page")
            search_output += f"""
            URL: {url}
            CONTENT:
            {text}
            """
    else:
        print(f"Failed to retrieve search results, status code: {response.status_code}")

    end_time = time.time()
    print(f"Total time: {end_time - start_time}")

    return search_output