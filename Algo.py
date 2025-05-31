import requests
from bs4 import BeautifulSoup
from collections import deque
import time
import json
import os
import urllib3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# File untuk menyimpan cache JSON
CACHE_FILE = "crawl_cache.json"

class WebCrawlerCache:
    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self.cache_data = self.load_cache()
        
    def load_cache(self):
        """Load cache dari file JSON"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {"urls": {}, "metadata": {}}
        return {"urls": {}, "metadata": {}}
    
    def save_cache(self):
        """Simpan cache ke file JSON"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            print(f"[CACHE-SAVED] Cache saved to {self.cache_file}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def get_cached_content(self, url):
        """Ambil konten dari cache"""
        return self.cache_data["urls"].get(url)
    
    def store_content(self, url, content, title=""):
        """Simpan konten ke cache"""
        self.cache_data["urls"][url] = {
            "content": content,
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content)
        }
    
    def get_cache_stats(self):
        """Dapatkan statistik cache"""
        cache_size = 0
        if os.path.exists(self.cache_file):
            cache_size = os.path.getsize(self.cache_file) / 1024 / 1024  # MB
        
        return {
            "total_urls": len(self.cache_data["urls"]),
            "cache_size_mb": round(cache_size, 2),
            "last_updated": self.cache_data.get("metadata", {}).get("last_updated", "Never")
        }
    
    def update_metadata(self, start_url, algorithm, max_depth):
        """Update metadata cache"""
        self.cache_data["metadata"] = {
            "last_updated": datetime.now().isoformat(),
            "start_url": start_url,
            "algorithm": algorithm,
            "max_depth": max_depth,
            "total_urls": len(self.cache_data["urls"])
        }
    
    def clear_cache(self):
        """Hapus semua cache"""
        self.cache_data = {"urls": {}, "metadata": {}}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        print("[CACHE-CLEARED] All cache data cleared")

# Initialize cache manager
cache_manager = WebCrawlerCache()

# Fungsi untuk membersihkan HTML dan mengembalikan teks bersih
def get_clean_text_from_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

# Fungsi caching dan pembersihan dengan opsi fresh/cached mode
def get_page_content(url, use_english, use_cache=True):
    """Ambil konten halaman dengan opsi cache"""
    if use_english:
        url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")
    
    # Jika menggunakan cache, cek dulu di cache
    if use_cache:
        cached = cache_manager.get_cached_content(url)
        if cached:
            print(f"[CACHE-HIT] {url}")
            return cached["content"], cached["title"]
    
    # Fetch dari internet (fresh mode atau cache miss)
    try:
        print(f"[FETCHING] {url}")
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else ""
            clean_text = get_clean_text_from_html(response.content)
            
            # Simpan ke cache untuk penggunaan selanjutnya
            cache_manager.store_content(url, clean_text, title)
            return clean_text, title
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    
    return "", ""

# Fungsi untuk pencocokan keyword menggunakan cosine similarity dengan memoization
def search_keyword_in_page(url, keyword, use_english, use_cache=True):
    """Cari keyword di halaman dengan memoization"""
    if not keyword.strip():
        return False
    
    content, title = get_page_content(url, use_english, use_cache)
    if not content:
        return False
    
    # Gunakan TF-IDF untuk pencarian yang lebih akurat
    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([content, keyword])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        similarity_score = similarity[0][0]
        print(f"[{url}] Cosine similarity: {similarity_score:.4f}")
        return similarity_score > 0.01  # Ambang batas diturunkan agar lebih sensitif
    except:
        # Fallback ke pencarian sederhana jika TF-IDF gagal
        return keyword.lower() in content.lower()

# Fungsi untuk mendapatkan semua link href dari halaman dengan opsi cache
def get_links(url, use_english, use_cache=True):
    """Ambil semua link dari halaman"""
    links = []
    try:
        if use_english:
            url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")
        
        # Jika menggunakan cache, ambil konten dari cache dulu
        if use_cache:
            cached = cache_manager.get_cached_content(url)
            if cached:
                # Parse links dari cached content
                # Karena cached content sudah berupa text, kita perlu fetch ulang untuk parsing HTML
                # Atau kita bisa simpan links terpisah di cache (implementasi lebih lanjut)
                pass
        
        # Fetch dari internet untuk mendapatkan links
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True) if 'ui.ac.id' in a['href']]
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    return links

