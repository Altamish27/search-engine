import requests
from bs4 import BeautifulSoup
from collections import deque
import time
import json
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# File untuk menyimpan cache
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
            print(f"Cache saved to {self.cache_file}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def get_cached_content(self, url):
        """Ambil konten dari cache"""
        return self.cache_data["urls"].get(url)
    
    def store_content(self, url, content, title="", links=None):
        """Simpan konten ke cache"""
        self.cache_data["urls"][url] = {
            "content": content,
            "title": title,
            "links": links or [],
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content)
        }
    
    def get_cache_stats(self):
        """Dapatkan statistik cache"""
        return {
            "total_urls": len(self.cache_data["urls"]),
            "cache_size_mb": os.path.getsize(self.cache_file) / 1024 / 1024 if os.path.exists(self.cache_file) else 0,
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

# Initialize cache
cache_manager = WebCrawlerCache()

def get_clean_text_from_html(content):
    """Bersihkan HTML dan kembalikan teks bersih"""
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def get_page_content(url, use_english, use_cache=True):
    """Ambil konten halaman dengan opsi cache"""
    if use_english:
        url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")
    
    # Jika menggunakan cache, cek dulu di cache
    if use_cache:
        cached = cache_manager.get_cached_content(url)
        if cached:
            print(f"[CACHE-HIT] {url}")
            return cached["content"], cached["title"], cached.get("links", [])
    
    # Fetch dari internet
    try:
        print(f"[FETCHING] {url}")
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else ""
            clean_text = get_clean_text_from_html(response.content)
            
            # Extract links
            links = [a['href'] for a in soup.find_all('a', href=True) if 'ui.ac.id' in a['href']]
            
            # Simpan ke cache
            cache_manager.store_content(url, clean_text, title, links)
            return clean_text, title, links
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    
    return "", "", []

# Fungsi untuk mendapatkan semua link href dari halaman
def get_links(url, use_english, use_cache=True):
    """Ambil semua link dari halaman dengan opsi cache"""
    if use_english:
        url = url.replace("https://www.ui.ac.id", "https://www.ui.ac.id/en")
    
    # Jika menggunakan cache, cek dulu di cache
    if use_cache:
        cached = cache_manager.get_cached_content(url)
        if cached and "links" in cached:
            print(f"[CACHE-HIT-LINKS] {url}")
            return cached["links"]
    
    # Fetch dari internet
    try:
        print(f"[FETCHING-LINKS] {url}")
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True) if 'ui.ac.id' in a['href']]
            
            # Jika belum ada content di cache, simpan sekalian
            if not cache_manager.get_cached_content(url):
                title = soup.title.string if soup.title else ""
                clean_text = get_clean_text_from_html(response.content)
                cache_manager.store_content(url, clean_text, title, links)
            
            return links
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    return []

# Fungsi untuk mencari kata kunci di halaman dengan memoization
def search_keyword_in_page(url, keyword, use_english, use_cache=True):
    """Cari keyword di halaman dengan memoization dan TF-IDF"""
    if not keyword.strip():
        return False
    
    content, title, links = get_page_content(url, use_english, use_cache)
    if not content:
        return False
    
    # Gunakan TF-IDF untuk pencarian yang lebih akurat
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([content, keyword])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        similarity_score = similarity[0][0]
        print(f"[{url}] TF-IDF similarity: {similarity_score:.4f}")
        return similarity_score > 0.01
    except:
        # Fallback ke pencarian sederhana
        return keyword.lower() in content.lower()

