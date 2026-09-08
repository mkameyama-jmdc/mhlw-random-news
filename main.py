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
    "kencom",
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
    },

    # --- 以下、競合サービス・関連団体を追加 ---

    # 競合サービス: Kencom を運営する DeSCヘルスケアのニュース一覧
    # 会社名(DeSCヘルスケア)で判定すると、学会でのブース出展や研究受賞など
    # PHR/kencomのサービス動向と関係ない社内広報まで拾ってしまうため、
    # このサイトだけは "keywords" でkencom関連の表記のみに絞って判定する
    {
        "name": "DeSCヘルスケア(Kencom)",
        "url": "https://desc-hc.co.jp/archives/category/news",
        "filter_required": True,
        "selector": "a",
        "keywords": ["kencom", "Kencom", "ケンコム"]
    },

    # 業界団体: 全国健康保険協会(協会けんぽ)のお知らせ一覧
    # 協会けんぽ自身を指す広すぎるキーワード(DeSCヘルスケアのような自社名)が
    # KEYWORDS側に無いため、専用keywordsは設定せず全体のKEYWORDSをそのまま使う。
    # マッチしうるのは主に「マイナ保険証」「マイナポータル」「医療DX」「PHR」。
    # なお「健診」はKEYWORDSに含めていない。協会けんぽは特定健診の締切・様式変更等の
    # 事務連絡を大量に出しており、含めるとDeSCと同種の"広すぎ"問題が起きるため。
    {
        "name": "全国健康保険協会(協会けんぽ)",
        "url": "https://www.kyoukaikenpo.or.jp/news/index.html",
        "filter_required": True,
        "selector": "a"
    },

    # --- 以下、構造未確認のため今回は見送り。URLと理由をメモとして残す ---
    # 健康保険組合連合会(健保連): https://www.kenporen.com/book/kenpo_news/
    #   → 月次ダイジェスト形式で記事単位のリンクが取得できず、URL差分方式に不向き。
    #     必要であれば手動確認のうえ別方式(全文比較など)で検討。
    # WELBY / FiNC / HELPO / dヘルスケア(NTTドコモ) / auウェルネス(KDDI):
    #   → ニュース一覧ページのHTML構造が未確認。追加する場合は該当ページを
    #     開いてニュース一覧のセレクタ(クラス名等)を確認してから設定すること。
    # NTT東日本 報道発表ページ: https://www.ntt-east.co.jp/release/
    #   → requestsでの取得がリダイレクトループになり失敗するため対象外。
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
            if not link or not title:
                continue

            full_url = urljoin(url, link)

            # 既に投稿済みならスキップ
            if full_url in posted_urls:
                continue

            # キーワード判定 (filter_requiredがTrueの場合のみ実施)
            # サイトごとに "keywords" が指定されていればそちらを優先し、
            # 無ければ全体の KEYWORDS を使う（大文字・小文字は区別しない）
            if filter_required:
                site_keywords = site_info.get("keywords", KEYWORDS)
                title_lower = title.lower()
                is_match = any(word.lower() in title_lower for word in site_keywords)
            else:
                is_match = True  # 人間ドック学会などは無条件でTrue

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