# BFS Web Crawler dengan opsi cache
def bfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    """BFS dengan opsi cache untuk optimasi performa"""
    visited = set()
    queue = deque([(start_url, 0, [])])
    all_links = set()
    keyword_found_urls = set()
    search_log = []
    path_info = {}
    visited_count = 0

    cache_mode = "[CACHE MODE]" if use_cache else "[FRESH MODE]"
    search_log.append(f"{cache_mode} Starting BFS crawling from {start_url}")

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
                    'log': log_entry,
                    'cache_mode': use_cache
                })

            if keyword and search_keyword_in_page(current_url, keyword, use_english, use_cache):
                log_entry = f"Keyword '{keyword}' found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                path_with_current = path + [current_url]
                path_info[current_url] = path_with_current
                path_log = f"Path to keyword: {' -> '.join(path_with_current)}"
                search_log.append(path_log)
                print(path_log)

                if progress_callback:
                    progress_callback({
                        'status': 'found',
                        'url': current_url,
                        'path': path_with_current,
                        'log': log_entry
                    })

            links = get_links(current_url, use_english, use_cache)
            all_links.update(links)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1, path + [current_url]))
            time.sleep(0.1 if use_cache else 0.2)  # Lebih cepat jika pakai cache

    # Simpan cache setelah crawling selesai jika mode fresh
    if not use_cache:
        cache_manager.update_metadata(start_url, "bfs", max_depth)
        cache_manager.save_cache()

    if progress_callback:
        progress_callback({
            'status': 'complete',
            'visited_count': visited_count,
            'all_links_count': len(all_links),
            'keyword_found_count': len(keyword_found_urls)
        })

    return all_links, keyword_found_urls, search_log, path_info

# DFS Web Crawler dengan opsi cache
def dfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    """DFS dengan opsi cache untuk optimasi performa"""
    visited = set()
    stack = [(start_url, 0, [])]
    all_links = set()
    keyword_found_urls = set()
    search_log = []
    path_info = {}
    visited_count = 0

    cache_mode = "[CACHE MODE]" if use_cache else "[FRESH MODE]"
    search_log.append(f"{cache_mode} Starting DFS crawling from {start_url}")

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
                    'log': log_entry,
                    'cache_mode': use_cache
                })

            if keyword and search_keyword_in_page(current_url, keyword, use_english, use_cache):
                log_entry = f"Keyword '{keyword}' found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                path_with_current = path + [current_url]
                path_info[current_url] = path_with_current
                path_log = f"Path to keyword: {' -> '.join(path_with_current)}"
                search_log.append(path_log)
                print(path_log)

                if progress_callback:
                    progress_callback({
                        'status': 'found',
                        'url': current_url,
                        'path': path_with_current,
                        'log': log_entry
                    })

            links = get_links(current_url, use_english, use_cache)
            all_links.update(links)
            for link in reversed(links):
                if link not in visited:
                    stack.append((link, depth + 1, path + [current_url]))
            time.sleep(0.1 if use_cache else 0.2)  # Lebih cepat jika pakai cache

    # Simpan cache setelah crawling selesai jika mode fresh
    if not use_cache:
        cache_manager.update_metadata(start_url, "dfs", max_depth)
        cache_manager.save_cache()

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

@app.route('/cache-stats')
def cache_stats():
    """Endpoint untuk mendapatkan statistik cache"""
    return jsonify(cache_manager.get_cache_stats())

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Endpoint untuk menghapus cache"""
    cache_manager.clear_cache()
    return jsonify({"message": "Cache cleared successfully", "stats": cache_manager.get_cache_stats()})

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    start_url = data.get('start_url', 'https://www.ui.ac.id')
    max_depth = int(data.get('max_depth', -1))
    keyword = data.get('keyword', '')
    use_english = data.get('use_english', False)
    algorithm = data.get('algorithm', 'bfs')
    use_cache = data.get('use_cache', True)  # Parameter baru untuk mode cache

    # Pilih algoritma yang akan digunakan
    if algorithm.lower() == 'dfs':
        all_links, keyword_found_urls, search_log, path_info = dfs(
            start_url, max_depth, keyword, use_english, use_cache)
    else:
        all_links, keyword_found_urls, search_log, path_info = bfs(
            start_url, max_depth, keyword, use_english, use_cache)

    return jsonify({
        'all_links': list(all_links),
        'keyword_found_urls': list(keyword_found_urls),
        'search_log': search_log,
        'path_info': path_info,
        'algorithm': algorithm,
        'cache_used': use_cache,
        'cache_stats': cache_manager.get_cache_stats()
    })

if __name__ == '__main__':
    app.run(debug=True)