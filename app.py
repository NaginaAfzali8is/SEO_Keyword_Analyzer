from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import requests
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
import re
import os

app = Flask(__name__, template_folder="templates")

# --- Helper Functions ---

def fetch_webpage(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def extract_keywords_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    title = soup.title.string.strip() if soup.title else ''
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    
    headings = []
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        for heading in soup.find_all(tag):
            if heading.text:
                headings.append(heading.text.strip())

    full_text = ' '.join(soup.stripped_strings)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', full_text.lower())

    word_counts = Counter(words)
    return {
        "title": title,
        "meta_description": meta_desc['content'] if meta_desc else '',
        "meta_keywords": meta_keywords['content'] if meta_keywords else '',
        "headings": headings,
        "word_counts": word_counts
    }

# --- Routes ---

@app.route('/', methods=['GET'])
def home():
    return render_template("form.html")

@app.route('/analyze', methods=['POST'])
def analyze_urls():
    urls = request.form.get('urls', '')
    url_list = [url.strip() for url in urls.split(',') if url.strip()]
    
    all_data = []
    all_words_across_sites = defaultdict(set)

    for url in url_list:
        try:
            html = fetch_webpage(url)
            seo = extract_keywords_from_html(html)

            for word, count in seo["word_counts"].items():
                all_data.append({
                    "Website": url,
                    "Page Title": seo["title"],
                    "Meta Description": seo["meta_description"],
                    "Meta Keywords": seo["meta_keywords"],
                    "Heading Count": len(seo["headings"]),
                    "Word": word,
                    "Word Count": count
                })
                all_words_across_sites[word].add(url)

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    df = pd.DataFrame(all_data)
    df['Is Common Keyword'] = df['Word'].apply(lambda w: 'Yes' if len(all_words_across_sites[w]) > 1 else 'No')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='SEO Keywords')
        workbook = writer.book
        worksheet = writer.sheets['SEO Keywords']
        format_highlight = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        keyword_col_idx = df.columns.get_loc('Is Common Keyword')

        for row_num, is_common in enumerate(df['Is Common Keyword'], start=1):
            if is_common == 'Yes':
                worksheet.write(row_num, keyword_col_idx, is_common, format_highlight)

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='seo_keyword_analysis.xlsx'
    )

# --- Main Entrypoint ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
