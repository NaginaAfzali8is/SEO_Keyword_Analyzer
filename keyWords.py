import requests
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
import pandas as pd
import re

# List of websites to scan
urls = [
    "https://hubstaff.com/",
    "https://www.timedoctor.com/",
    "https://toggl.com/",
    "https://screenshotmonitor.com/",
    "https://www.activtrak.com/",
    "https://www.prohance.net/prohance-vs-other-time-tracking-competitors.php",
    "https://www.rescuetime.com/"
]

def fetch_webpage(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def extract_keywords(html):
    soup = BeautifulSoup(html, 'html.parser')

    title = soup.title.string if soup.title else ''

    meta_keywords = ''
    meta = soup.find('meta', attrs={'name': 'keywords'})
    if meta:
        meta_keywords = meta.get('content', '')

    headings = []
    for tag in ['h1', 'h2', 'h3']:
        for heading in soup.find_all(tag):
            if heading.text:
                headings.append(heading.text.strip())

    texts = soup.stripped_strings
    full_text = ' '.join(texts)

    words = re.findall(r'\b\w{4,}\b', full_text.lower())
    word_counts = Counter(words).most_common(50)  # Top 50 words for better comparison

    return {
        "title": title,
        "meta_keywords": meta_keywords,
        "headings": headings,
        "top_words": word_counts
    }

def main():
    all_data = []
    all_words_across_sites = defaultdict(set)  # {word: set of websites}

    for url in urls:
        try:
            print(f"🔍 Fetching: {url}")
            html = fetch_webpage(url)
            page_info = extract_keywords(html)
            
            for word, count in page_info['top_words']:
                all_data.append({
                    "Website": url,
                    "Page Title": page_info["title"],
                    "Meta Keywords": page_info["meta_keywords"],
                    "Heading Count": len(page_info["headings"]),
                    "Word": word,
                    "Word Count": count
                })
                all_words_across_sites[word].add(url)

        except Exception as e:
            print(f"❌ Failed to fetch {url}: {e}")

    # Create a DataFrame
    df = pd.DataFrame(all_data)

    # Mark common keywords
    df['Is Common Keyword'] = df['Word'].apply(lambda word: 'Yes' if len(all_words_across_sites[word]) > 1 else 'No')

    # Save to Excel
    output_file = "website_keyword_analysis.xlsx"
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Keyword Analysis')

        # Highlight common keywords
        workbook = writer.book
        worksheet = writer.sheets['Keyword Analysis']
        format_highlight = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

        # Find the column number for 'Is Common Keyword'
        keyword_col_idx = df.columns.get_loc('Is Common Keyword')

        # Apply formatting
        for row_num, is_common in enumerate(df['Is Common Keyword'], start=1):
            if is_common == 'Yes':
                worksheet.write(row_num, keyword_col_idx, is_common, format_highlight)

    print(f"\n✅ Analysis complete! Saved to {output_file}")

if __name__ == "__main__":
    main()
