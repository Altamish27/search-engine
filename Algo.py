import requests
from bs4 import BeautifulSoup
from collections import deque
import time
import urllib3
import shelve  # Tambahan untuk file-based caching
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# In-memory cache
page_cache = {}

# Fungsi untuk membersihkan HTML dan mengembalikan teks bersih
def get_clean_text_from_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

# Fungsi caching dan pembersihan
def get_cached_page_text(url, use_english):
    if use_english:
        url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")

    # Cek di cache RAM
    if url in page_cache:
        return page_cache[url]

    # Cek di file cache
    with shelve.open("page_cache.db") as file_cache:
        if url in file_cache:
            print(f"[CACHE-HIT] {url} (from file)")
            page_cache[url] = file_cache[url]
            return file_cache[url]

    # Fetch dari internet kalau belum ada di cache
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            clean_text = get_clean_text_from_html(response.content)
            page_cache[url] = clean_text
            with shelve.open("page_cache.db") as file_cache:
                file_cache[url] = clean_text
            print(f"[CACHE-STORE] {url}")
            return clean_text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

    return ""

# Fungsi untuk pencocokan keyword menggunakan cosine similarity
def search_keyword_in_page(url, keyword, use_english):
    if not keyword.strip():
        return False
    page_text = get_cached_page_text(url, use_english)
    if not page_text:
        return False
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform([page_text, keyword])
    similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
    print(f"[{url}] Cosine similarity: {similarity[0][0]:.4f}")
    return similarity[0][0] > 0.01  # Ambang batas diturunkan agar lebih sensitif

# Fungsi untuk mendapatkan semua link href dari halaman
def get_links(url, use_english):
    links = []
    try:
        if use_english:
            url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True) if 'ui.ac.id' in a['href']]
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    return links

# BFS Web Crawler
def bfs(start_url, max_depth, keyword="", use_english=False, progress_callback=None):
    visited = set()
    queue = deque([(start_url, 0, [])])
    all_links = set()
    keyword_found_urls = set()
    search_log = []
    path_info = {}
    visited_count = 0

    while queue:
        current_url, depth, path = queue.popleft()
        if max_depth != -1 and depth > max_depth:
            continue
        if current_url not in visited:
            visited.add(current_url)
            visited_count += 1
            log_entry = f"Visiting (Depth {depth}): {current_url}"
            search_log.append(log_entry)
            print(log_entry)

            if progress_callback:
                progress_callback({
                    'status': 'searching',
                    'url': current_url,
                    'depth': depth,
                    'visited_count': visited_count,
                    'log': log_entry
                })

            if keyword and search_keyword_in_page(current_url, keyword, use_english):
                log_entry = f"Keyword found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                path_with_current = path + [current_url]
                path_info[current_url] = path_with_current
                path_log = f"Path to the keyword: {' -> '.join(path_with_current)}"
                search_log.append(path_log)
                print(path_log)

                if progress_callback:
                    progress_callback({
                        'status': 'found',
                        'url': current_url,
                        'path': path_with_current,
                        'log': log_entry
                    })

            links = get_links(current_url, use_english)
            all_links.update(links)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1, path + [current_url]))
            time.sleep(0.2)

    if progress_callback:
        progress_callback({
            'status': 'complete',
            'visited_count': visited_count,
            'all_links_count': len(all_links),
            'keyword_found_count': len(keyword_found_urls)
        })

    return all_links, keyword_found_urls, search_log, path_info

# DFS Web Crawler
def dfs(start_url, max_depth, keyword="", use_english=False, progress_callback=None):
    visited = set()
    stack = [(start_url, 0, [])]
    all_links = set()
    keyword_found_urls = set()
    search_log = []
    path_info = {}
    visited_count = 0

    while stack:
        current_url, depth, path = stack.pop()
        if max_depth != -1 and depth > max_depth:
            continue
        if current_url not in visited:
            visited.add(current_url)
            visited_count += 1
            log_entry = f"Visiting (Depth {depth}): {current_url}"
            search_log.append(log_entry)
            print(log_entry)

            if progress_callback:
                progress_callback({
                    'status': 'searching',
                    'url': current_url,
                    'depth': depth,
                    'visited_count': visited_count,
                    'log': log_entry
                })

            if keyword and search_keyword_in_page(current_url, keyword, use_english):
                log_entry = f"Keyword found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                path_with_current = path + [current_url]
                path_info[current_url] = path_with_current
                path_log = f"Path to the keyword: {' -> '.join(path_with_current)}"
                search_log.append(path_log)
                print(path_log)

                if progress_callback:
                    progress_callback({
                        'status': 'found',
                        'url': current_url,
                        'path': path_with_current,
                        'log': log_entry
                    })

            links = get_links(current_url, use_english)
            all_links.update(links)
            for link in reversed(links):
                if link not in visited:
                    stack.append((link, depth + 1, path + [current_url]))
            time.sleep(0.2)

    if progress_callback:
        progress_callback({
            'status': 'complete',
            'visited_count': visited_count,
            'all_links_count': len(all_links),
            'keyword_found_count': len(keyword_found_urls)
        })

    return all_links, keyword_found_urls, search_log, path_info

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    start_url = data.get('start_url', 'https://www.ui.ac.id')
    max_depth = int(data.get('max_depth', -1))
    keyword = data.get('keyword', '')
    use_english = data.get('use_english', False)
    algorithm = data.get('algorithm', 'bfs')

    if algorithm.lower() == 'dfs':
        all_links, keyword_found_urls, search_log, path_info = dfs(
            start_url, max_depth, keyword, use_english)
    else:
        all_links, keyword_found_urls, search_log, path_info = bfs(
            start_url, max_depth, keyword, use_english)

    return jsonify({
        'all_links': list(all_links),
        'keyword_found_urls': list(keyword_found_urls),
        'search_log': search_log,
        'path_info': path_info,
        'algorithm': algorithm
    })

if __name__ == '__main__':
    app.run(debug=True)