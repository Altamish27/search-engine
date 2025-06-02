# Web Crawler Search Engine

## Deskripsi Proyek

Web Crawler Search Engine adalah aplikasi web yang mengimplementasikan algoritma pencarian graph traversal (BFS dan DFS) untuk menjelajahi dan mengindeks halaman web. Aplikasi ini dirancang khusus untuk menjelajahi website Universitas Indonesia (UI) dengan kemampuan pencarian kata kunci menggunakan teknologi TF-IDF dan cosine similarity.

## Fitur Utama

### 1. Algoritma Pencarian
- **Breadth-First Search (BFS)**: Menjelajahi web secara level-by-level
- **Depth-First Search (DFS)**: Menjelajahi web secara mendalam terlebih dahulu
- **Kontrol Kedalaman**: Dapat membatasi kedalaman pencarian untuk menghindari infinite crawling

### 2. Sistem Caching Cerdas
- **Cache Mode**: Menggunakan data yang telah di-cache untuk performa optimal
- **Fresh Mode**: Mengambil data langsung dari internet dengan auto-save ke cache
- **Cache Management**: Fitur untuk melihat statistik dan menghapus cache

### 3. Pencarian Kata Kunci
- **TF-IDF (Term Frequency-Inverse Document Frequency)**: Algoritma advanced untuk relevansi teks
- **Cosine Similarity**: Mengukur kesamaan antara dokumen dan query
- **Fallback Mechanism**: Pencarian sederhana jika TF-IDF gagal

### 4. Interface Web Responsif
- **Real-time Progress**: Menampilkan progress crawling secara real-time
- **Hasil Terorganisir**: Tab-based interface untuk log, hasil pencarian, dan semua link
- **Cache Statistics**: Dashboard untuk monitoring cache

## Arsitektur Sistem

### Struktur Direktori
```
search-engine/
├── app.py                 # Aplikasi utama Flask
├── Algo.py               # File backup/alternative implementation
├── requirements.txt      # Dependencies Python
├── crawl_cache.json     # File cache (auto-generated)
├── templates/
│   └── index.html       # Frontend interface
└── static/
    └── css/
        └── style.css    # Custom styling
```

### Komponen Utama

#### 1. WebCrawlerCache Class
Mengelola sistem caching dengan fitur:
- Load/save cache dari/ke file JSON
- Auto-save periodik untuk mengurangi I/O overhead
- Statistik cache (jumlah URL, ukuran file, waktu update)
- Metadata tracking (algoritma, kedalaman, URL awal)

#### 2. Graph Traversal Algorithms

**BFS Implementation:**
```python
def bfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    visited = set()
    queue = deque([(start_url, 0, [])])
    # ... implementasi BFS
```

**DFS Implementation:**
```python
def dfs(start_url, max_depth, keyword="", use_english=False, use_cache=True, progress_callback=None):
    visited = set()
    stack = [(start_url, 0, [])]
    # ... implementasi DFS
```

#### 3. Text Processing Pipeline
- **HTML Cleaning**: Menghilangkan tag script, style, header, footer, nav
- **TF-IDF Vectorization**: Menggunakan scikit-learn TfidfVectorizer
- **Similarity Calculation**: Cosine similarity untuk relevansi

## Analisis Kompleksitas

### 1. Kompleksitas Waktu (Time Complexity)

#### BFS Algorithm
- **Worst Case**: O(V + E)
  - V = jumlah vertices (halaman web)
  - E = jumlah edges (links antar halaman)
- **Best Case**: O(1) jika target ditemukan di root
- **Average Case**: O(V + E)

**Penjelasan**:
- Setiap vertex (URL) dikunjungi tepat sekali: O(V)
- Setiap edge (link) dieksplorasi tepat sekali: O(E)
- Total: O(V + E)

#### DFS Algorithm
- **Worst Case**: O(V + E)
- **Best Case**: O(1) jika target ditemukan di root
- **Average Case**: O(V + E)

**Penjelasan**:
- Sama dengan BFS, setiap node dan edge dikunjungi tepat sekali
- Perbedaan hanya pada urutan kunjungan, bukan kompleksitas

#### Text Processing (TF-IDF)
- **Per Document**: O(n × m)
  - n = jumlah kata dalam dokumen
  - m = ukuran vocabulary
- **Cosine Similarity**: O(m) untuk setiap perbandingan

### 2. Kompleksitas Ruang (Space Complexity)

#### BFS Algorithm
- **Visited Set**: O(V) - menyimpan semua URL yang dikunjungi
- **Queue**: O(w) - w adalah width maksimum tree (branching factor)
- **Cache Storage**: O(V × D) - D adalah rata-rata ukuran dokumen
- **Total**: O(V × D)

#### DFS Algorithm
- **Visited Set**: O(V)
- **Stack**: O(h) - h adalah height maksimum tree (max_depth)
- **Cache Storage**: O(V × D)
- **Total**: O(V × D)

**Keunggulan DFS**: Menggunakan ruang stack yang lebih efisien O(h) vs O(w)

#### Sistem Caching
- **Memory Usage**: O(V × D)
- **Disk Usage**: O(V × D) - persistent storage dalam JSON
- **Metadata**: O(V) - informasi tambahan per URL

### 3. Optimasi Performa

#### Cache Hit Ratio
- **Cache Hit**: O(1) - langsung mengambil dari memory/disk
- **Cache Miss**: O(T) - T adalah waktu network request dan processing
- **Speedup Factor**: Hingga 100x lebih cepat dengan cache hit