# Fungsi BFS untuk menemukan semua link dengan batas kedalaman
def bfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    """BFS dengan opsi cache dan memoization"""
    visited = set()  # Set untuk menyimpan URL yang sudah dikunjungi
    queue = deque([(start_url, 0, [])])  # Antrian untuk BFS (URL, kedalaman, path yang dilalui)
    all_links = set()  # Set untuk menyimpan semua link yang ditemukan
    keyword_found_urls = set()  # Set untuk menyimpan URL yang mengandung kata kunci
    search_log = []  # Untuk menyimpan log pencarian
    path_info = {}  # Dictionary untuk menyimpan informasi path setiap URL yang mengandung kata kunci

    visited_count = 0
    
    cache_mode = "[CACHE MODE]" if use_cache else "[FRESH MODE]"
    search_log.append(f"{cache_mode} Starting BFS crawling from {start_url}")
    
    while queue:
        current_url, depth, path = queue.popleft()
        
        # Jika max_depth adalah -1, berarti kedalaman tidak terbatas
        if max_depth != -1 and depth > max_depth:
            continue
        
        if current_url not in visited:
            visited.add(current_url)
            visited_count += 1
            log_entry = f"Visiting (Depth {depth}): {current_url}"
            search_log.append(log_entry)
            print(log_entry)
            
            # Update progress jika callback diberikan
            if progress_callback:
                progress_callback({
                    'status': 'searching',
                    'url': current_url,
                    'depth': depth,
                    'visited_count': visited_count,
                    'log': log_entry,
                    'cache_mode': use_cache
                })
            
            # Mencari kata kunci di halaman
            if keyword and search_keyword_in_page(current_url, keyword, use_english, use_cache):
                log_entry = f"Keyword '{keyword}' found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                # Simpan path menuju URL yang mengandung kata kunci
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

            links = get_links(current_url, use_english, use_cache)  # Mendapatkan semua link dari halaman
            all_links.update(links)  # Menambahkan link baru ke set all_links
            
            # Tambahkan link yang belum dikunjungi ke dalam antrian
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1, path + [current_url]))

            # Agar tidak terlalu cepat mengirim permintaan - lebih cepat jika pakai cache
            time.sleep(0.1 if use_cache else 0.2)

    # Simpan cache setelah crawling selesai (hanya jika mode fresh)
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

# Fungsi DFS untuk menemukan semua link dengan batas kedalaman
def dfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    """DFS dengan opsi cache dan memoization"""
    visited = set()  # Set untuk menyimpan URL yang sudah dikunjungi
    stack = [(start_url, 0, [])]  # Stack untuk DFS (URL, kedalaman, path yang dilalui)
    all_links = set()  # Set untuk menyimpan semua link yang ditemukan
    keyword_found_urls = set()  # Set untuk menyimpan URL yang mengandung kata kunci
    search_log = []  # Untuk menyimpan log pencarian
    path_info = {}  # Dictionary untuk menyimpan informasi path setiap URL yang mengandung kata kunci

    visited_count = 0
    
    cache_mode = "[CACHE MODE]" if use_cache else "[FRESH MODE]"
    search_log.append(f"{cache_mode} Starting DFS crawling from {start_url}")
    
    while stack:
        current_url, depth, path = stack.pop()  # Pop dari atas stack (LIFO)
        
        # Jika max_depth adalah -1, berarti kedalaman tidak terbatas
        if max_depth != -1 and depth > max_depth:
            continue
        
        if current_url not in visited:
            visited.add(current_url)
            visited_count += 1
            log_entry = f"Visiting (Depth {depth}): {current_url}"
            search_log.append(log_entry)
            print(log_entry)
            
            # Update progress jika callback diberikan
            if progress_callback:
                progress_callback({
                    'status': 'searching',
                    'url': current_url,
                    'depth': depth,
                    'visited_count': visited_count,
                    'log': log_entry,
                    'cache_mode': use_cache
                })
            
            # Mencari kata kunci di halaman
            if keyword and search_keyword_in_page(current_url, keyword, use_english, use_cache):
                log_entry = f"Keyword '{keyword}' found at: {current_url}"
                search_log.append(log_entry)
                print(log_entry)
                keyword_found_urls.add(current_url)
                # Simpan path menuju URL yang mengandung kata kunci
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

            links = get_links(current_url, use_english, use_cache)  # Mendapatkan semua link dari halaman
            all_links.update(links)  # Menambahkan link baru ke set all_links
            
            # Tambahkan link yang belum dikunjungi ke dalam stack (urutan terbalik agar traversal DFS benar)
            for link in reversed(links):
                if link not in visited:
                    stack.append((link, depth + 1, path + [current_url]))

            # Agar tidak terlalu cepat mengirim permintaan - lebih cepat jika pakai cache
            time.sleep(0.1 if use_cache else 0.2)

    # Simpan cache setelah crawling selesai (hanya jika mode fresh)
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
    return jsonify({"status": "success", "message": "Cache cleared successfully"})

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    start_url = data.get('start_url', 'https://www.ui.ac.id')
    max_depth = int(data.get('max_depth', -1))
    keyword = data.get('keyword', '')
    use_english = data.get('use_english', False)
    algorithm = data.get('algorithm', 'bfs')  # Default to BFS if not specified
    use_cache = data.get('use_cache', True)  # Parameter baru untuk cache mode
    
    # Pilih algoritma yang akan digunakan
    if algorithm.lower() == 'dfs':
        all_links, keyword_found_urls, search_log, path_info = dfs(
            start_url, 
            max_depth, 
            keyword, 
            use_english,
            use_cache
        )
    else:
        all_links, keyword_found_urls, search_log, path_info = bfs(
            start_url, 
            max_depth, 
            keyword, 
            use_english,
            use_cache
        )
    
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
