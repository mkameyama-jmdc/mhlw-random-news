import requests
from bs4 import BeautifulSoup
import urllib3
from urllib.parse import urljoin
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 設定 (GitHub Actionsの環境変数から読み込む) ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
KEYWORDS = [
    "My Health Web",
    "マイヘルスウェブ",
    "Kencom",
    "ケンコム",
    "JAHIS",
    "一般社団法人保健医療福祉情報システム工業会",
    "健保連",
    "健康保険組合連合会",
    "PHR",
    "一般社団法人PHR普及推進協議会",
    "PHRサービス事業協会",
    "マイナポータル",
    "マイナ保険証",
    "医療DX"
]

HISTORY_FILE = "post_history.txt"

# サイトごとの詳細設定
TARGET_SITES = [
    {"name": "厚労省", "url": "https://www.mhlw.go.jp/stf/new-info/index.html", "filter_required": True, "selector": "a"},
    {"name": "デジタル庁", "url": "https://digital-agency-news.digital.go.jp/", "filter_required": True, "selector": "a"},
    {"name": "総務省", "url": "https://www.soumu.go.jp/menu_news/s-news/index.html", "filter_required": True, "selector": "a"},
    {"name": "経産省", "url": "https://www.meti.go.jp/press/category/04.html", "filter_required": True, "selector": "a"},
    # 人間ドック学会: キーワード不要(False)、かつ table-newslist 内の aタグのみを取得
    {
        "name": "日本人間ドック・予防医療学会", 
        "url": "https://www.ningen-dock.jp/news_list/", 
        "filter_required": False, 
        "selector": ".table-newslist a" 
    }
]
# ----------------------------------------------

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def check_site(site_info, posted_urls):
    name = site_info["name"]
    url = site_info["url"]
    filter_required = site_info["filter_required"]
    selector = site_info["selector"]
    
    try:
        response = requests.get(url, verify=False, timeout=15)
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.text, "html.parser")

        # 指定されたセレクタに一致する要素（aタグ）をすべて取得
        articles = soup.select(selector)

        for a in articles:
            title = a.get_text(strip=True)
            link = a.get('href')
            if not link or not title: continue
            
            full_url = urljoin(url, link)
            
            # 既に投稿済みならスキップ
            if full_url in posted_urls:
                continue

            # キーワード判定 (filter_requiredがTrueの場合のみ実施)
            if filter_required:
                is_match = any(word in title for word in KEYWORDS)
            else:
                is_match = True # 人間ドック学会などは無条件でTrue

            if is_match:
                payload = {"text": f"【{name} 新着】\n{title}\n{full_url}"}
                # Slack通知
                res = requests.post(SLACK_WEBHOOK_URL, json=payload, verify=False)
                
                if res.status_code == 200:
                    save_history(full_url)
                    posted_urls.add(full_url)
                    print(f"新着通知済 ({name}): {title}")
                else:
                    print(f"Slack通知失敗: {res.status_code}")

    except Exception as e:
        print(f"エラー ({name}): {e}")

def main():
    if not SLACK_WEBHOOK_URL:
        print("エラー: SLACK_WEBHOOK_URL が設定されていません。")
        return
        
    posted_urls = load_history()
    for site in TARGET_SITES:
        check_site(site, posted_urls)

if __name__ == "__main__":
    main()