#### Rate Limiting
- **Sleep Time**: 0.1s (cache mode) vs 0.2s (fresh mode)
- **Purpose**: Menghindari overload server target
- **Trade-off**: Kecepatan vs politeness

### 4. Kompleksitas dalam Konteks Web Crawling

#### Network Factors
- **Latency**: Rata-rata 100-500ms per request
- **Bandwidth**: Tergantung ukuran halaman (KB-MB)
- **Reliability**: Potential timeouts dan errors

#### Scalability Analysis
Untuk website UI (universitas-indonesia.ac.id):
- **Estimated Pages**: ~10,000-50,000 halaman
- **Max Depth 3**: ~1,000-5,000 halaman tercakup
- **Memory Usage**: ~100MB-1GB tergantung cache
- **Processing Time**: 
  - Fresh Mode: 5-10 menit untuk depth 3
  - Cache Mode: 30 detik - 2 menit

## Instalasi dan Penggunaan

### Prerequisites
- Python 3.7+
- pip package manager

### Langkah Instalasi

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd search-engine
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan Aplikasi**
   ```bash
   python app.py
   ```

4. **Akses Web Interface**
   Buka browser dan kunjungi: `http://localhost:5000`

### Cara Penggunaan

1. **Set Parameter Pencarian**:
   - **Start URL**: URL awal untuk memulai crawling (default: https://www.ui.ac.id)
   - **Keyword**: Kata kunci yang dicari (opsional)
   - **Max Depth**: Kedalaman maksimum crawling (-1 untuk unlimited)
   - **Algorithm**: Pilih BFS atau DFS
   - **Use Cache**: Toggle cache mode vs fresh mode
   - **English Version**: Crawl versi English dari website

2. **Monitor Progress**:
   - Real-time log menampilkan URL yang sedang dikunjungi
   - Progress counter menunjukkan jumlah halaman yang telah di-crawl
   - Status indicator menampilkan mode cache yang digunakan

3. **Analisis Hasil**:
   - **Search Log**: Riwayat lengkap proses crawling
   - **Found URLs**: Halaman yang mengandung keyword
   - **All Links**: Semua link yang ditemukan
   - **Path Visualization**: Jalur menuju halaman dengan keyword

## Dependencies

### Core Libraries
- **Flask 2.3.3**: Web framework untuk interface
- **requests 2.31.0**: HTTP client untuk web crawling
- **beautifulsoup4 4.12.2**: HTML parsing dan cleaning
- **scikit-learn 1.3.0**: TF-IDF dan machine learning utilities
- **urllib3 2.0.4**: Low-level HTTP utilities

### Standard Libraries
- **collections.deque**: Implementasi queue efisien untuk BFS
- **json**: Serialisasi data cache
- **datetime**: Timestamp dan metadata
- **os**: File system operations
- **time**: Rate limiting dan delays

## Fitur Advanced

### 1. Smart Caching System
- **Auto-save**: Cache disimpan otomatis setiap 5 URL dalam fresh mode
- **Metadata Tracking**: Simpan informasi algoritma, depth, dan timestamp
- **Cache Statistics**: Real-time monitoring ukuran dan performa cache

### 2. Error Handling
- **Network Timeouts**: 10 detik timeout untuk setiap request
- **SSL Verification**: Disabled untuk menghindari certificate issues
- **Exception Recovery**: Graceful handling untuk failed requests

### 3. Progress Monitoring
- **Real-time Updates**: Live progress callback untuk UI
- **Detailed Logging**: Comprehensive log untuk debugging
- **Performance Metrics**: Tracking visited count, found count, dll

### 4. Configurable Parameters
- **Flexible Depth Control**: Support untuk unlimited depth (-1)
- **Language Support**: English/Indonesian version switching
- **Rate Limiting**: Adjustable delay between requests

## Perbandingan BFS vs DFS

### BFS (Breadth-First Search)
**Keunggulan**:
- Optimal untuk mencari shortest path
- Memberikan hasil level-by-level yang terorganisir
- Lebih baik untuk coverage yang merata

**Kelemahan**:
- Memory usage lebih tinggi O(w)
- Tidak cocok untuk deep exploration

**Use Case Terbaik**:
- Mencari konten di halaman utama atau near-surface
- Site mapping dan indexing

### DFS (Depth-First Search)
**Keunggulan**:
- Memory efficient O(h)
- Cocok untuk deep content exploration
- Faster untuk mencari konten spesifik yang dalam

**Kelemahan**:
- Bisa terjebak di branch yang sangat dalam
- Tidak optimal untuk shortest path

**Use Case Terbaik**:
- Research content yang tersembunyi dalam
- Specific document hunting

## Kesimpulan

Aplikasi Web Crawler Search Engine ini mengimplementasikan algoritma graph traversal klasik (BFS dan DFS) dalam konteks real-world web crawling. Dengan kompleksitas waktu O(V + E) dan optimasi caching yang efektif, aplikasi ini dapat melakukan crawling dan indexing website besar dengan performa yang baik.

Sistem caching yang cerdas mengurangi beban network dan meningkatkan responsivitas, sementara implementasi TF-IDF memberikan relevansi pencarian yang superior dibandingkan simple string matching.

Arsitektur modular dan interface yang user-friendly membuat aplikasi ini cocok untuk penelitian, educational purposes, dan prototype sistem pencarian yang lebih kompleks.

## License

Project ini dibuat untuk tujuan educational dalam mata kuliah Analisis dan Desain Algoritma.
