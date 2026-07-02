import os, time, sys, textwrap, json, requests, random, zipfile, platform, subprocess, re, html, glob, threading, queue, builtins, traceback
from colorama import Back, Fore, Style
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin

for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
    try:
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import fade
except ImportError:
    os.system("pip install fade==0.0.9")
    import fade
try:
    from ebooklib import epub # type: ignore
except ImportError:
    os.system("pip install EbookLib")
    from ebooklib import epub # type: ignore
try:
    import colorama
except ImportError:
    os.system("pip install colorama==0.4.6")
    import colorama
try:
    import selenium
except ImportError:
    os.system("pip install selenium==4.35.0")
    import selenium
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    os.system("pip install webdriver-manager")
    from webdriver_manager.chrome import ChromeDriverManager
try:
    import undetected_chromedriver as uc
except ImportError:
    os.system("pip install undetected-chromedriver")
    import undetected_chromedriver as uc

chrome_browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_driver_path = "NONE"
VERSION = "2.7"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = os.path.join(bundled_root, name)
        if os.path.exists(bundled):
            return bundled
    local = os.path.join(app_dir(), name)
    if os.path.exists(local):
        return local
    return os.path.join(os.getcwd(), name)


CONFIG_PATH = os.path.join(app_dir(), "config.json")

DEFAULT_POLISH_GUIDE = (
    "对比原文和粗译文，优化翻译，使它更加自然，可以适当填充主语、谓语、宾语等必要成分，"
    "让文本更有逻辑性。"
)

# ── Default settings (overridden by config.json if present) ──────────────
SETTINGS = {
    "download_format": "txt",       # "txt" or "epub"
    "translate":       False,       # auto-translate Korean → English
    "theme":           "purplepink",# fade colour theme for ASCII art
    "gui_language":    "zh",        # "zh" or "en"
    "llm_api_base":    "https://api.openai.com/v1/chat/completions",
    "llm_api_key":     "",
    "llm_model":       "gpt-4o-mini",
    "translation_style": "",
    "polish_style": DEFAULT_POLISH_GUIDE,
    "glossary_extraction_guide": "",
    "last_translate_source_type": "TXT Folder",
    "last_translate_source_path": "",
    "last_translate_output_path": "",
    "last_translate_glossary_mode": "both",
    "last_polish_source_path": "",
    "last_polish_translation_path": "",
    "last_polish_output_path": "",
    "last_polish_glossary_path": "",
    "last_polish_extra_glossary_paths": [],
    "polish_glossary_split": False,
    "polish_glossary_lines": 80,
    "polish_symbol_split": False,
    "polish_symbol_lines": 80,
    "polish_text_split": True,
    "polish_text_lines": 80,
    "novelpia_profile_dir": "",
    "novelpia_delay_min": 4.0,
    "novelpia_delay_max": 7.0
}

# All valid fade colour methods (single-argument string → text)
FADE_THEMES = [
    "purplepink", "pinkred", "greenblue", "fire", "water",
    "ocean", "lime", "brazil", "russia", "random",
    "purpleblue", "blackwhite", "gold", "metal", "earth",
]

def _apply_fade(text: str) -> str:
    """Apply the current theme from SETTINGS to text via fade."""
    theme = SETTINGS.get("theme", "purplepink")
    if theme == "ocean":
        return fade.water(text)          # fade.ocean doesn't exist; water is the closest
    func = getattr(fade, theme, None)
    if func is None:
        func = fade.purplepink
    return func(text)

# Each theme's two endpoint colours: (primary/bracket, secondary/text)
_THEME_COLOURS = {
    "purplepink":  (Fore.MAGENTA,        Fore.LIGHTMAGENTA_EX),
    "pinkred":     (Fore.LIGHTMAGENTA_EX, Fore.LIGHTRED_EX),
    "greenblue":   (Fore.GREEN,           Fore.LIGHTCYAN_EX),
    "fire":        (Fore.RED,             Fore.LIGHTYELLOW_EX),
    "water":       (Fore.BLUE,            Fore.LIGHTCYAN_EX),
    "ocean":       (Fore.BLUE,            Fore.CYAN),
    "lime":        (Fore.GREEN,           Fore.LIGHTGREEN_EX),
    "brazil":      (Fore.GREEN,           Fore.YELLOW),
    "russia":      (Fore.RED,             Fore.WHITE),
    "purpleblue":  (Fore.MAGENTA,         Fore.BLUE),
    "blackwhite":  (Fore.WHITE,           Fore.LIGHTBLACK_EX),
    "gold":        (Fore.YELLOW,          Fore.WHITE),
    "metal":       (Fore.LIGHTBLUE_EX,    Fore.WHITE),
    "earth":       (Fore.YELLOW,          Fore.GREEN),
}

_RANDOM_COLOURS = [
    Fore.MAGENTA, Fore.LIGHTMAGENTA_EX, Fore.LIGHTRED_EX, Fore.RED,
    Fore.LIGHTCYAN_EX, Fore.CYAN, Fore.BLUE, Fore.LIGHTBLUE_EX,
    Fore.GREEN, Fore.LIGHTGREEN_EX, Fore.YELLOW, Fore.LIGHTYELLOW_EX,
    Fore.WHITE,
]

def T() -> str:
    """Primary colour for the current theme (brackets, borders)."""
    if SETTINGS.get("theme") == "random":
        return random.choice(_RANDOM_COLOURS)
    return _THEME_COLOURS.get(SETTINGS.get("theme", "purplepink"), (Fore.MAGENTA, Fore.LIGHTMAGENTA_EX))[0]

def T2() -> str:
    """Secondary colour for the current theme (inner text, separators)."""
    if SETTINGS.get("theme") == "random":
        return random.choice(_RANDOM_COLOURS)
    return _THEME_COLOURS.get(SETTINGS.get("theme", "purplepink"), (Fore.MAGENTA, Fore.LIGHTMAGENTA_EX))[1]

def load_config():
    global chrome_driver_path, SETTINGS
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding="utf-8") as f:
                config = json.load(f)
            chrome_driver_path = config.get("DRIVERPATH", "NONE")
            for key in SETTINGS:
                if key in config:
                    SETTINGS[key] = config[key]
        except json.JSONDecodeError as e:
            print(f"Error reading config.json: {e}")
    bundled_driver = resource_path("chromedriver.exe")
    if (not chrome_driver_path or chrome_driver_path == "NONE" or not os.path.exists(chrome_driver_path)) and os.path.exists(bundled_driver):
        chrome_driver_path = bundled_driver

def save_config():
    try:
        config = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                config = {}
        config["DRIVERPATH"] = chrome_driver_path
        for key, val in SETTINGS.items():
            config[key] = val
        with open(CONFIG_PATH, 'w', encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

load_config()

w = Fore.WHITE
b = Fore.BLACK
g = Fore.LIGHTGREEN_EX
ly = Fore.LIGHTYELLOW_EX
lm = Fore.LIGHTMAGENTA_EX
c = Fore.LIGHTCYAN_EX
lr = Fore.LIGHTRED_EX
lb = Fore.LIGHTBLUE_EX
m = Fore.MAGENTA
bb = Fore.BLUE
rr = Fore.RESET
r = Fore.RED
y = Fore.YELLOW
gg = Fore.GREEN

random_loading_medium = random.uniform(0.7, 1.5)
random_loading_small = random.uniform(0.4, 0.9)
random_loading_large = random.uniform(1.2, 2.1)

def Spinner():
    l = ['|', '/', '-', '\\', ' ']
    for i in l+l+l:
        sys.stdout.write(f"""\r {i}""")
        sys.stdout.flush()
        time.sleep(0.1)

def press_any_key():
    try:
        import msvcrt
        print(f"\n{T()}[{T2()}#{T()}] {w}Press any key to continue...", end="", flush=True)
        msvcrt.getch()
    except ImportError:
        import sys, tty, termios
        print(f"\n{T()}[{T2()}#{T()}] {w}Press any key to continue...", end="", flush=True)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def save_to_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def list_txt_files(folder_path):
    try:
        return [
            os.path.join(folder_path, name)
            for name in os.listdir(folder_path)
            if name.lower().endswith(".txt") and os.path.isfile(os.path.join(folder_path, name))
        ]
    except FileNotFoundError:
        return []

def save_as_epub(folder_path, novel_title):
    from ebooklib import epub

    def safe_filename(name):
        return re.sub(r'[\\/*?:"<>|]', '-', name).strip()

    def clean_xml_text(value):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value or '')

    def extract_chapter_number(name):
        m = re.search(r'(?:chapter|episode)[^0-9]*?(\d+(?:\.\d+)?)', name, flags=re.IGNORECASE)
        if m:
            num = m.group(1)
            try:
                return int(num) if '.' not in num else float(num)
            except:
                return float('inf')
        m2 = re.search(r'(\d+(?:\.\d+)?)', name)
        if m2:
            num = m2.group(1)
            try:
                return int(num) if '.' not in num else float(num)
            except:
                return float('inf')
        return float('inf')

    def natural_key(s):
        parts = re.split(r'(\d+)', s.lower())
        return [int(p) if p.isdigit() else p for p in parts]

    txt_files = list_txt_files(folder_path)
    if not txt_files:
        print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} No .txt files found to convert.")
        return

    files_with_nums = []
    for p in txt_files:
        base = os.path.basename(p)
        num = extract_chapter_number(base)
        files_with_nums.append((num, base, p))

    files_with_nums.sort(key=lambda x: (x[0], natural_key(x[1])))
    sorted_files = [item[2] for item in files_with_nums]

    book = epub.EpubBook()
    book.set_identifier(safe_filename(novel_title.lower()) or "novel")
    book.set_title(novel_title)
    book.set_language("en")
    book.add_author("TopStop5's Novelscraper")
    try:
        book.add_metadata('DC', 'creator', 'Novelscraper by TopStop5')
        book.add_metadata('DC', 'title', novel_title)
    except Exception:
        pass

    chapters = []
    total_chaps = len(sorted_files)
    zero_pad = len(str(total_chaps))

    for idx, file_path in enumerate(sorted_files, 1):
        fname = os.path.basename(file_path)
        chap_title = os.path.splitext(fname)[0]
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = clean_xml_text(f.read())

        paras = [p.strip() for p in re.split(r'(?:\r?\n){2,}', text) if p.strip()]
        if not paras:
            continue
        html_body = ''.join(f'<p>{html.escape(p)}</p>' for p in paras)
        html_doc = f'<h1>{html.escape(chap_title)}</h1>{html_body}'

        ch = epub.EpubHtml(title=chap_title, file_name=f'chapter_{str(idx).zfill(zero_pad)}.xhtml', lang='en')
        ch.content = html_doc
        book.add_item(ch)
        chapters.append(ch)

    if not chapters:
        print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} No readable chapter text found for EPUB.")
        return

    book.toc = chapters
    book.spine = ['nav'] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output_path = os.path.join(folder_path, f"{safe_filename(novel_title)}.epub")
    epub.write_epub(output_path, book)
    try:
        print(f"\n{g}[{w}!{g}]{w} EPUB created: {output_path}")
    except UnicodeEncodeError:
        safe_output_path = output_path.encode("unicode_escape").decode("ascii")
        print(f"\n{g}[{w}!{g}]{w} EPUB created: {safe_output_path}")


# ─────────────────────────────────────────────
#  SBXH2 HANDLER
# ─────────────────────────────────────────────

translate_cache: dict = {}

def translate_text(text: str) -> str:
    if not text or not text.strip():
        return text
    if text in translate_cache:
        return translate_cache[text]
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=ko&tl=en&dt=t&q={requests.utils.quote(text)}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()
        result = "".join(t[0] for t in data[0] if t[0])
        translate_cache[text] = result
        return result
    except Exception:
        return text


def translate_lines(lines: list) -> list:
    chunk_size = 25
    out = list(lines)
    for i in range(0, len(out), chunk_size):
        chunk = out[i : i + chunk_size]
        out[i : i + chunk_size] = [translate_text(l) for l in chunk]
    return out


def clean_sbxh2_chapter_text(raw: str):
    """
    Strip site chrome from clipboard/innerText on sbxh2/newtokki pages.

    Strategy
    --------
    The breadcrumb line always looks like (Korean or English):
        홈 › 소설 › <title> › N화
        home › novel › <title> › Episode N
    Everything BEFORE and INCLUDING that line is site header chrome.

    After the breadcrumb the actual chapter content follows, but it ends
    with a navigation footer that always starts with one of:
        ‹ Previous episode   /   ‹ 이전화
    followed by nav links and a font-size control block
        letter−16px+basic
    Everything from that footer onward is stripped too.
    """
    if not raw:
        return None

    text = raw.replace("\r", "")

    # ── 1. Trim header ──────────────────────────────────────────────
    # The page structure is always:
    #   ... site chrome ...
    #   홈 › 소설 › <title> › N화 <chapter-title>   ← breadcrumb
    #   ‹ 이전화  목록  책갈피  다음화 ›              ← nav bar
    #   글자 − 16px + 기본                           ← font-size control
    #   <actual story content starts here>
    #
    # Strategy: find the font-size control line and start content AFTER it.
    # If that line is absent, fall back to cutting after the breadcrumb.

    # Primary: cut after the font-size control line (글자 − NNpx  OR  letter − NNpx)
    font_ctrl_pattern = re.compile(
        r"(?:글자|letter)\s*[-−]\s*\d+px[^\n]*",
        re.IGNORECASE,
    )
    fm = font_ctrl_pattern.search(text)
    if fm:
        text = text[fm.end():]
    else:
        # Fallback: cut after the breadcrumb line (everything up to end of that line)
        breadcrumb_pattern = re.compile(
            r"(?:홈|home)\s*[›>]\s*(?:소설|novel)\s*[›>][^\n]*",
            re.IGNORECASE,
        )
        bm = breadcrumb_pattern.search(text)
        if bm:
            text = text[bm.end():]
        else:
            # Last resort: strip known site-chrome blocks line by line
            noise_lines = re.compile(
                r"^\s*(?:"
                r"https?://\S+|"
                r"@\w+|"
                r"[🐰🌙🏆🔧📢🛠️].*|"
                r"(?:New Rabbit|Newtokki|뉴토끼).*|"
                r"(?:home|홈|webtoon|웹툰|novel|소설|comic book|만화|"
                r"animated film|애니|ranking|랭킹|game|게임|"
                r"community|커뮤니티|bookmark|북마크|event|이벤트|"
                r"patch notes?|패치노트|announcement|공지사항|"
                r"log\s*in|로그인|join the membership|회원가입|"
                r"customer service center|고객센터|"
                r"download the app|앱 다운로드|telegram channel|텔레그램 채널|"
                r"search by work|recently viewed works|최근본작품|"
                r"point ranking|포인트랭킹|advertising inquiry|광고문의|"
                r"this feature is in preparation|준비 중|"
                r"basic|dark)\s*"
                r")\s*$",
                re.IGNORECASE,
            )
            text = "\n".join(
                line for line in text.splitlines()
                if not noise_lines.match(line)
            )

    # ── 2. Trim footer ──────────────────────────────────────────────
    footer_pattern = re.compile(
        r"(?:‹\s*(?:Previous episode|이전화)|"
        r"(?:letter|글자)\s*[-−]\s*\d+px|"   # English "letter−16px" OR Korean "글자 − 16px"
        r"inventory|북마크|bookmark)"
        r".*",
        re.IGNORECASE | re.DOTALL,
    )
    text = footer_pattern.sub("", text)

    # ── 3. General noise passes ─────────────────────────────────────
    misc_patterns = [
        r"^https?://\S+$",
        r"@\w+\s*",
        r"^basic\s*$",
        r"^dark\s*$",
        # NOTE: do NOT add generic words like "awakening" here — they are common
        # story vocabulary (e.g. 각성 = awakening) and will wipe out real content.
    ]
    for p in misc_patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

    # ── 4. Normalise whitespace ─────────────────────────────────────
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text if text else None


def _is_cloudflare_challenge(driver) -> bool:
    """
    Return True if the current page is a Cloudflare challenge/verification screen
    that requires manual user interaction (i.e. uc could NOT auto-solve it).
    Detects both the JS-challenge title and the "Performing security verification"
    body text that appears on the interactive CAPTCHA variant.
    """
    CF_TITLE_FRAGMENTS = [
        "just a moment", "checking your browser", "please wait",
        "security check", "enable javascript", "one moment", "attention required",
        "请稍候", "稍候", "请稍等",
    ]
    CF_BODY_FRAGMENTS = [
        "performing security verification",
        "this website uses a security service",
        "verifies you are not a bot",
        "verify you are human",
        "请稍候",
        "请稍等",
        "启用 javascript",
        "启用 javascript 和 cookie",
        "cf-challenge",
        "challenge-platform",
    ]
    try:
        title = (driver.title or "").lower()
        if any(frag in title for frag in CF_TITLE_FRAGMENTS):
            return True
        if "__cf_chl" in (driver.current_url or ""):
            return True
        body = (driver.execute_script(
            "return document.body ? document.body.innerText : '';"
        ) or "").lower()
        if any(frag in body for frag in CF_BODY_FRAGMENTS):
            return True
    except Exception:
        pass
    return False


def wait_for_cloudflare(driver, timeout: int = 30) -> bool:
    """
    Wait for a Cloudflare challenge to clear.

    * Auto-challenges (JS spinner): uc resolves these on its own; we just poll.
    * Manual CAPTCHA ("Performing security verification"): we PAUSE scraping,
      print a clear notice, and wait up to 5 minutes for the user to solve it
      in the browser window.  Scraping resumes automatically once the page loads.
    """
    manual_notified = False
    manual_deadline = None

    deadline = time.time() + timeout
    while True:
        now = time.time()

        is_cf = _is_cloudflare_challenge(driver)

        if is_cf:
            # Check whether this is the manual-verification variant
            try:
                body = (driver.execute_script(
                    "return document.body ? document.body.innerText : '';"
                ) or "").lower()
                needs_manual = any(frag in body for frag in [
                    "performing security verification",
                    "this website uses a security service",
                    "verifies you are not a bot",
                    "verify you are human",
                    "请稍候",
                    "请稍等",
                    "启用 javascript",
                    "启用 javascript 和 cookie",
                ])
            except Exception:
                needs_manual = False

            if needs_manual:
                if not manual_notified:
                    manual_notified = True
                    manual_deadline = time.time() + 300   # 5-minute window
                    print(f"\n{T()}╔══════════════════════════════════════════════════╗")
                    print(f"{T()}║  {Fore.LIGHTRED_EX}⚠  CLOUDFLARE MANUAL VERIFICATION REQUIRED  {Fore.LIGHTRED_EX}⚠  ║")
                    print(f"{T()}╠══════════════════════════════════════════════════╣")
                    print(f"{T()}║  {Fore.WHITE}Scraping has been PAUSED.                       {T()}║")
                    print(f"{T()}║  {Fore.WHITE}Please solve the CAPTCHA in the Chrome window.  {T()}║")
                    print(f"{T()}║  {Fore.WHITE}Scraping will resume automatically afterwards.  {T()}║")
                    print(f"{T()}╚══════════════════════════════════════════════════╝{Fore.RESET}\n")
                # Use the extended 5-min deadline while waiting for manual solve
                if manual_deadline and time.time() > manual_deadline:
                    print(f"{r}[{w}!{r}]{w} Cloudflare timeout — could not verify after 5 minutes.")
                    return False
                time.sleep(2)
                continue
            else:
                # Auto-challenge — just wait out the normal timeout
                if now > deadline:
                    return True  # uc usually handles it; optimistically continue
                time.sleep(1)
                continue

        # No CF challenge detected
        try:
            body_text = driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ) or ""
            if len(body_text.strip()) > 200:
                if manual_notified:
                    print(f"{g}[{w}!{g}]{w} Cloudflare cleared — resuming scrape …\n")
                return True
        except Exception:
            pass

        if now > deadline:
            return True  # optimistically continue

        time.sleep(1)


def configure_sbxh_browser(driver) -> None:
    """Install sbxh browser guards before the first page navigation."""
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = window.chrome || { runtime: {} };
                window.__ntkDevtoolsPreflight = 1;
                Object.defineProperty(window, 'DisableDevtool', {
                    value: function(){ return undefined; },
                    writable: false,
                    configurable: false
                });
            """
        })
    except Exception as e:
        print(f"{y}[{w}!{y}]{w} Could not install sbxh browser guards: {e}")


def _parse_sbxh_chapters_from_html(page_html: str, base_url: str, novel_id: str) -> list:
    """Extract sbxh/newtokki chapter links from raw Next.js HTML."""
    if not page_html:
        return []

    anchor_pattern = re.compile(
        rf'<a\b[^>]*href=["\']([^"\']*/novel/{re.escape(novel_id)}/[^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    ep_pattern = re.compile(r"^\s*(\d+)\s*(?:화|話|회|episode|ep\.?)", re.IGNORECASE)

    chapters = []
    seen_urls = set()

    for match in anchor_pattern.finditer(page_html):
        href = html.unescape(match.group(1))
        block = match.group(2)
        text = re.sub(r"<[^>]+>", " ", block)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if re.search(r"(?:부터\s*보기|최신화부터|from\s+(?:first|latest)|latest\s+episode)", text, re.IGNORECASE):
            continue

        ep_match = ep_pattern.search(text)
        if not ep_match:
            continue

        ep_num = int(ep_match.group(1))
        absolute_url = urljoin(base_url, href)
        if absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)

        title = text[ep_match.end():].strip(" -–—:")
        chapters.append({"ep": ep_num, "url": absolute_url, "title": title})

    chapters.sort(key=lambda x: x["ep"])
    return chapters


def _fetch_sbxh_chapters_from_index(novel_index_url: str, novel_id: str) -> list:
    """Fetch the novel index HTML directly and parse its chapter list."""
    try:
        parsed = urlparse(novel_index_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        resp = requests.get(
            novel_index_url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            proxies={"http": None, "https": None},
        )
        if resp.status_code != 200:
            return []
        return _parse_sbxh_chapters_from_html(resp.text, base_url, novel_id)
    except Exception:
        return []


def get_chapter_list(driver, novel_index_url: str, novel_id: str | None = None) -> list:
    """
    Return a list of dicts sorted by episode number:
        {"ep": int, "url": str, "title": str}

    Reads the chapter <a> links directly from the novel index page.
    Chapter IDs in the URL are NOT sequential integers — only the
    scraped URLs are reliable.

    NOTE: the caller must already have navigated to the index page and
    waited for CF to clear before calling this.  We do NOT re-navigate
    here so we don't blow away the already-cleared session.
    """
    print(f"{T()}[{T2()}!{T()}]{w} Reading chapter list from current page …")

    parsed_index = urlparse(novel_index_url)
    base_url = f"{parsed_index.scheme}://{parsed_index.netloc}"
    if novel_id is None:
        parts = parsed_index.path.strip("/").split("/")
        if "novel" in parts:
            idx = parts.index("novel")
            novel_id = parts[idx + 1] if idx + 1 < len(parts) else None

    if novel_id:
        try:
            chapters = _parse_sbxh_chapters_from_html(driver.page_source, base_url, novel_id)
            fetched = _fetch_sbxh_chapters_from_index(novel_index_url, novel_id)
            if fetched and len(fetched) > len(chapters):
                print(f"{T()}[{T2()}!{T()}]{w} Direct HTML fetch found {len(fetched)} episodes.")
                return fetched
            if chapters:
                return chapters
        except Exception as e:
            print(f"{y}[{w}!{y}]{w} HTML chapter parser failed, trying DOM fallback: {e}")

    # Wait for at least one chapter-style link to exist in the DOM
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='/novel/']")
            )
        )
    except TimeoutException:
        pass

    time.sleep(1)   # small settle for lazy-loaded content

    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/novel/']")
    ep_pattern = re.compile(r"^\s*(\d+)\s*(?:화|話|회|episode|ep\.?)", re.IGNORECASE)

    chapters = []
    seen_urls = set()

    for a in anchors:
        href = a.get_attribute("href") or ""
        if not href or href in seen_urls:
            continue
        # Must be a chapter URL: exactly 3 path segments /novel/<id>/<chapterId>
        parts = urlparse(href).path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "novel":
            continue
        if novel_id and parts[1] != novel_id:
            continue
        seen_urls.add(href)

        text = (a.get_attribute("innerText") or a.text or "").strip()
        text = re.sub(r"\s+", " ", text)
        mp = ep_pattern.search(text)
        if not mp:
            continue
        ep_num = int(mp.group(1))

        subtitle = text[mp.end():].strip(" -–—:")

        chapters.append({"ep": ep_num, "url": href, "title": subtitle})

    chapters.sort(key=lambda x: x["ep"])
    return chapters


def extract_via_clipboard(driver):
    """
    Extract visible page text by simulating Ctrl+A / Ctrl+C and reading the
    system clipboard.  This captures content that is visually rendered but
    not reachable via JS innerText (Shadow DOM, protected containers, etc.).
    Falls back to JS innerText if the clipboard approach yields nothing.
    """
    try:
        import pyperclip
    except ImportError:
        import subprocess
        subprocess.call([sys.executable, "-m", "pip", "install", "pyperclip", "--quiet"])
        import pyperclip

    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys

    # ── 1. Clipboard approach ────────────────────────────────────────
    try:
        # Clear clipboard first so we can detect a failed copy
        pyperclip.copy("")
        time.sleep(0.3)

        # Click the body to make sure the page has focus
        driver.execute_script("document.body.click();")
        time.sleep(0.3)

        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        time.sleep(0.4)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()
        time.sleep(0.5)

        text = pyperclip.paste()
        if text and len(text.strip()) > 80:
            return text
    except Exception:
        pass

    # ── 2. JS fallback: stripped body clone ─────────────────────────
    try:
        text = driver.execute_script("""
            var clone = document.body.cloneNode(true);
            var junk = clone.querySelectorAll(
                'script,style,nav,header,footer,button,input,select,noscript'
            );
            junk.forEach(function(el){ el.parentNode.removeChild(el); });
            return clone.innerText;
        """)
        if text and len(text.strip()) > 80:
            return text
    except Exception:
        pass

    # ── 3. Last resort ───────────────────────────────────────────────
    try:
        text = driver.execute_script("return document.body.innerText;")
        if text and len(text.strip()) > 80:
            return text
    except Exception:
        pass

    return None


def handle_sbxh2(driver, novel_url: str, do_translate: bool) -> None:
    """
    Scrape chapters from sbxh2.com (newtokki).

    Key behaviours
    --------------
    * Title    → h1 selector (confirmed working by diagnostics).
    * Chapters → scraped from the novel index page <a> links; episode
                 numbers are mapped to their real (non-sequential) URLs.
    * Content  → innerText of a script/nav-stripped DOM clone, then
                 surgically cleaned with clean_sbxh2_chapter_text().
    * CF check → driver must be launched WITHOUT --headless (handled
                 in main()); 5-second wait added for the JS challenge.
    """
    try:
        parsed   = urlparse(novel_url)
        parts    = parsed.path.strip("/").split("/")
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if "novel" in parts:
            idx      = parts.index("novel")
            novel_id = parts[idx + 1] if idx + 1 < len(parts) else None
        else:
            novel_id = None

        if not novel_id:
            print(f"{r}[{w}X{r}]{w} Could not parse novel ID from URL.")
            return

        novel_index_url = f"{base_url}/novel/{novel_id}"

        print(f"{T()}[{T2()}!{T()}]{w} Loading novel index page …")
        try:
            driver.get(novel_index_url)
        except TimeoutException:
            driver.execute_script("window.stop();")

        # Block here until Cloudflare clears (up to 2 minutes).
        # The user can solve a CAPTCHA in the browser window if one appears.
        cf_ok = wait_for_cloudflare(driver, timeout=120)
        if not cf_ok:
            print(f"{r}[{w}X{r}]{w} Could not get past Cloudflare. Try again or solve the CAPTCHA manually.")
            return

        # ── grab title AFTER CF cleared ─────────────────────────────
        novel_title = None
        for sel in ["h1", "h2", ".novel-title", ".title", ".book-title"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                txt = el.text.strip()
                if txt:
                    novel_title = txt
                    break
            except Exception:
                continue

        if not novel_title:
            # driver.title format: "Novel Name | 뉴토끼"
            raw_title = driver.title or ""
            novel_title = raw_title.split("|")[0].split("–")[0].split("-")[0].strip()
        if not novel_title:
            novel_title = f"Novel_{novel_id}"

        folder_name = re.sub(r'[\\/*?:"<>|]', "-", novel_title).strip()
        folder_path = os.path.join(os.getcwd(), folder_name)
        os.makedirs(folder_path, exist_ok=True)

        print(f"{T()}[{T2()}!{T()}]{w} Novel : {novel_title}")
        print(f"{T()}[{T2()}!{T()}]{w} Folder: {folder_path}")

        # ── Active-settings notification ────────────────────────────
        fmt_disp   = "EPUB (auto)"
        tl_disp    = f"{Fore.LIGHTGREEN_EX}ON{Fore.RESET}" if SETTINGS["translate"] else f"{Fore.RED}OFF{Fore.RESET}"
        theme_disp = SETTINGS["theme"]
        print(f"\n{T()}┌─ Active Settings {'─'*31}┐{Fore.RESET}")
        print(f"  {T()}[{T2()}!{T()}]{Fore.WHITE}  Format   : {T()}{fmt_disp}{Fore.RESET}")
        print(f"  {T()}[{T2()}!{T()}]{Fore.WHITE}  Translate: {tl_disp}")
        print(f"  {T()}[{T2()}!{T()}]{Fore.WHITE}  Theme    : {T()}{theme_disp}{Fore.RESET}")
        print(f"  {T()}[{T2()}!{T()}]{Fore.WHITE}  Change settings via option {T()}[3]{Fore.WHITE} from the main menu.{Fore.RESET}")
        print(f"{T()}└{'─'*49}┘{Fore.RESET}\n")

        # Chapter list reads from the CURRENT page (already loaded + CF-cleared)
        chapters = get_chapter_list(driver, novel_index_url, novel_id)

        if not chapters:
            print(f"{r}[{w}X{r}]{w} No chapters found on index page.")
            return

        first_ep = chapters[0]["ep"]
        last_ep  = chapters[-1]["ep"]
        print(f"{T()}[{T2()}!{T()}]{w} Episodes available: {first_ep} – {last_ep}  ({len(chapters)} total)")

        ep_map = {ch["ep"]: ch for ch in chapters}
        selected = chapters
        print(f"{T()}[{T2()}!{T()}]{w} Auto mode: downloading all detected episodes and building EPUB.")

        failed_eps = []

        def try_download(ch: dict) -> bool:
            ep_num   = ch["ep"]
            ep_url   = ch["url"]
            ep_label = ch["title"] or f"Episode {ep_num}"
            safe_label = re.sub(r'[\\/*?:"<>|]', '-', ep_label)
            file_path = os.path.join(folder_path, f"Episode {ep_num:04d} - {safe_label}.txt")

            if os.path.exists(file_path) and os.path.getsize(file_path) > 200:
                print(f"{y}[{w}~{y}]{w} Episode {ep_num}: already saved, skipping.")
                return True

            print(f"{T()}[{T2()}!{T()}]{w} Episode {ep_num}: {ep_url}")
            try:
                driver.get(ep_url)
            except TimeoutException:
                driver.execute_script("window.stop();")

            # Wait for CF to clear on this chapter page too
            wait_for_cloudflare(driver, timeout=60)

            # Poll until the *cleaned* chapter text is non-empty.
            # Raw body text passes 400 chars even with just nav/headers, so we
            # must clean first and check the result — that way we only proceed
            # once real chapter content is actually on the page.
            raw  = None
            text = None
            for attempt in range(20):
                raw = extract_via_clipboard(driver)
                if raw:
                    text = clean_sbxh2_chapter_text(raw)
                    if text and len(text.strip()) >= 200:
                        break
                    text = None
                    # On 3rd attempt dump diagnostics so we can see what
                    # the page returns vs what survives cleaning
                    if attempt == 2:
                        print(f"{y}[{w}DBG{y}]{w} --- RAW clipboard (first 800 chars) ---")
                        print((raw or "")[:800])
                        print(f"{y}[{w}DBG{y}]{w} --- CLEANED (first 800 chars) ---")
                        print((clean_sbxh2_chapter_text(raw or "") or "<empty after cleaning>")[:800])
                        print(f"{y}[{w}DBG{y}]{w} --- END ---")
                if attempt < 19:
                    print(f"{y}[{w}~{y}]{w} Episode {ep_num}: waiting for content … ({attempt + 1}/20)")
                    time.sleep(1.5)

            if not raw:
                print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} Could not extract text for Episode {ep_num}")
                return False
            if not text:
                print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} Episode {ep_num} was empty after cleaning")
                return False

            if do_translate:
                print(f"{T()}[{T2()}~{T()}]{w} Translating Episode {ep_num} …")
                lines = [l for l in text.split("\n") if l.strip()]
                lines = translate_lines(lines)
                text  = "\n\n".join(lines)

            save_to_file(file_path, text)
            print(f"{gg}[{w}+{gg}]{w} Saved Episode {ep_num}")
            return True

        for ch in selected:
            if not try_download(ch):
                failed_eps.append(ch["ep"])

        for retry_round in range(1, 3):
            if not failed_eps:
                break
            print(f"\n{y}[{w}!{y}]{w} Retrying failed episodes, round {retry_round}/2: {failed_eps}")
            still_failed = []
            for ep_num in failed_eps:
                if ep_num in ep_map:
                    if not try_download(ep_map[ep_num]):
                        still_failed.append(ep_num)
                else:
                    still_failed.append(ep_num)
            failed_eps = still_failed

        if failed_eps:
            print(f"\n{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} Some episodes still failed: {failed_eps}")
        else:
            print(f"\n{gg}[{w}!{gg}]{w} All episodes downloaded successfully.")

        print(f"{T()}[{T2()}!{T()}]{w} Building EPUB from saved episodes...")
        save_as_epub(folder_path, novel_title)

        print(f"{T()}[{T2()}!{T()}]{w} Done.")

    except Exception as e:
        print(f"{r}[{w}X{r}]{w} Error in sbxh2 handler: {e}")
        import traceback; traceback.print_exc()


# ─────────────────────────────────────────────
#  EXISTING HANDLERS (unchanged)
# ─────────────────────────────────────────────

def lnccreate_novel_folder(driver):
    try:
        current_url = driver.current_url
        parsed = urlparse(current_url)
        parts = parsed.path.strip("/").split("/")

        if "book" in parts:
            book_index = parts.index("book")
            slug = parts[book_index + 1]
        else:
            raise Exception("Could not locate book title in URL")

        novel_title = slug.replace("-", " ").title()
        folder_name = novel_title.replace(":", " -").replace("/", "-")
        folder_path = os.path.join(os.getcwd(), folder_name)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"{T()}[{T2()}!{T()}] {w}Created folder: {folder_path}")
        else:
            print(f"{y}[{w}!{y}] {w}Folder already exists: {folder_path}")

        return folder_path

    except Exception as e:
        print(f"{r}[{w}X{r}]{w} Error creating novel folder from URL: {e}")
        return None

def lncscrape_chapter(driver, chapter_url, chapter_title, folder_path, max_line_length=80):
    try:
        try:
            driver.get(chapter_url)
        except TimeoutException:
            driver.execute_script("window.stop();")

        time.sleep(1.2)

        container = driver.find_element(By.ID, "chapter-container")

        title_text = ""
        try:
            title_el = driver.find_element(By.CLASS_NAME, "chapter-title")
            title_text = title_el.text.strip()
        except:
            pass

        try:
            content_root = container.find_element(By.CLASS_NAME, "chapter-content")
        except:
            content_root = container

        for ad in content_root.find_elements(By.CSS_SELECTOR, ".nf-ads"):
            driver.execute_script("arguments[0].remove();", ad)

        final_lines = []

        if title_text:
            final_lines.append(title_text)

        paragraphs = content_root.find_elements(By.XPATH, ".//p")

        for p in paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if (
                text.startswith("If you find any errors")
                or text.startswith("Share to your friends")
                or "Tap the middle of the screen" in text
            ):
                break
            if text == title_text:
                continue
            final_lines.append(text)

        if len(final_lines) <= (1 if title_text else 0):
            for line in content_root.text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line == title_text:
                    continue
                if line.startswith("If you find any errors"):
                    break
                final_lines.append(line)

        wrapped = [textwrap.fill(line, width=max_line_length) for line in final_lines]
        final_content = "\n\n".join(wrapped)
        save_to_file(os.path.join(folder_path, f"{chapter_title}.txt"), final_content)
        print(f"{T()}[{T2()}+{T()}]{w} Downloaded {chapter_title}")

    except Exception as e:
        print(f"{r}[{w}x{r}]{w} Error scraping {chapter_title}: {e}")

def lncdownload_chapters(driver, base_url, start_chapter, end_chapter, folder_path):
    for ch_num in range(start_chapter, end_chapter + 1):
        chapter_url = f"{base_url}/chapter-{ch_num}"
        chapter_title = f"Chapter {ch_num}"
        try:
            time.sleep(0.02)
            print(f"{T()}[{T2()}!{T()}] {w}Downloading {chapter_title} from {chapter_url}")
            driver.get(chapter_url)
            lncscrape_chapter(driver, chapter_url, chapter_title, folder_path)
        except Exception as e:
            raise Exception(f"Failed to download chapter {ch_num}: {e}")

def get_chrome_version():
    os_type = platform.system().lower()
    version = None

    try:
        if os_type == "windows":
            output = subprocess.run(
                [r'reg', 'query', r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon', '/v', 'version'],
                capture_output=True, text=True
            )
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output.stdout)
            if match:
                version = match.group(1)
        elif os_type == "darwin":
            output = subprocess.run(
                ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                capture_output=True, text=True
            )
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output.stdout)
            if match:
                version = match.group(1)
        elif os_type == "linux":
            for cmd in ["google-chrome", "chrome", "chromium-browser"]:
                try:
                    output = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output.stdout)
                    if match:
                        version = match.group(1)
                        break
                except FileNotFoundError:
                    continue
    except Exception as e:
        print(f"{r}[{w}X{r}]{w} Error detecting Chrome version: {e}")

    if not version:
        raise RuntimeError("Could not detect Chrome version automatically.")
    return version


def find_chrome_executable():
    os_type = platform.system().lower()
    candidates = []
    if os_type == "windows":
        candidates.extend([
            chrome_browser_path,
            os.path.join(os.getenv("PROGRAMFILES", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.getenv("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ])
    elif os_type == "darwin":
        candidates.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    else:
        candidates.extend(["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"])

    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return candidate
            continue
        try:
            probe = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if probe.returncode == 0:
                return candidate
        except Exception:
            continue
    raise RuntimeError("Could not find Google Chrome. Please install Chrome or set chrome_browser_path in Nibble.py.")


def find_chrome_user_data_dir():
    os_type = platform.system().lower()
    candidates = []
    if os_type == "windows":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        candidates.extend([
            os.path.join(local_app_data, "Google", "Chrome", "User Data"),
            os.path.join(local_app_data, "Google", "Chrome Beta", "User Data"),
            os.path.join(local_app_data, "Google", "Chrome SxS", "User Data"),
        ])
    elif os_type == "darwin":
        candidates.append(os.path.expanduser("~/Library/Application Support/Google/Chrome"))
    else:
        candidates.extend([
            os.path.expanduser("~/.config/google-chrome"),
            os.path.expanduser("~/.config/google-chrome-beta"),
            os.path.expanduser("~/.config/chromium"),
        ])

    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return os.path.abspath(candidate)

    # Confirm that Chrome exists before returning its standard user-data path.
    find_chrome_executable()
    if candidates and candidates[0]:
        return os.path.abspath(candidates[0])
    raise RuntimeError("Could not locate the Google Chrome user data folder.")


def auto_novelpia_profile_dir():
    chrome_user_data = find_chrome_user_data_dir()
    chrome_root = os.path.dirname(chrome_user_data)
    return os.path.join(chrome_root, "Nibble", "novelpia_chrome_profile")


def get_chrome_major_version():
    version = get_chrome_version()
    match = re.match(r"(\d+)", version)
    if not match:
        raise RuntimeError(f"Could not parse Chrome major version from {version}.")
    return int(match.group(1))


def explain_undetected_chrome_error(error):
    text = str(error)
    match = re.search(
        r"only supports Chrome version\s+(\d+).*?Current browser version is\s+(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        driver_ver, browser_ver = match.groups()
        return (
            f"ChromeDriver version mismatch: driver={driver_ver}, Chrome={browser_ver}. "
            "Please update Google Chrome and try again. If it still fails, close Chrome, "
            "delete undetected-chromedriver cache under your user temp/appdata folder, then restart Nibble."
        )
    return ""

def download_chromedriver():
    random_loading_small = 0.5
    random_loading_medium = 1
    random_loading_large = 1.5

    os_type = platform.system().lower()
    chrome_driver_path = os.path.join(os.getcwd(), "chromedriver")

    version = get_chrome_version()
    print(f"{T()}[{T2()}!{T()}]{w} Detected Chrome version: {version}")

    if os_type == "windows":
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win32/chromedriver-win32.zip"
        driver_file_name = "chromedriver-win32.zip"
    elif os_type == "darwin":
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/mac-x64/chromedriver-mac-x64.zip"
        driver_file_name = "chromedriver-mac-x64.zip"
    elif os_type == "linux":
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip"
        driver_file_name = "chromedriver-linux64.zip"
    else:
        raise Exception("Unsupported OS")

    zip_file_path = os.path.join(os.getcwd(), driver_file_name)
    time.sleep(random_loading_small)
    print(f"{T()}[{T2()}!{T()}]{w} Downloading ChromeDriver from {download_url}...")
    time.sleep(random_loading_large)

    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(zip_file_path, "wb") as zip_file:
            zip_file.write(response.content)
        time.sleep(random_loading_small)
        print(f"{T()}[{T2()}+{T()}]{w} Downloaded {driver_file_name}. Extracting...")
        time.sleep(random_loading_medium)
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(os.getcwd())
        os.remove(zip_file_path)
        base_folder_name = driver_file_name.replace(".zip", "")
        extracted_folder = os.path.join(os.getcwd(), base_folder_name)

        if os.path.isdir(extracted_folder):
            for item in ["chromedriver.exe", "chromedriver"]:
                item_path = os.path.join(extracted_folder, item)
                if os.path.exists(item_path):
                    new_path = os.path.join(os.getcwd(), os.path.basename(item_path))
                    os.replace(item_path, new_path)
            try:
                os.rmdir(extracted_folder)
            except OSError:
                import shutil
                shutil.rmtree(extracted_folder, ignore_errors=True)
        time.sleep(random_loading_medium)
        print(f"{T()}[{T2()}+{T()}]{w} ChromeDriver extracted and moved successfully.")
        time.sleep(random_loading_large)

        if os_type == "windows":
            chrome_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")

        return chrome_driver_path
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[{Fore.WHITE}x{Fore.RED}]{w} Error downloading ChromeDriver: {e}")
        return None

def check_and_set_driver():
    global chrome_driver_path

    random_loading_small = 0.5
    random_loading_large = 1.5

    if chrome_driver_path == "NONE" or chrome_driver_path == "C:/Program Files":
        driver_exists = input(f"\n{T()}[{T2()}>{T()}]{w} Do you have ChromeDriver? (Y/N): ").strip().lower()

        if driver_exists == "y":
            time.sleep(random_loading_small)
            chrome_driver_path = input(f"{T()}[{T2()}>{T()}]{w} Please input your ChromeDriver path: ").strip()
            print(f"{T()}[{T2()}!{T()}] {w}Driver path set to: {chrome_driver_path}")
        elif driver_exists == "n":
            time.sleep(random_loading_small)
            print(f"{T()}[{T2()}!{T()}]{w} Downloading ChromeDriver for your system...")
            time.sleep(random_loading_large)
            new_driver_path = download_chromedriver()
            if new_driver_path is None:
                time.sleep(random_loading_small)
                print(f"{r}[{w}X{r}]{w}  Failed to download ChromeDriver.")
                time.sleep(4)
                return
            else:
                chrome_driver_path = new_driver_path

        save_config()

        print(f"{T()}[{T2()}!{T()}] {w}Driver path set to: {chrome_driver_path}")

def normalize_novelfire_base_url(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if 'book' in parts:
        book_index = parts.index('book')
        base_path = '/'.join(parts[:book_index + 2])
        return f"{parsed.scheme}://{parsed.netloc}/{base_path}"
    return url.rstrip('/')

def handle_novelfire(driver, novel_url):
    print(f'{T()}[{T2()}+{T()}]{w} NovelFire downloads may be slow.')
    novel_base_url = normalize_novelfire_base_url(novel_url)
    if novel_base_url.endswith('/chapters/'):
        folder_path = os.path.join(os.getcwd(), "Downloaded_Chapters")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        novel_title = "Downloaded_Chapters"
    else:
        driver.get(novel_url)
        folder_path = lnccreate_novel_folder(driver)
        if not folder_path:
            print(f"{T()}[{T2()}!{T()}] {w}Could not create or find folder. Exiting...")
            driver.quit()
            return
        novel_title = os.path.basename(folder_path)

    start_chapter = int(input(f"\n{T()}[{T2()}>{T()}]{w} Enter the starting chapter: "))
    end_chapter = int(input(f"{T()}[{T2()}>{T()}]{w} Enter the ending chapter: "))
    download_format = input(f"{T()}[{T2()}?{T()}]{w} Download format (txt/epub) [default = txt]: ").strip().lower()
    if download_format not in ['txt', 'epub']:
        download_format = 'txt'

    failed_chapters = []

    def try_download(ch_num):
        try:
            lncdownload_chapters(driver, novel_base_url, ch_num, ch_num, folder_path)
            return True
        except Exception as e:
            print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}] {w}Error downloading Chapter {ch_num}: {e}")
            return False

    for ch in range(start_chapter, end_chapter + 1):
        if not try_download(ch):
            failed_chapters.append(ch)

    while failed_chapters:
        print(f"\n{r}[{w}X{r}]{w} The following chapters failed: {failed_chapters}")
        retry = input(f"{T()}[{T2()}>{T()}]{w} Retry these chapters? (y/n): ").strip().lower()
        if retry != "y":
            break
        still_failed = []
        for ch in failed_chapters:
            if not try_download(ch):
                still_failed.append(ch)
        failed_chapters = still_failed

    if failed_chapters:
        print(f"\n{T()}[{T2()}!{T()}] {w}Some chapters still failed: {failed_chapters}")
    else:
        print(f"\n{gg}[{w}!{gg}] {w}All requested chapters downloaded successfully.")
        if download_format == "epub":
            save_as_epub(folder_path, novel_title)

    print(f'{T()}[{T2()}!{T()}] {w}Finished downloading the requested chapters.')

def handle_wetriedtls(driver, novel_url):
    try:
        driver.get(novel_url)
        time.sleep(2)

        novel_title = None
        try:
            title_element = driver.find_element(By.TAG_NAME, "h1")
            novel_title = title_element.text.strip()
        except:
            pass
        if not novel_title:
            try:
                novel_title = driver.title.split("|")[0].strip()
            except:
                novel_title = "Untitled_Novel"

        folder_name = novel_title.replace(':', ' -').replace('/', '-')
        folder_path = os.path.join(os.getcwd(), folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"{T()}[{T2()}!{T()}] {w}Created folder: {folder_path}")
        else:
            print(f"{y}[{w}!{y}] {w}Folder already exists: {folder_path}")

        try:
            chapter_list = driver.find_element(By.CSS_SELECTOR, "ul.grid.grid-cols-1.gap-3")
            chapter_links = chapter_list.find_elements(By.TAG_NAME, "a")
            latest_chap_num = max(int(a.get_attribute("href").split("/")[-1].replace("chapter-", "")) for a in chapter_links)
            print(f"{T()}[{T2()}!{T()}] {w}Latest available chapter: {latest_chap_num}")
        except Exception as e:
            print(f"{y}[{w}!{y}] {w}Could not determine latest chapter: {e}")
            latest_chap_num = None

        while True:
            time.sleep(1)
            start_chapter = int(input(f"\n{T()}[{T2()}>{T()}]{w} Enter the starting chapter: ").strip())
            end_chapter = int(input(f"{T()}[{T2()}>{T()}]{w} Enter the ending chapter: ").strip())
            if latest_chap_num and end_chapter > latest_chap_num:
                print(f"{y}[{w}!{y}] {w}You cannot download beyond chapter {latest_chap_num}.")
            else:
                break

        download_format = input(f"{T()}[{T2()}?{T()}]{w} Download format (txt/epub) [default txt]: ").strip().lower()
        if download_format not in ['txt', 'epub']:
            download_format = 'txt'

        failed_chapters = []

        def try_download(chap_num):
            chapter_url = f"{novel_url.rstrip('/')}/chapter-{chap_num}"
            chapter_title = f"Chapter {chap_num}"
            print(f"{T()}[{T2()}!{T()}] {w}Downloading {chapter_title} from {chapter_url}")
            driver.get(chapter_url)
            try:
                WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, "reader-container")))
                container = driver.find_element(By.ID, "reader-container")
                paragraphs = container.find_elements(By.TAG_NAME, "p")
                lines = [p.text.strip() for p in paragraphs if p.text.strip()]
                content = "\n\n".join(lines)
                save_to_file(os.path.join(folder_path, f"{chapter_title}.txt"), content)
                print(f"{T()}[{T2()}+{T()}] {w}Downloaded {chapter_title}")
                return True
            except Exception as e:
                print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}] {w}Error downloading {chapter_title}: {e}")
                return False
            finally:
                time.sleep(random.uniform(0.5, 1.2))

        for chap_num in range(start_chapter, end_chapter + 1):
            if not try_download(chap_num):
                failed_chapters.append(chap_num)

        while failed_chapters:
            print(f"\n{y}[{w}!{y}] {w}The following chapters failed: {failed_chapters}")
            retry = input(f"{T()}[{T2()}?{T()}]{w} Retry these chapters? (y/n): ").strip().lower()
            if retry != "y":
                break
            still_failed = []
            for ch in failed_chapters:
                if not try_download(ch):
                    still_failed.append(ch)
            failed_chapters = still_failed

        if failed_chapters:
            print(f"\n{Fore.RED}[{Fore.WHITE}!{Fore.RED}] {w}Some chapters still failed: {failed_chapters}")
        else:
            print(f"\n{T()}[{T2()}!{T()}] {w}All requested chapters downloaded successfully.")
            if download_format == "epub":
                save_as_epub(folder_path, novel_title)

        print(f"{T()}[{T2()}!{T()}] {w}Finished downloading chapters {start_chapter} to {end_chapter}.")

    except Exception as e:
        print(f"{r}[{w}X{r}]{w} Error in WetriedTLS handler: {e}")

def handle_helioscans(driver, novel_url):
    try:
        driver.get(novel_url)
        time.sleep(2)

        novel_title = None
        try:
            title_element = driver.find_element(By.TAG_NAME, "h1")
            novel_title = title_element.text.strip()
        except:
            pass
        if not novel_title:
            try:
                novel_title = driver.title.split("|")[0].strip()
            except:
                novel_title = "Untitled_Novel"
        novel_title = re.sub(r'(\s*[-:]\s*Chapter\s*\d+)$', '', novel_title, flags=re.IGNORECASE)

        folder_name = novel_title.replace(':', ' -').replace('/', '-')
        folder_path = os.path.join(os.getcwd(), folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"{T()}[{T2()}+{T()}] {w}Created folder: {folder_path}")
        else:
            print(f"{y}[{w}!{y}]{w} Folder already exists: {folder_path}")

        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, "chapters")))
        chapter_elements = driver.find_elements(By.CSS_SELECTOR, "#chapters a.chapter-el")

        chapters = []
        latest_free_chap_num = 0
        for elem in chapter_elements:
            try:
                elem.find_element(By.CSS_SELECTOR, "div.flex.gap-1.justify-center.items-center.w-fit.bg-yellow-200.text-yellow-600")
                is_paid = True
            except:
                is_paid = False

            if not is_paid:
                title = elem.get_attribute("title") or elem.text
                href = elem.get_attribute("href")
                if title and href:
                    chap_num_match = re.search(r'\d+', title)
                    if chap_num_match:
                        chap_num = int(chap_num_match.group())
                        if chap_num > latest_free_chap_num:
                            latest_free_chap_num = chap_num
                        chapters.append((chap_num, title.strip(), href.strip()))

        if not chapters:
            print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} No free chapters found.")
            return

        chapters.sort(key=lambda x: x[0])
        print(f"{T()}[{T2()}!{T()}] {w}Latest free chapter available: {latest_free_chap_num}")

        while True:
            start_chapter = int(input(f"\n{T()}[{T2()}>{T()}]{w} Enter the starting chapter: ").strip())
            end_chapter = int(input(f"{T()}[{T2()}>{T()}]{w} Enter the ending chapter: ").strip())
            if end_chapter > latest_free_chap_num:
                print(f"{y}[{w}!{y}]{w} You cannot download beyond chapter {latest_free_chap_num}.")
            else:
                break

        download_format = input(f"{T()}[{T2()}>{T()}]{w} Download format (txt/epub) [default txt]: ").strip().lower()
        if download_format not in ['txt', 'epub']:
            download_format = 'txt'

        selected = [(num, title, url) for (num, title, url) in chapters if start_chapter <= num <= end_chapter]
        if not selected:
            print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} No chapters in that range.")
            return

        failed_chapters = []

        def try_download(chap_num, chapter_title, chapter_url):
            print(f"{T()}[{T2()}!{T()}] {w}Downloading {chapter_title} from {chapter_url}")
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(chapter_url)
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#pages")))
                pages_container = driver.find_element(By.CSS_SELECTOR, "div#pages")
                reader_container = pages_container.find_element(By.CSS_SELECTOR, "div.novel-reader.default")
                paragraphs = reader_container.find_elements(By.TAG_NAME, "p")
                lines = [p.text.strip() for p in paragraphs if p.text.strip()]
                content = "\n\n".join(lines)
                save_to_file(os.path.join(folder_path, f"Chapter {chap_num}.txt"), content)
                print(f"{T()}[{T2()}+{T()}] {w}Downloaded {chapter_title}")
                return True
            except Exception as e:
                print(f"{r}[{w}X{r}]{w} Error downloading {chapter_title}: {e}")
                return False
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(random.uniform(0.5, 1.2))

        for chap_num, chapter_title, chapter_url in selected:
            if not try_download(chap_num, chapter_title, chapter_url):
                failed_chapters.append((chap_num, chapter_title, chapter_url))

        while failed_chapters:
            print(f"\n{y}[{w}!{y}]{w} The following chapters failed: {[ch[1] for ch in failed_chapters]}")
            retry = input(f"{T()}[{T2()}?{T()}]{w} Retry these chapters? (y/n): ").strip().lower()
            if retry != "y":
                break
            still_failed = []
            for chap_num, chapter_title, chapter_url in failed_chapters:
                if not try_download(chap_num, chapter_title, chapter_url):
                    still_failed.append((chap_num, chapter_title, chapter_url))
            failed_chapters = still_failed

        if failed_chapters:
            print(f"\n{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} Some chapters still failed: {[ch[1] for ch in failed_chapters]}")
        else:
            print(f"\n{gg}[{w}!{gg}]{w} All requested chapters downloaded successfully.")

        if download_format == "epub":
            save_as_epub(folder_path, novel_title)

        print(f"{T()}[{T2()}!{T()}]{w} Finished downloading chapters {start_chapter} to {end_chapter}.")

    except Exception as e:
        print(f"{r}[{w}X{r}]{w} Error in Helioscans handler: {e}")

def handle_webnoveltranslations(driver, novel_url=None):
    try:
        driver.get(novel_url)
        time.sleep(2)
        try:
            title_element = driver.find_element(By.TAG_NAME, "h1")
            novel_title = title_element.text.strip()
        except:
            novel_title = driver.title.split("|")[0].strip()
        novel_title = re.sub(r'(\s*[-:]\s*Chapter\s*\d+)$', '', novel_title, flags=re.IGNORECASE)

        folder_name = novel_title.replace(':', ' -').replace('/', '-')
        folder_path = os.path.join(os.getcwd(), folder_name)
        os.makedirs(folder_path, exist_ok=True)
        start_chapter = int(input(f"\n{T()}[{T2()}>{T()}]{w} Enter the starting chapter: ").strip())
        end_chapter = int(input(f"\n{T()}[{T2()}>{T()}]{w} Enter the ending chapter: ").strip())

        download_format = input(f"\n{T()}[{T2()}>{T()}]{w} Convert to epub or remain txt? (txt/epub): ").strip().lower()
        if download_format not in ['txt', 'epub']:
            download_format = 'txt'

        failed_chapters = []

        def try_download(chap_num):
            if novel_url.endswith("/"):
                chapter_url = f"{novel_url}chapter-{chap_num}/"
            else:
                chapter_url = f"{novel_url}/chapter-{chap_num}/"

            print(f"{T()}[{T2()}!{T()}]{w} Downloading Chapter {chap_num} ({chapter_url})")
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(chapter_url)
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#novel-chapter-container")))
                container = driver.find_element(By.CSS_SELECTOR, "div#novel-chapter-container")
                paragraphs = container.find_elements(By.TAG_NAME, "p")
                lines = [p.text.strip() for p in paragraphs if p.text.strip()]
                if not lines:
                    print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} No text found for Chapter {chap_num}, skipping.")
                    return False
                content = "\n\n".join(lines)
                save_to_file(os.path.join(folder_path, f"Chapter {chap_num}.txt"), content)
                print(f"{T()}[{T2()}!{T()}]{w} Downloaded Chapter {chap_num}")
                return True
            except Exception:
                print(f"Chapter {chap_num} not found or failed to load, skipping.")
                return False
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(random.uniform(0.5, 1.2))

        for chap_num in range(start_chapter, end_chapter + 1):
            if not try_download(chap_num):
                failed_chapters.append(chap_num)

        if failed_chapters:
            print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} The following chapters failed or were missing: {failed_chapters}")

        if download_format == "epub":
            save_as_epub(folder_path, novel_title)

        print(f"{T()}[{T2()}!{T()}]{w} Finished downloading chapters {start_chapter} to {end_chapter}.")

    except Exception as e:
        print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}]{w} Error in WebnovelTranslations handler: {e}")


def _novelpia_text(zh_text, en_text):
    return zh_text if SETTINGS.get("gui_language", "zh") == "zh" else en_text


def _novelpia_novel_id(novel_url):
    match = re.search(r"/novel/(\d+)", urlparse(novel_url).path)
    return match.group(1) if match else None


def _novelpia_safe_name(value):
    value = html.unescape(value or "")
    value = re.sub(r'[\\/*?:"<>|]', "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:140] or "Untitled"


def _novelpia_name_key(value):
    return re.sub(r"[\W_]+", "", html.unescape(value or "").casefold())


NOVELPIA_LOADING_MARKERS = (
    "소설 내용을 불러오고 있습니다",
    "소설 내용을 불러오고 있습니다.",
)

NOVELPIA_BASE64_NOISE_RE = re.compile(r"^[A-Za-z0-9+/_=-]{72,}$")


def _novelpia_line_is_noise(line):
    stripped = (line or "").strip()
    if not stripped or len(stripped) < 72:
        return False
    if not NOVELPIA_BASE64_NOISE_RE.fullmatch(stripped):
        return False
    return bool(re.search(r"[A-Z]", stripped) and re.search(r"[a-z]", stripped) and re.search(r"\d", stripped))


def _novelpia_clean_text(text):
    lines = []
    for line in (text or "").splitlines():
        if _novelpia_line_is_noise(line):
            continue
        lines.append(line.rstrip())
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _novelpia_text_has_noise(text):
    return any(_novelpia_line_is_noise(line) for line in (text or "").splitlines())


def _novelpia_content_is_placeholder(text):
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    if any(marker in cleaned for marker in NOVELPIA_LOADING_MARKERS):
        without_markers = cleaned
        for marker in NOVELPIA_LOADING_MARKERS:
            without_markers = without_markers.replace(marker, "")
        without_markers = re.sub(r"\[Illustration\]", "", without_markers, flags=re.IGNORECASE)
        without_markers = re.sub(r"커버\s*접기", "", without_markers)
        meaningful_lines = [
            line.strip()
            for line in without_markers.splitlines()
            if len(line.strip()) >= 20
        ]
        return len(meaningful_lines) < 3 and len(without_markers.strip()) < 240
    return False


def _novelpia_saved_file_is_valid(path):
    try:
        if not path or not os.path.exists(path) or os.path.getsize(path) <= 100:
            return False
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            sample = fh.read()
        return not _novelpia_content_is_placeholder(sample) and not _novelpia_text_has_noise(sample)
    except OSError:
        return False


def _novelpia_wait_for_episode_list(driver, timeout=45):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return !!document.querySelector('#episode_list #episode_table "
            "[id^=\"bookmark_\"]');"
        )
    )


def _novelpia_collect_current_page(driver):
    return driver.execute_script(
        """
        return Array.from(document.querySelectorAll('#episode_list #episode_table tr'))
          .map((row) => {
            const mark = row.querySelector('[id^="bookmark_"]');
            if (!mark) return null;
            const cell = mark.closest('td') || row;
            const onclick = cell.getAttribute('onclick') || '';
            const idMatch = (mark.id || '').match(/bookmark_(\\d+)/);
            const urlMatch = onclick.match(/\\/viewer\\/(\\d+)/);
            const chapterId = idMatch ? idMatch[1] : (urlMatch ? urlMatch[1] : '');
            if (!chapterId) return null;
            const titleNode = cell.querySelector('b');
            const title = (titleNode ? titleNode.innerText : '').trim();
            const rowText = (row.innerText || '').replace(/\\s+/g, ' ').trim();
            const epMatch = rowText.match(/EP\\.\\s*(\\d+)/i);
            return {
              id: chapterId,
              title: title,
              ep: epMatch ? Number(epMatch[1]) : null,
              kind: /BONUS/i.test(rowText) ? 'bonus' : 'episode'
            };
          }).filter(Boolean);
        """
    ) or []


def _novelpia_collect_notices(driver):
    return driver.execute_script(
        """
        return Array.from(document.querySelectorAll('.notice_table tr'))
          .map((row) => {
            const cell = Array.from(row.querySelectorAll('[onclick]')).find((el) =>
              (el.getAttribute('onclick') || '').includes('/viewer/'));
            if (!cell) return null;
            const match = (cell.getAttribute('onclick') || '').match(/\\/viewer\\/(\\d+)/);
            if (!match) return null;
            const titleNode = cell.querySelector('b');
            return {
              id: match[1],
              title: (titleNode ? titleNode.innerText : '').trim(),
              ep: null,
              kind: 'notice'
            };
          }).filter(Boolean);
        """
    ) or []


def _novelpia_page_count(driver):
    value = driver.execute_script(
        """
        const box = document.querySelector('.select_episode_box');
        const text = box ? (box.textContent || '') : '';
        const match = text.match(/\\/\\s*(\\d+)/);
        if (match) return Number(match[1]);
        const values = Array.from(document.querySelectorAll('.page-link'))
          .map((el) => Number((el.innerText || '').trim()))
          .filter(Number.isFinite);
        return values.length ? Math.max(...values) : 1;
        """
    )
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def _novelpia_go_to_list_page(driver, page_number, novel_id, previous_first_id=None):
    clicked = driver.execute_script(
        """
        const input = document.querySelector('#select_episode_no');
        const button = document.querySelector('.select_episode_box .btn-page-go');
        if (!input || !button) return false;
        input.value = arguments[0];
        input.dispatchEvent(new Event('input', {bubbles: true}));
        button.click();
        return true;
        """,
        page_number,
    )
    if not clicked:
        raise RuntimeError("Novelpia page-jump controls were not found.")

    target_index = str(page_number - 1)

    def page_changed(d):
        state = d.execute_script(
            """
            const mark = document.querySelector('#episode_list #episode_table [id^="bookmark_"]');
            return {
              page: localStorage.getItem(arguments[0]),
              first: mark ? mark.id.replace('bookmark_', '') : ''
            };
            """,
            f"novel_page_{novel_id}",
        )
        if not state or state.get("page") != target_index:
            return False
        return not previous_first_id or state.get("first") != previous_first_id

    WebDriverWait(driver, 45).until(page_changed)


def _novelpia_extract_rendered_text(driver):
    return driver.execute_script(
        """
        const source = document.querySelector('#novel_text');
        if (!source) return '';
        let text = (source.innerText || source.textContent || '')
          .replace(/\\u00a0/g, ' ')
          .replace(/[ \\t]+\\n/g, '\\n')
          .replace(/\\n{3,}/g, '\\n\\n')
          .trim();
        const imageCount = source.querySelectorAll('img').length;
        if (imageCount) {
          const markers = Array.from({length: imageCount}, () => '[Illustration]').join('\\n');
          text = text ? `${text}\\n\\n${markers}` : markers;
        }
        return text;
        """
    ) or ""


def _novelpia_normalize_viewer_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _novelpia_navigate(driver, target_url):
    try:
        driver.get(target_url)
    except TimeoutException:
        # Keep the already rendered page instead of refreshing repeatedly.
        driver.execute_script("window.stop();")


def _novelpia_viewer_state(driver):
    state = driver.execute_script(
        """
        const root = document.querySelector('#novel_text');
        const rootText = root ? (root.innerText || root.textContent || '') : '';
        const normalizedRootText = rootText
          .replace(/\\u00a0/g, ' ')
          .replace(/\\s+/g, ' ')
          .trim();
        const isLoading = normalizedRootText.includes('소설 내용을 불러오고 있습니다');
        const bodyText = (document.body ? (document.body.innerText || document.body.textContent || '') : '')
          .replace(/\\s+/g, ' ')
          .trim();
        const visible = !!root && Number.parseFloat(getComputedStyle(root).opacity || '1') > 0;
        const imageCount = root ? root.querySelectorAll('img').length : 0;
        const textWithoutLoading = normalizedRootText
          .replace(/소설 내용을 불러오고 있습니다\\.?/g, '')
          .replace(/커버\\s*접기/g, '')
          .trim();
        const hasContent = visible && !isLoading && (
          textWithoutLoading.length >= 120 ||
          (textWithoutLoading.length >= 60 && imageCount > 0)
        );
        return {
          path: location.pathname || '',
          rootText: normalizedRootText,
          isLoading,
          imageCount,
          hasContent,
          textTail: bodyText.slice(-1000)
        };
        """
    ) or {}
    text = str(state.get("textTail") or "")
    lowered = text.lower()
    login_markers = (
        "로그인이 필요",
        "로그인 후",
        "로그인을 해주세요",
        "로그인해주세요",
        "로그인 하셔야",
        "login",
    )
    access_markers = (
        "회원",
        "플러스",
        "구매",
        "보유하신 코인",
        "열람권",
        "본인인증",
        "성인 인증",
        "권한",
        "이용하실 수 없습니다",
    )
    state["loginRequired"] = (
        not state.get("hasContent")
        and (
            any(marker in text for marker in login_markers)
            or any(marker in lowered for marker in ("sign in", "log in"))
            or any(marker in text for marker in access_markers)
        )
    )
    return state


def _novelpia_load_chapter(driver, chapter, base_url):
    _novelpia_navigate(driver, urljoin(base_url, f"/viewer/{chapter['id']}"))

    def viewer_ready(d):
        if not urlparse(d.current_url).path.startswith("/viewer/"):
            return True
        state = _novelpia_viewer_state(d)
        return bool(state.get("hasContent") or state.get("loginRequired"))

    try:
        WebDriverWait(driver, 50).until(viewer_ready)
    except TimeoutException as exc:
        current_url = getattr(driver, "current_url", "")
        try:
            state = _novelpia_viewer_state(driver)
            detail = state.get("textTail") or current_url
        except Exception:
            detail = current_url
        raise TimeoutException(
            _novelpia_text(
                f"章节正文等待超时：{current_url}\n页面可见文本末尾：{detail}",
                f"Timed out waiting for rendered chapter text: {current_url}\nVisible page tail: {detail}",
            )
        ) from exc
    state = _novelpia_viewer_state(driver)
    if state.get("loginRequired"):
        raise PermissionError(_novelpia_text(
            f"该章节需要登录、会员/订阅或认证权限：{driver.current_url}\n页面提示：{state.get('textTail', '')}",
            f"This chapter requires login, membership/subscription, or verification access: {driver.current_url}\nPage says: {state.get('textTail', '')}",
        ))
    if not urlparse(driver.current_url).path.startswith("/viewer/"):
        raise PermissionError(_novelpia_text(
            "网页跳离了阅读器，可能需要登录、实名或订阅权限。",
            "The page left the viewer; login, age verification, or subscription access may be required.",
        ))

    text = _novelpia_clean_text(_novelpia_extract_rendered_text(driver))
    if not text or _novelpia_content_is_placeholder(text):
        visible = (driver.find_element(By.TAG_NAME, "body").text or "").strip()
        raise PermissionError(
            _novelpia_text("没有读到正文，已停止以避免反复请求：", "No chapter text was rendered; stopping: ")
            + (visible[-500:] if visible else driver.current_url)
        )
    return text


def handle_novelpia(driver, novel_url):
    """Download Novelpia through its rendered web UI, one visible page at a time."""
    novel_id = _novelpia_novel_id(novel_url)
    if not novel_id:
        print(f"{r}[{w}X{r}]{w} " + _novelpia_text(
            "网址应为 https://novelpia.com/novel/作品编号",
            "Expected a URL like https://novelpia.com/novel/12345",
        ))
        return

    parsed = urlparse(novel_url)
    base_url = f"{parsed.scheme or 'https'}://{parsed.netloc or 'novelpia.com'}"
    novel_url = f"{base_url}/novel/{novel_id}"
    print(f"{T()}[{T2()}!{T()}]{w} " + _novelpia_text(
        "正在用可见 Chrome 打开 Novelpia 作品页……",
        "Opening the Novelpia novel in visible Chrome...",
    ))
    _novelpia_navigate(driver, novel_url)
    WebDriverWait(driver, 45).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )

    if not driver.get_cookie("LOGINKEY"):
        print(_novelpia_text(
            "未检测到登录态。会员/订阅章节必须先在这个浏览器窗口里正常登录；验证码请手动完成。"
            "只抓免费章节才可以未登录继续。",
            "No saved login was detected. Log in normally in the browser for chapters your account can access; "
            "solve any CAPTCHA manually. Continue as a guest only for free chapters.",
        ))
        input(_novelpia_text(
            "登录完成后按回车继续（如果只抓免费章，也可直接回车）：",
            "Press Enter after logging in (or press Enter directly for free chapters only): ",
        ))
        _novelpia_navigate(driver, novel_url)

    _novelpia_wait_for_episode_list(driver)
    title = driver.execute_script(
        """
        if (window.ENP_VAR && ENP_VAR.collect && ENP_VAR.collect.productName) {
          return ENP_VAR.collect.productName;
        }
        const meta = document.querySelector('meta[property="og:title"]');
        return meta ? meta.content : document.title;
        """
    ) or f"Novelpia_{novel_id}"
    if title.startswith("노벨피아") and " - " in title:
        title = title.rsplit(" - ", 1)[-1]
    title = _novelpia_safe_name(title)

    range_text = input(_novelpia_text(
        "下载范围（如 1-50；留空为全部）：",
        "Episode range (for example 1-50; blank means all): ",
    )).strip()
    start_ep, end_ep = 1, None
    if range_text:
        range_match = re.fullmatch(r"\s*(\d+)\s*(?:[-~～]\s*(\d+)\s*)?", range_text)
        if not range_match:
            raise ValueError(_novelpia_text("下载范围格式无效。", "Invalid episode range."))
        start_ep = int(range_match.group(1))
        end_ep = int(range_match.group(2) or range_match.group(1))
        if end_ep < start_ep:
            start_ep, end_ep = end_ep, start_ep

    current_page = driver.execute_script(
        "return localStorage.getItem(arguments[0]);", f"novel_page_{novel_id}"
    )
    if current_page not in (None, "0"):
        current = _novelpia_collect_current_page(driver)
        _novelpia_go_to_list_page(
            driver, 1, novel_id, current[0]["id"] if current else None
        )

    current = _novelpia_collect_current_page(driver)
    numbered = [item for item in current if item.get("ep") is not None]
    if len(numbered) >= 2 and numbered[0]["ep"] > numbered[-1]["ep"]:
        previous_id = current[0]["id"] if current else None
        clicked = driver.execute_script(
            """
            const button = Array.from(document.querySelectorAll('[onclick]')).find((el) =>
              (el.getAttribute('onclick') || '').includes("episode_sort('down')"));
            if (!button) return false;
            button.click();
            return true;
            """
        )
        if clicked:
            WebDriverWait(driver, 45).until(
                lambda d: (
                    (_novelpia_collect_current_page(d) or [{}])[0].get("id")
                    not in (None, previous_id)
                )
            )

    notices = _novelpia_collect_notices(driver)
    total_pages = _novelpia_page_count(driver)
    print(_novelpia_text(
        f"作品：{title}；章节列表共 {total_pages} 页。正在逐页读取网页列表……",
        f"Novel: {title}; {total_pages} chapter-list page(s). Reading the rendered list...",
    ))

    chapters = []
    seen_ids = set()
    for page_number in range(1, total_pages + 1):
        if page_number > 1:
            current = _novelpia_collect_current_page(driver)
            previous_id = current[0]["id"] if current else None
            _novelpia_go_to_list_page(driver, page_number, novel_id, previous_id)
            time.sleep(random.uniform(1.2, 2.4))
        for chapter in _novelpia_collect_current_page(driver):
            if chapter["id"] not in seen_ids:
                chapters.append(chapter)
                seen_ids.add(chapter["id"])
        print(_novelpia_text(
            f"  列表页 {page_number}/{total_pages}：累计 {len(chapters)} 章",
            f"  List page {page_number}/{total_pages}: {len(chapters)} chapter(s)",
        ))

    last_ep = 0
    for chapter in chapters:
        if chapter.get("ep") is not None:
            last_ep = chapter["ep"]
        chapter["range_ep"] = last_ep
    selected = [
        chapter for chapter in chapters
        if chapter.get("range_ep", 0) >= start_ep
        and (end_ep is None or chapter.get("range_ep", 0) <= end_ep)
    ]
    jobs = notices + selected
    if not jobs:
        print(f"{r}[{w}X{r}]{w} " + _novelpia_text(
            "所选范围没有章节。", "No chapters matched the selected range."
        ))
        return

    folder_path = os.path.join(os.getcwd(), _novelpia_safe_name(f"[{novel_id}] {title}"))
    os.makedirs(folder_path, exist_ok=True)
    delay_min = max(2.0, float(SETTINGS.get("novelpia_delay_min", 4.0)))
    delay_max = max(delay_min, float(SETTINGS.get("novelpia_delay_max", 7.0)))
    print(_novelpia_text(
        f"输出：{folder_path}\n单线程、单标签页；每章随机等待 {delay_min:.1f}–{delay_max:.1f} 秒。"
        "遇到登录、验证或权限页会立即停止。",
        f"Output: {folder_path}\nOne tab and one request at a time; random {delay_min:.1f}-{delay_max:.1f}s "
        "pause per chapter. Login, verification, or access pages stop the run.",
    ))

    notice_no = bonus_no = completed = 0
    for index, chapter in enumerate(jobs, 1):
        if chapter["kind"] == "notice":
            notice_no += 1
            prefix = f"Notice {notice_no:04d}"
            file_prefix = f"{notice_no:03d} - Notice"
        elif chapter["kind"] == "bonus":
            bonus_no += 1
            prefix = f"Bonus {bonus_no:04d}"
            file_prefix = f"{len(notices) + int(chapter.get('range_ep', 0)):03d}.{bonus_no} - BONUS"
        else:
            prefix = f"Episode {int(chapter['ep']):04d}"
            file_prefix = f"{len(notices) + int(chapter['ep']):03d}"

        safe_title = _novelpia_safe_name(chapter.get("title") or prefix)
        file_path = os.path.join(folder_path, f"{file_prefix} - {safe_title}.txt")
        legacy_path = next(
            (
                path for path in list_txt_files(folder_path)
                if _novelpia_name_key(os.path.splitext(os.path.basename(path))[0]).endswith(
                    _novelpia_name_key(safe_title)
                )
                and _novelpia_saved_file_is_valid(path)
            ),
            None,
        )
        if legacy_path and os.path.normcase(legacy_path) != os.path.normcase(file_path):
            print(
                f"{y}[{w}~{y}]{w} {prefix}: "
                + _novelpia_text(
                    f"检测到已有章节 {os.path.basename(legacy_path)}，跳过。",
                    f"matching existing chapter {os.path.basename(legacy_path)}; skipped.",
                )
            )
            completed += 1
            continue
        if _novelpia_saved_file_is_valid(file_path):
            print(f"{y}[{w}~{y}]{w} {prefix}: " + _novelpia_text("已存在，跳过。", "already saved; skipped."))
            completed += 1
            continue
        if os.path.exists(file_path):
            print(f"{y}[{w}!{y}]{w} {prefix}: " + _novelpia_text(
                "检测到旧的无效或未清洗文件，将重新抓取覆盖。",
                "old invalid or unclean file detected; re-downloading.",
            ))

        print(f"{T()}[{T2()}!{T()}]{w} [{index}/{len(jobs)}] {prefix} - {safe_title}")
        try:
            body = _novelpia_load_chapter(driver, chapter, base_url)
        except (PermissionError, TimeoutException) as exc:
            print(f"{r}[{w}X{r}]{w} {exc}")
            print(_novelpia_text(
                "为避免连续触发站点保护，本次任务已在首个失败章节处停止；已保存文件可直接续跑。",
                "To avoid repeated protection triggers, the run stopped at the first failed chapter. "
                "Saved files can be resumed.",
            ))
            break

        content = body if body.startswith(safe_title) else f"{safe_title}\n\n{body}"
        save_to_file(file_path, content.rstrip() + "\n")
        completed += 1
        if index < len(jobs):
            wait_seconds = random.uniform(delay_min, delay_max)
            print(_novelpia_text(
                f"  已保存；等待 {wait_seconds:.1f} 秒……",
                f"  Saved; waiting {wait_seconds:.1f}s...",
            ))
            time.sleep(wait_seconds)

    print(_novelpia_text(
        f"已保存/已存在 {completed}/{len(jobs)} 个章节文件。",
        f"Saved/already present: {completed}/{len(jobs)} chapter file(s).",
    ))
    if completed == len(jobs) and SETTINGS.get("download_format") == "epub":
        save_as_epub(folder_path, title)


# ─────────────────────────────────────────────
#  SITE HANDLER REGISTRY + DISPATCHER
# ─────────────────────────────────────────────

SITE_HANDLERS = {
    'novelpia.com': handle_novelpia,
    'novelfire': handle_novelfire,
    'wetriedtls': handle_wetriedtls,
    'helioscans': handle_helioscans,
    'webnoveltranslations': handle_webnoveltranslations,
}

def dispatch_handler(driver, novel_url):
    url_lower = novel_url.lower()
    # sbxh uses saved settings — no redundant prompts
    if 'sbxh' in url_lower:
        do_translate = SETTINGS["translate"]
        handle_sbxh2(driver, novel_url, do_translate)
        return

    for site_key, handler_func in SITE_HANDLERS.items():
        if site_key in url_lower:
            handler_func(driver, novel_url)
            return

    print(f"{r}[{w}X{r}]{w} Not a supported site.")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    global chrome_driver_path
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        Spinner()
        os.system('cls' if os.name == 'nt' else 'clear')

        titlecard = r"""
 ▐ ▄        ▌ ▐·▄▄▄ .▄▄▌      .▄▄ ·  ▄▄· ▄▄▄   ▄▄▄·  ▄▄▄·▄▄▄ .▄▄▄  
•█▌▐█▪     ▪█·█▌▀▄.▀·██•      ▐█ ▀. ▐█ ▌▪▀▄ █·▐█ ▀█ ▐█ ▄█▀▄.▀·▀▄ █·
▐█▐▐▌ ▄█▀▄ ▐█▐█•▐▀▀▪▄██▪      ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▄█▀▀█  ██▀·▐▀▀▪▄▐▀▀▄ 
██▐█▌▐█▌.▐▌ ███ ▐█▄▄▌▐█▌▐▌    ▐█▄▪▐█▐███▌▐█•█▌▐█ ▪▐▌▐█▪·•▐█▄▄▌▐█•█▌
▀▀ █▪ ▀█▄▀▪. ▀   ▀▀▀ .▀▀▀      ▀▀▀▀ ·▀▀▀ .▀  ▀ ▀  ▀ .▀    ▀▀▀ .▀  ▀                       
"""
        namecard = r"""
  ___        _    ___ _    _ _   _         __ _    _    
 | _ )_  _  (_)  / __(_)__| | |_| |_  ___ / _(_)__| |_  
 | _ \ || |  _  | (__| / _` |  _| ' \/ -_)  _| (_-< ' \ 
 |___/\_, | (_)  \___|_\__,_|\__|_||_\___|_| |_/__/_||_|
      |__/                                                                                
"""
        faded_title = _apply_fade(titlecard)
        faded_name  = _apply_fade(namecard)
        print(faded_title)
        time.sleep(.02)
        print(faded_name)
        time.sleep(.02)

        print(f'{T()}[{T2()}!{T()}]{Fore.WHITE} Information: To reset driver path please type "RESET". To Exit type "EXIT"')
        time.sleep(.07)
        print(f'''
{T()}[{T2()}1{T()}]{w} Scrape a novel  {Fore.RESET}|{Fore.RESET}{T()}[{T2()}2{T()}]{w} Convert txt to epub   {Fore.RESET}|{Fore.RESET}{T()}[{T2()}3{T()}]{w} Settings
''')

        choice = input(f'{T()}[{T2()}>{T()}]{w} What would you like to do?: ').strip()

        if choice.lower() == 'exit':
            os.system('cls' if os.name == 'nt' else 'clear')
            Spinner()
            time.sleep(.2)
            sys.exit(0)

        if choice.lower() == 'reset':
            chrome_driver_path = "NONE"
            save_config()
            print(f"{T()}[{T2()}!{T()}] {w}Driver path has been reset to NONE")
            time.sleep(.67)
            press_any_key()

        if choice == '1':
            os.system('cls' if os.name == 'nt' else 'clear')
            time.sleep(.2)
            Spinner()
            time.sleep(.09)
            os.system('cls' if os.name == 'nt' else 'clear')
            scrapetitle = r"""
  /$$$$$$                                                  
 /$$__  $$                                                 
| $$  \__/  /$$$$$$$  /$$$$$$  /$$$$$$   /$$$$$$   /$$$$$$ 
|  $$$$$$  /$$_____/ /$$__  $$|____  $$ /$$__  $$ /$$__  $$
 \____  $$| $$      | $$  \__/ /$$$$$$$| $$  \ $$| $$$$$$$$
 /$$  \ $$| $$      | $$      /$$__  $$| $$  | $$| $$_____/
|  $$$$$$/|  $$$$$$$| $$     |  $$$$$$$| $$$$$$$/|  $$$$$$$
 \______/  \_______/|__/      \_______/| $$____/  \_______/
                                       | $$                
                                       | $$                
                                       |__/                
"""
            faded_scrapetitle = _apply_fade(scrapetitle)
            print(faded_scrapetitle)
            novel_url = input(f"{T()}[{T2()}>{T()}]{w} Enter the novel URL (0 to go back, EXIT to exit): ").strip()
            if novel_url == '0' or novel_url.lower() == 'back':
                continue
            if novel_url.lower() == 'exit':
                continue

            # Check supported sites (sbxh included)
            url_lower = novel_url.lower()
            matched = 'sbxh' in url_lower
            if not matched:
                for site_key in SITE_HANDLERS:
                    if site_key in url_lower:
                        matched = True
                        break

            if not matched:
                print(f"{r}[{w}X{r}]{w} Not a supported site. Please enter a valid URL.")
                time.sleep(2)
                continue

            sys.stderr = open(os.devnull, 'w')
            is_sbxh = 'sbxh' in url_lower
            is_novelpia = 'novelpia.com' in url_lower
            driver = None

            if is_sbxh:
                # ── undetected-chromedriver for Cloudflare sites ──────────
                # IMPORTANT: uc MUST manage its own chromedriver — do NOT pass
                # the path from config here.  uc downloads a patched driver that
                # matches your installed Chrome version and strips all automation
                # flags (navigator.webdriver, missing plugins, chrome.runtime,
                # etc).  Passing a regular chromedriver breaks the patching and
                # causes the infinite CF-challenge loop you saw.
                print(f"{T()}[{T2()}!{T()}]{w} Launching undetected Chrome for Cloudflare bypass …")
                print(f"{T()}[{T2()}!{T()}]{w} uc is managing its own driver — this is intentional.")
                try:
                    chrome_major = get_chrome_major_version()
                    print(f"{T()}[{T2()}!{T()}]{w} Detected Chrome major version: {chrome_major}")
                    uc_options = uc.ChromeOptions()
                    # NOTE: uc.ChromeOptions does NOT support add_experimental_option —
                    # uc patches those flags internally. Adding them here breaks the driver.
                    uc_options.add_argument("--disable-blink-features=AutomationControlled")
                    uc_options.add_argument("--disable-notifications")
                    uc_options.add_argument("--disable-popup-blocking")
                    uc_options.add_argument("--start-maximized")
                    driver = uc.Chrome(
                        options=uc_options,
                        # driver_executable_path intentionally omitted — let uc
                        # auto-download the correct patched driver for your Chrome
                        headless=False,
                        use_subprocess=True,
                        version_main=chrome_major,
                    )
                    configure_sbxh_browser(driver)
                except Exception as e:
                    print(f"{r}[{w}X{r}]{w} Failed to launch undetected Chrome: {e}")
                    print(f"{y}[{w}!{y}]{w} Run:  pip install undetected-chromedriver --upgrade")
                    time.sleep(3)
                    continue
            elif is_novelpia:
                # Novelpia runs visibly with a dedicated persistent profile.
                # Login, age checks, and CAPTCHA are completed by the user in
                # the normal page; no LOGINKEY or password is stored by Nibble.
                try:
                    driver = create_plain_chrome_driver(create_novelpia_chrome_options())
                except (ValueError, RuntimeError, selenium.common.exceptions.WebDriverException) as e:
                    print(f"{r}[{w}X{r}]{w} Could not launch the Novelpia browser: {e}")
                    time.sleep(3)
                    continue
            else:
                # ── plain selenium for all other sites ────────────────────
                chrome_options = Options()
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--disable-images")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--blink-settings=imagesEnabled=false")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
                prefs = {
                    "profile.managed_default_content_settings.images": 2,
                    "profile.managed_default_content_settings.fonts": 2,
                    "profile.managed_default_content_settings.media_stream": 2,
                }
                chrome_options.add_experimental_option("prefs", prefs)
                try:
                    driver = create_plain_chrome_driver(chrome_options)
                except (ValueError, RuntimeError, selenium.common.exceptions.WebDriverException):
                    print(f"{Fore.RED}[{Fore.WHITE}!{Fore.RED}] {w}ChromeDriver not found or invalid.")
                    reset_choice = input(f"{T()}[{T2()}?{T()}]{w} Reset driver path? (y/n): ").strip().lower()
                    if reset_choice == 'y':
                        chrome_driver_path = "NONE"
                        save_config()
                        print(f"{T()}[{T2()}!{T()}] {w}Driver path reset. Please run again.")
                        time.sleep(3)
                        continue
                    else:
                        print(f"{y}[{w}!{y}] {w}Cannot proceed without a valid ChromeDriver.")
                        time.sleep(2)
                        continue

            try:
                dispatch_handler(driver, novel_url)
            finally:
                driver.quit()
                time.sleep(2)
                press_any_key()
                os.system('cls' if os.name == 'nt' else 'clear')

        if choice == '2':
            os.system('cls' if os.name == 'nt' else 'clear')
            time.sleep(0.2)
            Spinner()
            time.sleep(0.09)
            os.system('cls' if os.name == 'nt' else 'clear')
            conversiontitle = r"""
 $$$$$$\                                                     $$\     
$$  __$$\                                                    $$ |    
$$ /  \__| $$$$$$\  $$$$$$$\ $$\    $$\  $$$$$$\   $$$$$$\ $$$$$$\   
$$ |      $$  __$$\ $$  __$$\\$$\  $$  |$$  __$$\ $$  __$$\\_$$  _|  
$$ |      $$ /  $$ |$$ |  $$ |\$$\$$  / $$$$$$$$ |$$ |  \__| $$ |    
$$ |  $$\ $$ |  $$ |$$ |  $$ | \$$$  /  $$   ____|$$ |       $$ |$$\ 
\$$$$$$  |\$$$$$$  |$$ |  $$ |  \$  /   \$$$$$$$\ $$ |       \$$$$  |
 \______/  \______/ \__|  \__|   \_/     \_______|\__|        \____/
"""
            faded_conversiontitle = _apply_fade(conversiontitle)
            print(faded_conversiontitle)

            folders = [f for f in os.listdir(os.getcwd()) if os.path.isdir(f)]
            if not folders:
                print(f"{r}[{w}X{r}]{w} No folders found in current directory.")
                press_any_key()
                continue

            print(f"{T()}[{T2()}!{T()}]{w} Available folders:")
            for i, folder in enumerate(folders, 1):
                print(f"  {T()}[{T2()}{i}{T()}]{w} {folder}")
            print(f"  {T()}[{T2()}0{T()}]{w} Back to main menu")

            while True:
                folder_choice = input(f"{T()}[{T2()}>{T()}]{w} Select a folder by number (0 to go back): ").strip()
                if folder_choice == '0':
                    break
                if folder_choice.isdigit() and 1 <= int(folder_choice) <= len(folders):
                    folder_path = folders[int(folder_choice) - 1]
                    break
                else:
                    print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} Invalid choice.{Fore.RESET}")
            else:
                press_any_key()
                continue

            if folder_choice == '0':
                continue

            txt_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.txt')]
            # Support both "Chapter N" and "Episode N" filenames
            chapter_nums = {}
            chapter_pattern = re.compile(r'(?:Chapter|Episode)\s*(\d+)', re.IGNORECASE)

            for file in txt_files:
                match = chapter_pattern.search(file)
                if match:
                    chap_num = int(match.group(1))
                    chapter_nums[chap_num] = file

            if not chapter_nums:
                print(f"{r}[{w}X{r}]{w} No chapters found in this folder.")
                press_any_key()
                continue

            sorted_chapters = sorted(chapter_nums.keys())
            ranges = []
            start = sorted_chapters[0]
            prev = start

            for num in sorted_chapters[1:]:
                if num != prev + 1:
                    ranges.append((start, prev))
                    start = num
                prev = num
            ranges.append((start, prev))

            range_strings = [f"{s} - {e}" if s != e else f"{s}" for s, e in ranges]
            print(f"{T()}[{T2()}!{T()}]{w} Chapters {', '.join(range_strings)} are available for conversion.")

            while True:
                conv_choice = input(f"{T()}[{T2()}>{T()}]{w} Convert all chapters or specific range? (ALL / SP / 0 to go back): {Fore.RESET}").strip().upper()
                if conv_choice == '0':
                    break
                if conv_choice in ['ALL', 'SP']:
                    break
                else:
                    print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} Enter ALL, SP, or 0 to go back.{Fore.RESET}")

            if conv_choice == '0':
                continue

            if conv_choice == 'ALL':
                selected_chapters = sorted_chapters
            else:
                while True:
                    try:
                        start_raw = input(f"{T()}[{T2()}>{T()}]{w} Start chapter (0 to go back): {Fore.RESET}").strip()
                        if start_raw == '0':
                            break
                        end_raw = input(f"{T()}[{T2()}>{T()}]{w} End chapter (0 to go back): {Fore.RESET}").strip()
                        if end_raw == '0':
                            break
                        start_chap = int(start_raw)
                        end_chap   = int(end_raw)
                        if start_chap in chapter_nums and end_chap in chapter_nums and start_chap <= end_chap:
                            selected_chapters = [c for c in sorted_chapters if start_chap <= c <= end_chap]
                            break
                        else:
                            print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} Invalid range.{Fore.RESET}")
                    except ValueError:
                        print(f"{Fore.RED}[{Fore.WHITE}X{Fore.RED}]{w} Enter valid numbers.{Fore.RESET}")
                else:
                    continue  # back was chosen inside range picker — skip epub build

            book = epub.EpubBook()
            book.set_identifier(folder_path)
            book.set_title(folder_path)
            book.set_language('en')
            book.add_author("TopStop5's Novelscraper")
            book.add_metadata('DC', 'title', folder_path)
            book.add_metadata('DC', 'creator', 'Novelscraper by TopStop5', {'id': 'creator', 'opf:role': 'aut'})

            for chap_num in selected_chapters:
                file_path = os.path.join(folder_path, chapter_nums[chap_num])
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().replace('\n', '<br/>')
                chapter = epub.EpubHtml(title=f"Chapter {chap_num}", file_name=f"chapter_{chap_num}.xhtml", lang='en')
                chapter.content = f"<h1>Chapter {chap_num}</h1><p>{content}</p>"
                book.add_item(chapter)
                book.spine.append(chapter)
                book.toc.append(epub.Link(f"chapter_{chap_num}.xhtml", f"Chapter {chap_num}", f"chap_{chap_num}"))

            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            epub_name = os.path.join(folder_path, f"{folder_path}.epub")
            epub.write_epub(epub_name, book)
            print(f"EPUB created: {epub_name}")
            press_any_key()

        if choice == '3':
            # ── SETTINGS ──────────────────────────────────────────────────
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                time.sleep(0.1)
                Spinner()
                time.sleep(0.05)
                os.system('cls' if os.name == 'nt' else 'clear')

                settingstitle = r"""
  $$$$$$\             $$\     $$\     $$\                               
 $$  __$$\            $$ |    $$ |    \__|                              
 $$ /  \__| $$$$$$\ $$$$$$\ $$$$$$\   $$\ $$$$$$$\   $$$$$$\   $$$$$$$\ 
 \$$$$$$\  $$  __$$\\_$$  _|\_$$  _|  $$ |$$  __$$\ $$  __$$\ $$  _____|
  \____$$\ $$$$$$$$ | $$ |    $$ |    $$ |$$ |  $$ |$$ /  $$ |\$$$$$$\  
 $$\   $$ |$$   ____| $$ |$$\ $$ |$$\ $$ |$$ |  $$ |$$ |  $$ | \____$$\ 
 \$$$$$$  |\$$$$$$$\  \$$$$  |\$$$$  |$$ |$$ |  $$ |\$$$$$$$ |$$$$$$$  |
  \______/  \_______|  \____/  \____/ \__|\__|  \__| \____$$ |\_______/ 
                                                     $$\   $$ |          
                                                     \$$$$$$  |          
                                                      \______/           
"""
                print(_apply_fade(settingstitle))

                # Current values
                fmt_val = SETTINGS["download_format"].upper()
                tl_val  = f"{Fore.LIGHTGREEN_EX}ON{Fore.RESET}" if SETTINGS["translate"] else f"{Fore.RED}OFF{Fore.RESET}"
                th_val  = SETTINGS["theme"]

                print(f"{T()}┌─ Current Settings ─────────────────────────────{Fore.RESET}")
                print(f"  {T()}[{T2()}1{T()}]{T2()} Download Format : {T()}{fmt_val}{Fore.RESET}")
                print(f"  {T()}[{T2()}2{T()}]{T2()} Translate KO→EN : {tl_val}")
                print(f"  {T()}[{T2()}3{T()}]{T2()} Theme           : {T()}{th_val}{Fore.RESET}")
                print(f"  {T()}[{T2()}4{T()}]{T2()} Reset all to defaults{Fore.RESET}")
                print(f"  {T()}[{T2()}0{T()}]{T2()} Back to main menu{Fore.RESET}")
                print(f"{T()}└─────────────────────────────────────────────────{Fore.RESET}\n")

                s = input(f"{T()}[{T2()}>{T()}]{T2()} Choose a setting to change: {Fore.RESET}").strip().lower()

                if s == '1':
                    cur = SETTINGS["download_format"]
                    nxt = "epub" if cur == "txt" else "txt"
                    SETTINGS["download_format"] = nxt
                    save_config()
                    print(f"\n{T()}[{T2()}!{T()}]{T2()} Download format set to {T()}{nxt.upper()}{Fore.RESET}")
                    time.sleep(0.8)

                elif s == '2':
                    SETTINGS["translate"] = not SETTINGS["translate"]
                    save_config()
                    state = f"{Fore.LIGHTGREEN_EX}ON{Fore.RESET}" if SETTINGS["translate"] else f"{Fore.RED}OFF{Fore.RESET}"
                    print(f"\n{T()}[{T2()}!{T()}]{T2()} Translation {state}")
                    time.sleep(0.8)

                elif s == '3':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    themepickertitle = r"""
 $$$$$$$$\ $$\                                                 
 \__$$  __|$$ |                                                
    $$ |   $$$$$$$\   $$$$$$\  $$$$$$\$$$$\   $$$$$$\         
    $$ |   $$  __$$\ $$  __$$\ $$  _$$  _$$\ $$  __$$\        
    $$ |   $$ |  $$ |$$$$$$$$ |$$ / $$ / $$ |$$$$$$$$ |       
    $$ |   $$ |  $$ |$$   ____|$$ | $$ | $$ |$$   ____|       
    $$ |   $$ |  $$ |\$$$$$$$\ $$ | $$ | $$ |\$$$$$$$\        
    \__|   \__|  \__| \_______|\__| \__| \__| \_______|       
"""
                    print(_apply_fade(themepickertitle))
                    print(f"{Fore.WHITE}  Pick a theme:\n")

                    # Build rows of 3, mirroring main menu style:
                    # {c1}[{c2}N{c1}]{c2} name  |  {c1}[{c2}N{c1}]{c2} name  ...
                    rows = []
                    for i, name in enumerate(FADE_THEMES, 1):
                        c1, c2 = _THEME_COLOURS.get(name, (Fore.MAGENTA, Fore.LIGHTMAGENTA_EX))
                        rows.append((c1, c2, i, name))

                    for row_start in range(0, len(rows), 3):
                        group = rows[row_start:row_start+3]
                        parts = []
                        for c1, c2, i, name in group:
                            parts.append(f"{c1}[{c2}{i}{c1}]{c2} {name}")
                        line = f"  {Fore.RESET}|{Fore.RESET}  ".join(parts)
                        print(f"{line}{Fore.RESET}")
                    print()

                    t = input(f"{T()}[{T2()}>{T()}]{T2()} Enter number or name (or 0 to cancel): {Fore.RESET}").strip().lower()
                    if t and t != '0':
                        chosen = None
                        if t.isdigit():
                            idx = int(t) - 1
                            if 0 <= idx < len(FADE_THEMES):
                                chosen = FADE_THEMES[idx]
                        elif t in FADE_THEMES:
                            chosen = t
                        if chosen:
                            SETTINGS["theme"] = chosen
                            save_config()
                            print(_apply_fade(f"\n  Theme set to: {chosen}"))
                            time.sleep(1)
                        else:
                            print(f"{Fore.RED}[{T2()}X{Fore.RED}]{T2()} Unknown theme.{Fore.RESET}")
                            time.sleep(0.8)

                elif s == '4':
                    SETTINGS["download_format"] = "txt"
                    SETTINGS["translate"]        = False
                    SETTINGS["theme"]            = "purplepink"
                    save_config()
                    print(f"\n{T()}[{T2()}!{T()}]{T2()} Settings reset to defaults.{Fore.RESET}")
                    time.sleep(0.9)

                elif s in ('0', 'b', 'back', ''):
                    break

                else:
                    print(f"{Fore.RED}[{T2()}X{Fore.RED}]{T2()} Invalid choice.{Fore.RESET}")
                    time.sleep(0.6)


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

GUI_TEXT = {
    "zh": {
        "title": "Nibble",
        "ready": "就绪",
        "running": "运行中...",
        "novel_url": "小说网址",
        "scrape": "抓取小说",
        "convert": "TXT 文件夹转 EPUB",
        "translate_tool": "大模型翻译",
        "polish_tool": "翻译润色",
        "settings": "设置",
        "reset_driver": "重置 ChromeDriver",
        "clear_log": "清空日志",
        "pause": "暂停翻译",
        "resume": "继续翻译",
        "stop_translation": "结束翻译",
        "missing_url_title": "缺少网址",
        "missing_url": "请输入小说网址。",
        "done_title": "完成",
        "done": "任务已完成。",
        "error_title": "错误",
        "input_required": "需要输入",
        "select_folder": "选择包含 TXT 章节的文件夹",
        "settings_saved": "设置已保存。",
        "saved_title": "已保存",
        "download_format": "下载格式",
        "translate": "韩文翻译为英文",
        "theme": "主题",
        "language": "界面语言",
        "save": "保存",
        "cancel": "取消",
        "driver_reset": "ChromeDriver 路径已重置。\n",
        "task_running_title": "任务仍在运行",
        "task_running": "当前任务仍在运行。仍要关闭窗口吗？",
        "api_base": "API 地址",
        "api_key": "API Key",
        "model": "模型",
        "source_type": "来源类型",
        "source_path": "来源路径",
        "output_path": "输出路径",
        "translation_path": "译文目录",
        "source_file": "原文 TXT",
        "translation_file": "译文 TXT",
        "output_file": "输出 TXT",
        "source_folder": "原文目录",
        "output_folder": "输出目录",
        "default_glossaries": "默认术语表",
        "extra_glossaries": "追加术语表",
        "add_glossary": "导入追加术语表",
        "clear_glossaries": "清空追加",
        "no_default_glossary": "译文目录中未找到默认术语表",
        "glossary": "术语表",
        "manual_glossary": "人工术语表",
        "machine_glossary": "机器术语表",
        "current_glossary": "当前术语表",
        "glossary_view": "术语表类型",
        "glossary_use": "翻译使用",
        "glossary_use_both": "人工 + 机器",
        "glossary_use_manual": "仅人工",
        "glossary_use_machine": "仅机器",
        "glossary_use_none": "不使用",
        "search_glossary": "搜索术语",
        "auto_glossary": "AI 自动增加术语表",
        "browse": "浏览",
        "import_glossary": "导入术语表",
        "export_glossary": "导出术语表",
        "add_term": "新增",
        "edit_term": "编辑",
        "delete_term": "删除",
        "start_translate": "开始翻译",
        "start_polish": "开始润色",
        "glossary_guide": "术语生成规范",
        "term_src": "原文",
        "term_dst": "译文",
        "term_info": "说明",
        "term_type": "类型",
        "term_active": "启用",
        "term_type_manual": "人工",
        "term_type_machine": "机器",
        "delete_confirm_title": "删除术语",
        "delete_confirm": "确定要删除这个术语吗？",
        "select_source": "选择来源",
        "select_output": "选择输出",
        "missing_translate_config": "请填写 API Key、模型、来源路径和输出路径。",
        "missing_polish_config": "请填写 API Key 和模型，并选择有效的原文目录、译文目录。",
        "missing_source_pairs": "以下译文没有找到同名原文 TXT：{names}",
        "test_api": "测试 API / 获取模型",
        "style_guide": "文风指导",
        "polish_guide": "润色指导",
        "polish_chunk_settings": "分段设置",
        "polish_chunk_enabled": "启用分段",
        "polish_lines_per_chunk": "每段行数",
        "invalid_polish_lines": "每段行数必须是大于 0 的整数。",
        "style_saved": "文风指导已保存。",
        "glossary_guide_saved": "术语生成规范已保存。",
        "api_unavailable": "该 API 不可用，无法获取模型列表。",
        "models_loaded": "模型列表获取成功。",
        "progress_idle": "翻译进度：未开始",
        "progress_status": "翻译进度：{current}/{total} | 当前：{name} | 总耗时：{elapsed} | 平均/章：{avg}",
        "log_translation_resumed": "翻译已继续。\n",
        "log_translation_paused": "已请求暂停翻译，当前 API 调用完成后会暂停。\n",
        "log_translation_stop_requested": "已请求结束翻译，当前 API 调用完成后会停止。\n",
        "log_machine_glossary_visible_update": "机器术语表界面已更新：+{added} 条术语\n",
        "log_translate_chunk": "正在翻译分块 {current}/{total}...",
        "log_translate_chunk_simple": "正在翻译分块 {current}...",
        "log_no_txt_files": "没有找到 TXT 文件。",
        "log_translation_stopped": "用户已结束翻译。",
        "log_skipping_existing": "跳过已存在文件：{name}",
        "log_translating_file": "正在翻译文件：{name}",
        "log_machine_glossary_updated": "机器术语表已更新：+{added} 条术语",
        "log_machine_glossary_failed": "机器术语表提取失败：{error}",
        "log_translating_epub_chapter": "正在翻译 EPUB 章节 {current}/{total}：{name}",
        "log_translated_epub_created": "已生成翻译后的 EPUB：{path}",
        "log_machine_glossary_loaded": "已自动加载机器术语表：{path}（{count} 条）\n",
        "log_polishing_file": "正在润色文件：{name}",
        "log_polish_stage": "润色阶段：{stage}",
        "log_polish_done": "已生成润色 TXT 文件夹：{path}",
        "invalid_polish_output": "输出目录不能与译文目录相同。",
        "polish_stage_glossary_check": "术语校对",
        "polish_stage_symbol_check": "符号对照",
        "polish_stage_polish": "自然润色",
        "polish_stage_logic_check": "逻辑病句检查",
        "novelpia_login_box": "Novelpia 登录",
        "novelpia_profile": "资料目录",
        "novelpia_login_help": "会员章需要先用普通 Chrome 登录到 Nibble 专用资料目录；抓取时会复用这个登录态。",
        "novelpia_open_login": "打开登录窗口",
        "novelpia_check_login": "检测登录状态",
        "novelpia_open_profile": "打开资料目录",
        "novelpia_profile_dir": "Novelpia 资料目录",
        "novelpia_auto_find": "自动寻找",
        "novelpia_auto_found": "已自动找到 Chrome，并设置 Novelpia 资料目录：\n{path}",
        "novelpia_delay_min": "Novelpia 最小等待秒数",
        "novelpia_delay_max": "Novelpia 最大等待秒数",
        "invalid_number_title": "数字无效",
        "invalid_number": "请填写有效的等待秒数。",
        "novelpia_login_ready": "已打开普通 Chrome。请在里面登录 Novelpia；完成后关闭这个 Chrome 窗口，再回到这里点确定。",
        "novelpia_login_manual_opened": "已用普通 Chrome 打开 Novelpia 登录窗口。这个窗口不会被 Google 当作 WebDriver 控制的浏览器。",
        "novelpia_login_detected": "已检测到 Novelpia 登录态。",
        "novelpia_login_missing": "未检测到 Novelpia 登录态。请在这个 Nibble 专用浏览器窗口里登录。",
        "novelpia_browser_closed": "Novelpia 登录窗口已关闭。\n",
        },
    "en": {
        "title": "Nibble",
        "ready": "Ready",
        "running": "Running...",
        "novel_url": "Novel URL",
        "scrape": "Scrape Novel",
        "convert": "Convert Folder to EPUB",
        "translate_tool": "LLM Translate",
        "polish_tool": "Translation Polish",
        "settings": "Settings",
        "reset_driver": "Reset ChromeDriver",
        "clear_log": "Clear Log",
        "pause": "Pause Translation",
        "resume": "Resume Translation",
        "stop_translation": "Stop Translation",
        "missing_url_title": "Missing URL",
        "missing_url": "Please enter a novel URL.",
        "done_title": "Done",
        "done": "Task finished.",
        "error_title": "Error",
        "input_required": "Input Required",
        "select_folder": "Select folder with TXT chapters",
        "settings_saved": "Settings saved.",
        "saved_title": "Saved",
        "download_format": "Download Format",
        "translate": "Translate KO to EN",
        "theme": "Theme",
        "language": "Interface Language",
        "save": "Save",
        "cancel": "Cancel",
        "driver_reset": "ChromeDriver path reset.\n",
        "task_running_title": "Task Running",
        "task_running": "A task is still running. Close the window anyway?",
        "api_base": "API Base",
        "api_key": "API Key",
        "model": "Model",
        "source_type": "Source Type",
        "source_path": "Source Path",
        "output_path": "Output Path",
        "translation_path": "Translation Folder",
        "source_file": "Source TXT",
        "translation_file": "Translation TXT",
        "output_file": "Output TXT",
        "source_folder": "Source Folder",
        "output_folder": "Output Folder",
        "default_glossaries": "Default Glossaries",
        "extra_glossaries": "Additional Glossaries",
        "add_glossary": "Import Additional Glossary",
        "clear_glossaries": "Clear Additional",
        "no_default_glossary": "No default glossary found beside the translation",
        "glossary": "Glossary",
        "manual_glossary": "Manual Glossary",
        "machine_glossary": "Machine Glossary",
        "current_glossary": "Current Glossary",
        "glossary_view": "Glossary View",
        "glossary_use": "Use in Translation",
        "glossary_use_both": "Manual + Machine",
        "glossary_use_manual": "Manual only",
        "glossary_use_machine": "Machine only",
        "glossary_use_none": "None",
        "search_glossary": "Search Glossary",
        "auto_glossary": "AI Auto-add Glossary",
        "browse": "Browse",
        "import_glossary": "Import Glossary",
        "export_glossary": "Export Glossary",
        "add_term": "Add",
        "edit_term": "Edit",
        "delete_term": "Delete",
        "start_translate": "Start Translation",
        "start_polish": "Start Polish",
        "glossary_guide": "Glossary Rules",
        "term_src": "Source",
        "term_dst": "Target",
        "term_info": "Info",
        "term_type": "Type",
        "term_active": "Active",
        "term_type_manual": "Manual",
        "term_type_machine": "Machine",
        "delete_confirm_title": "Delete Term",
        "delete_confirm": "Delete this glossary term?",
        "select_source": "Select Source",
        "select_output": "Select Output",
        "missing_translate_config": "Please fill API key, model, source path, and output path.",
        "missing_polish_config": "Please fill the API key and model, then select valid source and translation folders.",
        "missing_source_pairs": "No same-name source TXT was found for: {names}",
        "test_api": "Test API / Load Models",
        "style_guide": "Style Guide",
        "polish_guide": "Polish Guide",
        "polish_chunk_settings": "Chunk Settings",
        "polish_chunk_enabled": "Split",
        "polish_lines_per_chunk": "Lines per chunk",
        "invalid_polish_lines": "Lines per chunk must be a positive integer.",
        "style_saved": "Style guide saved.",
        "glossary_guide_saved": "Glossary extraction rules saved.",
        "api_unavailable": "This API is unavailable; models could not be loaded.",
        "models_loaded": "Models loaded successfully.",
        "progress_idle": "Translation progress: idle",
        "progress_status": "Translation progress: {current}/{total} | Current: {name} | Elapsed: {elapsed} | Avg/chapter: {avg}",
        "log_translation_resumed": "Translation resumed.\n",
        "log_translation_paused": "Translation pause requested. It will pause after the current API call finishes.\n",
        "log_translation_stop_requested": "Translation stop requested. It will stop after the current API call finishes.\n",
        "log_machine_glossary_visible_update": "Machine glossary visible update: +{added} terms\n",
        "log_translate_chunk": "Translating chunk {current}/{total}...",
        "log_translate_chunk_simple": "Translating chunk {current}...",
        "log_no_txt_files": "No TXT files found.",
        "log_translation_stopped": "Translation stopped by user.",
        "log_skipping_existing": "Skipping existing file: {name}",
        "log_translating_file": "Translating file: {name}",
        "log_machine_glossary_updated": "Machine glossary updated: +{added} terms",
        "log_machine_glossary_failed": "Machine glossary extraction failed: {error}",
        "log_translating_epub_chapter": "Translating EPUB chapter {current}/{total}: {name}",
        "log_translated_epub_created": "Translated EPUB created: {path}",
        "log_machine_glossary_loaded": "Machine glossary loaded: {path} ({count} terms)\n",
        "log_polishing_file": "Polishing file: {name}",
        "log_polish_stage": "Polish stage: {stage}",
        "log_polish_done": "Polished TXT folder created: {path}",
        "invalid_polish_output": "The output folder cannot be the same as the translation folder.",
        "polish_stage_glossary_check": "glossary check",
        "polish_stage_symbol_check": "symbol alignment",
        "polish_stage_polish": "natural polish",
        "polish_stage_logic_check": "logic check",
        "novelpia_login_box": "Novelpia Login",
        "novelpia_profile": "Profile",
        "novelpia_login_help": "Member chapters require logging in with regular Chrome into Nibble's dedicated profile; scraping reuses that session.",
        "novelpia_open_login": "Open Login Browser",
        "novelpia_check_login": "Check Login",
        "novelpia_open_profile": "Open Profile Folder",
        "novelpia_profile_dir": "Novelpia Profile Folder",
        "novelpia_auto_find": "Auto Find",
        "novelpia_auto_found": "Chrome was found and the Novelpia profile folder was set to:\n{path}",
        "novelpia_delay_min": "Novelpia Min Delay Seconds",
        "novelpia_delay_max": "Novelpia Max Delay Seconds",
        "invalid_number_title": "Invalid Number",
        "invalid_number": "Please enter valid delay seconds.",
        "novelpia_login_ready": "Regular Chrome is open. Log in to Novelpia there; when done, close that Chrome window, then return here and click OK.",
        "novelpia_login_manual_opened": "Opened the Novelpia login window with regular Chrome. Google should not see this as a WebDriver-controlled browser.",
        "novelpia_login_detected": "Novelpia login session detected.",
        "novelpia_login_missing": "No Novelpia login session detected. Log in inside this Nibble-dedicated browser window.",
        "novelpia_browser_closed": "Novelpia login browser closed.\n",
    },
}


def gui_text(key):
    lang = SETTINGS.get("gui_language", "zh")
    if lang not in GUI_TEXT:
        lang = "zh"
    return GUI_TEXT[lang].get(key, GUI_TEXT["zh"].get(key, key))


def clean_gui_output(text):
    text = ANSI_RE.sub("", str(text))
    text = text.replace("\r", "")
    text = re.sub(r"(?m)^\s*[|/\\-]\s*$\n?", "", text)
    text = re.sub(r"(?m)^\s*\[(?:!|X|x|\+|~|>|#|\?|DBG|\d+)\]\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:鈹[^\n]{4,}|鈺[^\n]{4,})\s*$\n?", "", text)
    return text


def load_glossary_file(path):
    # utf-8-sig transparently accepts both regular UTF-8 and UTF-8 with BOM.
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        entries = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            src = str(item.get("src", "")).strip()
            dst = str(item.get("dst", "")).strip()
            if not src or not dst:
                continue
            entries.append({
                "src": src,
                "dst": dst,
                "info": str(item.get("info", "")),
                "lock": int(item.get("lock", 0) or 0),
                "is_active": int(item.get("is_active", 1) or 0),
            })
    elif isinstance(data, dict):
        for src, dst in data.items():
            if str(src).strip() and str(dst).strip():
                entries.append({"src": str(src), "dst": str(dst), "info": "", "lock": 0, "is_active": 1})
    return entries


def save_glossary_file(path, entries):
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def merge_glossary_entries(target_entries, new_entries):
    existing = {e.get("src", "") for e in target_entries if e.get("src")}
    added = 0
    for item in new_entries:
        src = str(item.get("src", "")).strip()
        dst = str(item.get("dst", "")).strip()
        if not src or not dst or src in existing:
            continue
        target_entries.append({
            "src": src,
            "dst": dst,
            "info": str(item.get("info", "")).strip(),
            "lock": int(item.get("lock", 0) or 0),
            "is_active": int(item.get("is_active", 1) or 1),
        })
        existing.add(src)
        added += 1
    return added


def new_glossary_items(target_entries, candidates):
    existing = {e.get("src", "") for e in target_entries if e.get("src")}
    items = []
    seen = set()
    for item in candidates:
        src = str(item.get("src", "")).strip()
        dst = str(item.get("dst", "")).strip()
        if not src or not dst or src in existing or src in seen:
            continue
        items.append(item)
        seen.add(src)
    return items


def relevant_glossary_entries(text, entries, limit=80):
    active = [e for e in entries if e.get("is_active", 1) and e.get("src") and e.get("dst")]
    hits = [e for e in active if e["src"] in text]
    if len(hits) < min(20, len(active)):
        seen = {e["src"] for e in hits}
        hits.extend(e for e in active if e["src"] not in seen)
    return hits[:limit]


def extract_glossary_terms_with_llm(source_text, translated_text, api_config):
    source_text = sanitize_translation_source_text(source_text)
    translated_text = sanitize_translation_source_text(translated_text)
    if not source_text.strip() or not translated_text.strip():
        return []
    sample_source = source_text[:5000]
    sample_translated = translated_text[:5000]
    default_guide = (
        "Extract a concise glossary from this Korean novel passage and its Chinese translation. "
        "Focus on character names, nicknames, game terms, industry terms, proper nouns, skills, organizations, and repeated special terms. "
        "Do not include common words, particles, full sentences, or punctuation-only items. Limit to 30 items."
    )
    glossary_guide = (api_config.get("glossary_guide") or default_guide).strip()
    prompt = (
        f"{glossary_guide}\n"
        "Return ONLY a JSON array. Each item must be {\"src\":\"Korean term\",\"dst\":\"Chinese translation\",\"info\":\"category or short note\",\"lock\":0,\"is_active\":1}. "
        "\n\n"
        f"Korean source:\n{sample_source}\n\nChinese translation:\n{sample_translated}"
    )
    headers = {"Authorization": f"Bearer {api_config['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": api_config["model"],
        "messages": [
            {"role": "system", "content": "You are a terminology extraction assistant. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    resp = requests.post(chat_completion_url_from_base(api_config["api_base"]), headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        content = match.group(0)
    data = json.loads(content)
    return data if isinstance(data, list) else []


def split_translation_chunks(text, max_chars=4500):
    parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks, current = [], []
    current_len = 0
    for part in parts:
        extra = len(part) + 2
        if current and current_len + extra > max_chars:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(part)
        current_len += extra
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [text]


def polish_chunk_count(text, target_lines=80, max_chunks=None):
    line_count = max(1, len((text or "").replace("\r", "").splitlines()))
    target_lines = max(1, int(target_lines or 1))
    chunk_count = max(1, (line_count + target_lines - 1) // target_lines)
    if max_chunks is not None:
        chunk_count = min(max(1, int(max_chunks)), chunk_count)
    return chunk_count


def split_text_into_line_chunks(text, chunk_count, return_separators=False):
    text = (text or "").replace("\r", "").strip()
    if not text:
        return [""]
    lines = text.splitlines()
    chunk_count = max(1, min(int(chunk_count or 1), len(lines)))
    chunks = []
    separators = []
    start = 0
    for index in range(chunk_count):
        remaining_chunks = chunk_count - index
        remaining_lines = len(lines) - start
        size = (remaining_lines + remaining_chunks - 1) // remaining_chunks
        end = len(lines) if index == chunk_count - 1 else start + size
        if index < chunk_count - 1:
            search_start = max(start + 1, end - 8)
            search_end = min(len(lines) - (remaining_chunks - 1), end + 8)
            blank_lines = [pos for pos in range(search_start, search_end + 1) if not lines[pos - 1].strip()]
            if blank_lines:
                end = min(blank_lines, key=lambda pos: abs(pos - end))
        chunks.append("\n".join(lines[start:end]).strip())
        if index < chunk_count - 1:
            separators.append("\n\n" if end > start and not lines[end - 1].strip() else "\n")
        start = end
    if return_separators:
        return chunks, separators
    return chunks


def join_polished_chunks(chunks, separators):
    if not chunks:
        return ""
    result = chunks[0]
    for index, chunk in enumerate(chunks[1:]):
        result += separators[index] + chunk
    return result


def call_llm_translate(text, glossary_entries, api_base, api_key, model, style_guide=""):
    if not api_key:
        raise ValueError("Missing API key.")
    terms = relevant_glossary_entries(text, glossary_entries)
    glossary_text = "\n".join(
        f"- {e['src']} => {e['dst']}" + (f" ({e.get('info', '')})" if e.get("info") else "")
        for e in terms
    )
    system_prompt = (
        "You are a professional Korean-to-Chinese web novel translator. "
        "Translate faithfully and fluently into Simplified Chinese. "
        "Preserve paragraph breaks. Output only the translated text. "
        "Follow the glossary exactly for names and special terms."
    )
    user_prompt = (
        "Style guide:\n" + (style_guide.strip() or "(none)") +
        "\n\nGlossary:\n" + (glossary_text or "(none)") +
        "\n\nText:\n" + text
    )
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    data = post_chat_completion(api_base, headers, payload)
    return data["choices"][0]["message"]["content"].strip()


def translation_api_args(api_config):
    return {
        "api_base": api_config.get("api_base", ""),
        "api_key": api_config.get("api_key", ""),
        "model": api_config.get("model", ""),
        "style_guide": api_config.get("style_guide", ""),
    }


def chat_completion_url_from_base(api_base):
    api_base = (api_base or "").strip().rstrip("/")
    if api_base.endswith("/chat/completions"):
        return api_base
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    if api_base.endswith("/models"):
        return api_base[: -len("/models")] + "/chat/completions"
    return api_base + "/chat/completions"


def model_list_url_from_chat_url(api_base):
    api_base = (api_base or "").strip().rstrip("/")
    if api_base.endswith("/chat/completions"):
        return api_base[: -len("/chat/completions")] + "/models"
    if api_base.endswith("/completions"):
        return api_base[: -len("/completions")] + "/models"
    if api_base.endswith("/v1"):
        return api_base + "/models"
    return api_base + "/models"


def fetch_llm_models(api_base, api_key):
    if not api_base or not api_key:
        raise ValueError("Missing API base or API key.")
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(model_list_url_from_chat_url(api_base), headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    raw_models = data.get("data", data if isinstance(data, list) else [])
    models = []
    for item in raw_models:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("name")
        else:
            model_id = str(item)
        if model_id:
            models.append(str(model_id))
    models = sorted(set(models))
    if not models:
        raise ValueError("No models found.")
    return models


def post_chat_completion(api_base, headers, payload, timeout=(30, 300), retries=2):
    chat_url = chat_completion_url_from_base(api_base)
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(chat_url, headers=headers, json=payload, timeout=timeout)
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                detail = (resp.text or "")[:800]
                raise requests.HTTPError(f"{e}\nURL: {chat_url}\nResponse: {detail}") from e
            return resp.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt >= retries:
                break
            wait_seconds = 2 + attempt * 3
            print(f"API request timed out or disconnected. Retrying {attempt + 1}/{retries} after {wait_seconds}s...")
            time.sleep(wait_seconds)
    raise RuntimeError(
        "API 请求超时。请尝试换更快的模型，或稍后重试；程序已经把润色分块调小并自动重试，但服务端仍未及时返回。"
    ) from last_error


def translate_long_text_with_llm(text, glossary_entries, api_base, api_key, model):
    translated = []
    for idx, chunk in enumerate(split_translation_chunks(text), 1):
        print(gui_text("log_translate_chunk_simple").format(current=idx))
        translated.append(call_llm_translate(chunk, glossary_entries, api_base, api_key, model))
    return "\n\n".join(translated)


def wait_if_paused(pause_event):
    while pause_event is not None and pause_event.is_set():
        time.sleep(0.2)


def format_duration(seconds):
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def should_stop(stop_event):
    return stop_event is not None and stop_event.is_set()


def sanitize_translation_source_text(text):
    lines = []
    for line in (text or "").replace("\r", "").splitlines():
        stripped = line.strip()
        if stripped in {"+", "基本", "basic", "dark", "기본"}:
            continue
        if re.fullmatch(r"(?:글자|letter)\s*[-−]?\s*\d+px", stripped, flags=re.IGNORECASE):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def translate_long_text_with_llm_progress(text, glossary_entries, api_config, pause_event=None, stop_event=None):
    translated = []
    chunks = split_translation_chunks(sanitize_translation_source_text(text))
    translate_args = translation_api_args(api_config)
    for idx, chunk in enumerate(chunks, 1):
        if should_stop(stop_event):
            break
        wait_if_paused(pause_event)
        print(gui_text("log_translate_chunk").format(current=idx, total=len(chunks)))
        translated.append(call_llm_translate(chunk, glossary_entries, **translate_args))
    return "\n\n".join(translated)


def paired_source_file(source_folder, translated_file):
    if not source_folder:
        return None
    exact = os.path.join(source_folder, os.path.basename(translated_file))
    if os.path.exists(exact):
        return exact
    translated_stem = os.path.splitext(os.path.basename(translated_file))[0]
    for path in list_txt_files(source_folder):
        if os.path.splitext(os.path.basename(path))[0] == translated_stem:
            return path
    return None


def call_llm_polish_stage(source_text, translated_text, glossary_entries, api_config, stage, polish_guide=""):
    if not api_config.get("api_key"):
        raise ValueError("Missing API key.")
    probe_text = "\n".join([source_text or "", translated_text or ""])
    terms = relevant_glossary_entries(probe_text, glossary_entries, limit=200)
    glossary_text = "\n".join(
        f"- {e['src']} => {e['dst']}" + (f" ({e.get('info', '')})" if e.get("info") else "")
        for e in terms
    )
    stage_instructions = {
        "glossary_check": (
            "First pass for the entire chapter: compare the Korean source and Chinese translation against the glossary. "
            "Correct names, special terms, titles, organizations, skills, and repeated terminology. "
            "Apply every relevant glossary entry consistently. Do not polish style yet unless needed to make the correction grammatical."
        ),
        "symbol_check": (
            "Second pass for the entire chapter: compare the source and translation line by line and correct the translation's symbols and layout. "
            "Make quotation marks, brackets, dashes, ellipses, separators, message/reply markers, and paragraph breaks correspond to the source. "
            "Use natural Chinese punctuation forms, preserve the words and terminology already corrected, and do not rewrite the prose yet."
        ),
        "polish": (
            "Final pass for this approximately 80-line section: compare it closely with the matching Korean source and polish the Chinese text. "
            "Follow the polishing guide. Keep the plot, meaning, tone, speaker intent, corrected symbols, paragraph breaks, and glossary terms intact. "
            "Repair omitted subjects or other necessary sentence elements when the context requires them."
        ),
        "logic_check": (
            "Final pass: check for awkward phrasing, bad sentences, contradiction, missing logic, wrong pronouns, and unclear subjects. "
            "Fix only real problems and output the final polished Chinese text."
        ),
    }
    system_prompt = (
        "You are a professional Korean-to-Chinese web novel translation editor. "
        "Output only the edited Chinese text. Do not add notes, analysis, markdown, or headings."
    )
    user_prompt = (
        stage_instructions.get(stage, stage_instructions["polish"]) +
        "\n\nPolishing guide:\n" + (polish_guide.strip() or "(none)") +
        "\n\nGlossary:\n" + (glossary_text or "(none)") +
        "\n\nKorean source for reference:\n" + (source_text.strip() or "(not provided)") +
        "\n\nChinese text to edit:\n" + translated_text
    )
    headers = {"Authorization": f"Bearer {api_config['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": api_config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.15,
    }
    data = post_chat_completion(api_config["api_base"], headers, payload)
    return data["choices"][0]["message"]["content"].strip()


def run_configured_polish_stage(
    source_text, translated_text, glossary_entries, api_config, stage,
    split_enabled=False, target_lines=80, pause_event=None, stop_event=None,
):
    chunk_count = polish_chunk_count(translated_text, target_lines) if split_enabled else 1
    source_chunks = split_text_into_line_chunks(source_text, chunk_count)
    translated_chunks, chunk_separators = split_text_into_line_chunks(
        translated_text, chunk_count, return_separators=True
    )
    edited_chunks = []
    for chunk_index, translated_chunk in enumerate(translated_chunks, 1):
        if should_stop(stop_event):
            break
        wait_if_paused(pause_event)
        source_ref = source_chunks[chunk_index - 1] if chunk_index <= len(source_chunks) else source_text
        label = gui_text(f"polish_stage_{stage}")
        if len(translated_chunks) > 1:
            label += f" {chunk_index}/{len(translated_chunks)}"
        print(gui_text("log_polish_stage").format(stage=label))
        edited_chunks.append(call_llm_polish_stage(
            source_ref,
            translated_chunk,
            glossary_entries,
            api_config,
            stage,
            api_config.get("polish_guide", ""),
        ))
    if should_stop(stop_event) or not edited_chunks:
        return ""
    return join_polished_chunks(edited_chunks, chunk_separators)


def polish_long_text_with_llm_progress(source_text, translated_text, glossary_entries, api_config, pause_event=None, stop_event=None):
    source_text = sanitize_translation_source_text(source_text)
    text = sanitize_translation_source_text(translated_text)
    stage_chunking = api_config.get("stage_chunking", {})

    for stage in ("glossary_check", "symbol_check", "polish"):
        settings = stage_chunking.get(stage, {})
        text = run_configured_polish_stage(
            source_text,
            text,
            glossary_entries,
            api_config,
            stage,
            split_enabled=bool(settings.get("enabled", stage == "polish")),
            target_lines=settings.get("lines", 80),
            pause_event=pause_event,
            stop_event=stop_event,
        )
        if should_stop(stop_event) or not text.strip():
            return ""
    return text


def default_polish_glossary_paths(translation_path):
    if not translation_path:
        return []
    elif os.path.isdir(translation_path):
        folder = os.path.abspath(translation_path)
    else:
        folder = os.path.dirname(os.path.abspath(translation_path))
    paths = []
    for name in ("_machine_glossary.json", "_manual_glossary.json"):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            paths.append(path)
    return paths


def default_polish_output_folder(translation_folder):
    normalized = os.path.normpath(translation_folder)
    parent = os.path.dirname(normalized)
    folder_name = os.path.basename(normalized)
    return os.path.join(parent, folder_name + "_polished")


def load_polish_glossaries(translation_path, extra_paths=None):
    default_paths = default_polish_glossary_paths(translation_path)
    machine_path = next((p for p in default_paths if os.path.basename(p) == "_machine_glossary.json"), None)
    manual_path = next((p for p in default_paths if os.path.basename(p) == "_manual_glossary.json"), None)
    entries_by_source = {}
    order = []

    def add_entries(path, overwrite=False):
        if not path or not os.path.isfile(path):
            return
        for entry in load_glossary_file(path):
            src = entry.get("src", "")
            if src not in entries_by_source:
                order.append(src)
                entries_by_source[src] = entry
            elif overwrite:
                entries_by_source[src] = entry

    add_entries(machine_path)
    add_entries(manual_path, overwrite=True)
    for path in extra_paths or []:
        add_entries(path, overwrite=False)
    return [entries_by_source[src] for src in order], default_paths


def polish_txt_file_with_llm(
    source_file, translation_file, output_file, glossary_entries, api_config,
    progress_callback=None, pause_event=None, stop_event=None,
):
    with open(source_file, "r", encoding="utf-8-sig", errors="replace") as f:
        source_text = f.read()
    with open(translation_file, "r", encoding="utf-8-sig", errors="replace") as f:
        translated_text = f.read()
    print(gui_text("log_polishing_file").format(name=os.path.basename(translation_file)))
    start_time = time.time()
    polished = polish_long_text_with_llm_progress(
        source_text, translated_text, glossary_entries, api_config, pause_event, stop_event
    )
    if not should_stop(stop_event) and polished.strip():
        save_to_file(output_file, polished)
        if progress_callback:
            progress_callback(1, 1, os.path.basename(translation_file), start_time, 1)
        print(gui_text("log_polish_done").format(path=output_file))
    return output_file


def polish_txt_folder_with_llm(
    source_folder, translation_folder, output_folder, glossary_entries, api_config,
    progress_callback=None, pause_event=None, stop_event=None,
):
    if not output_folder:
        output_folder = default_polish_output_folder(translation_folder)
    if os.path.normcase(os.path.abspath(output_folder)) == os.path.normcase(os.path.abspath(translation_folder)):
        raise ValueError(gui_text("invalid_polish_output"))
    files = sorted(list_txt_files(translation_folder))
    if not files:
        print(gui_text("log_no_txt_files"))
        return output_folder
    missing_names = [
        os.path.basename(path)
        for path in files
        if not os.path.isfile(os.path.join(source_folder, os.path.basename(path)))
    ]
    if missing_names:
        preview = ", ".join(missing_names[:10])
        if len(missing_names) > 10:
            preview += f" ... (+{len(missing_names) - 10})"
        raise FileNotFoundError(gui_text("missing_source_pairs").format(names=preview))
    os.makedirs(output_folder, exist_ok=True)
    start_time = time.time()
    completed = 0
    total = len(files)
    for index, file_path in enumerate(files, 1):
        if should_stop(stop_event):
            print(gui_text("log_translation_stopped"))
            break
        wait_if_paused(pause_event)
        name = os.path.basename(file_path)
        out_path = os.path.join(output_folder, name)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(gui_text("log_skipping_existing").format(name=name))
            completed += 1
            if progress_callback:
                progress_callback(index, total, name, start_time, completed)
            continue
        print(gui_text("log_polishing_file").format(name=name))
        source_path = os.path.join(source_folder, name)
        with open(source_path, "r", encoding="utf-8-sig", errors="replace") as f:
            source_text = f.read()
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            translated_text = f.read()
        polished = polish_long_text_with_llm_progress(source_text, translated_text, glossary_entries, api_config, pause_event, stop_event)
        if should_stop(stop_event) and not polished.strip():
            break
        save_to_file(out_path, polished)
        completed += 1
        if progress_callback:
            progress_callback(index, total, name, start_time, completed)
    print(gui_text("log_polish_done").format(path=output_folder))
    return output_folder


def translate_txt_folder_with_llm(
    source_folder, output_folder, glossary_entries, api_config,
    progress_callback=None, pause_event=None, stop_event=None,
    auto_glossary=False, machine_glossary_entries=None, machine_glossary_path=None,
    use_machine_glossary=True,
    glossary_callback=None,
):
    os.makedirs(output_folder, exist_ok=True)
    files = sorted(list_txt_files(source_folder))
    if not files:
        print(gui_text("log_no_txt_files"))
        return
    start_time = time.time()
    completed = 0
    total = len(files)
    for index, file_path in enumerate(files, 1):
        if should_stop(stop_event):
            print(gui_text("log_translation_stopped"))
            break
        wait_if_paused(pause_event)
        name = os.path.basename(file_path)
        out_path = os.path.join(output_folder, name)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(gui_text("log_skipping_existing").format(name=name))
            completed += 1
            if progress_callback:
                progress_callback(index, total, name, start_time, completed)
            continue
        print(gui_text("log_translating_file").format(name=name))
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        combined_glossary = list(glossary_entries)
        if use_machine_glossary:
            combined_glossary += machine_glossary_entries or []
        translated = translate_long_text_with_llm_progress(text, combined_glossary, api_config, pause_event, stop_event)
        if should_stop(stop_event) and not translated.strip():
            break
        save_to_file(out_path, translated)
        if auto_glossary and machine_glossary_entries is not None:
            try:
                new_terms = extract_glossary_terms_with_llm(text, translated, api_config)
                added_items = new_glossary_items(machine_glossary_entries, new_terms)
                added = merge_glossary_entries(machine_glossary_entries, added_items)
                if added and machine_glossary_path:
                    save_glossary_file(machine_glossary_path, machine_glossary_entries)
                if added and glossary_callback:
                    glossary_callback(added_items, machine_glossary_path)
                print(gui_text("log_machine_glossary_updated").format(added=added))
            except Exception as e:
                print(gui_text("log_machine_glossary_failed").format(error=e))
        completed += 1
        if progress_callback:
            progress_callback(index, total, name, start_time, completed)
    save_as_epub(output_folder, os.path.basename(output_folder.rstrip("\\/")) or "Translated Novel")


def strip_html_for_translation(content):
    raw = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content or "")
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p>|</div>|</h[1-6]>", "\n\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(raw).strip()


def translate_epub_with_llm(
    source_epub, output_epub, glossary_entries, api_config,
    progress_callback=None, pause_event=None, stop_event=None,
    auto_glossary=False, machine_glossary_entries=None, machine_glossary_path=None,
    use_machine_glossary=True,
    glossary_callback=None,
):
    from ebooklib import epub
    import ebooklib

    book = epub.read_epub(source_epub)
    out = epub.EpubBook()
    title = os.path.splitext(os.path.basename(output_epub))[0]
    out.set_identifier(safe_id := re.sub(r"[^a-zA-Z0-9_-]+", "-", title).strip("-") or "translated")
    out.set_title(title)
    out.set_language("zh")
    out.add_author("Nibble Translator")

    chapters = []
    documents = [item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT) if not isinstance(item, epub.EpubNav)]
    zero_pad = len(str(len(documents) or 1))
    start_time = time.time()
    completed = 0
    total = len(documents)
    for idx, item in enumerate(documents, 1):
        if should_stop(stop_event):
            print(gui_text("log_translation_stopped"))
            break
        wait_if_paused(pause_event)
        chap_title = getattr(item, "title", None) or f"Chapter {idx}"
        print(gui_text("log_translating_epub_chapter").format(current=idx, total=total, name=chap_title))
        text = strip_html_for_translation(item.get_content())
        if not text:
            completed += 1
            if progress_callback:
                progress_callback(idx, total, chap_title, start_time, completed)
            continue
        combined_glossary = list(glossary_entries)
        if use_machine_glossary:
            combined_glossary += machine_glossary_entries or []
        translated = translate_long_text_with_llm_progress(text, combined_glossary, api_config, pause_event, stop_event)
        if should_stop(stop_event) and not translated.strip():
            break
        if auto_glossary and machine_glossary_entries is not None:
            try:
                new_terms = extract_glossary_terms_with_llm(text, translated, api_config)
                added_items = new_glossary_items(machine_glossary_entries, new_terms)
                added = merge_glossary_entries(machine_glossary_entries, added_items)
                if added and machine_glossary_path:
                    save_glossary_file(machine_glossary_path, machine_glossary_entries)
                if added and glossary_callback:
                    glossary_callback(added_items, machine_glossary_path)
                print(gui_text("log_machine_glossary_updated").format(added=added))
            except Exception as e:
                print(gui_text("log_machine_glossary_failed").format(error=e))
        paras = [p.strip() for p in re.split(r"\n{2,}", translated) if p.strip()]
        body = "".join(f"<p>{html.escape(p)}</p>" for p in paras)
        ch = epub.EpubHtml(title=chap_title, file_name=f"chapter_{str(idx).zfill(zero_pad)}.xhtml", lang="zh")
        ch.content = f"<h1>{html.escape(chap_title)}</h1>{body}"
        out.add_item(ch)
        chapters.append(ch)
        completed += 1
        if progress_callback:
            progress_callback(idx, total, chap_title, start_time, completed)

    out.toc = chapters
    out.spine = ["nav"] + chapters
    out.add_item(epub.EpubNcx())
    out.add_item(epub.EpubNav())
    epub.write_epub(output_epub, out)
    print(gui_text("log_translated_epub_created").format(path=output_epub))


class TkLogWriter:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, text):
        if text:
            cleaned = clean_gui_output(text)
            if cleaned:
                self.log_queue.put(("log", cleaned))

    def flush(self):
        pass


class NibbleGUI:
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.log_queue = queue.Queue()
        self.prompt_queue = queue.Queue()
        self.worker = None
        self.bg_source_image = None
        self.bg_photo = None

        self.root = tk.Tk()
        self.root.title(gui_text("title"))
        self.root.geometry("980x680")
        self.root.minsize(820, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var = tk.StringVar(value=gui_text("ready"))
        self.progress_var = tk.StringVar(value=gui_text("progress_idle"))
        self.url_var = tk.StringVar(value="https://sbxh4.com/novel/26305")
        self.novelpia_profile_var = tk.StringVar()
        self.active_glossary_search_var = tk.StringVar()
        self.labels = {}
        self.buttons = {}
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.translation_running = False
        self.active_manual_entries = None
        self.active_machine_entries = None
        self.active_manual_glossary_path = None
        self.active_machine_glossary_path = None
        self.active_refresh_terms = None

        self.configure_style()
        self.load_background_image()
        self.build_ui()
        self.root.after(100, self.poll_queues)

    def configure_style(self):
        style = self.ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self.root.configure(bg="#fff3dc")
        style.configure(".", font=("Segoe UI", 10), background="#fff3dc", foreground="#6b2f2f")
        style.configure("TFrame", background="#fff3dc")
        style.configure("TLabel", background="#fff3dc", foreground="#6b2f2f")
        style.configure("TLabelframe", background="#fff3dc", foreground="#8a3a4a")
        style.configure("TLabelframe.Label", background="#fff3dc", foreground="#8a3a4a", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background="#d9577a", foreground="white", padding=(12, 7), borderwidth=0)
        style.map("TButton", background=[("active", "#c43f68"), ("disabled", "#e9b0bd")], foreground=[("disabled", "#fff7ea")])
        style.configure("TCheckbutton", background="#fff3dc", foreground="#6b2f2f")
        style.configure("TEntry", fieldbackground="#fffaf2", foreground="#4b2a24", bordercolor="#f0b77f", lightcolor="#f0b77f", darkcolor="#f0b77f")
        style.configure("TCombobox", fieldbackground="#fffaf2", foreground="#4b2a24", arrowcolor="#d9577a")
        style.configure("Treeview", background="#fffaf2", fieldbackground="#fffaf2", foreground="#4b2a24", rowheight=24)
        style.configure("Treeview.Heading", background="#ffd6a6", foreground="#6b2f2f", font=("Segoe UI", 10, "bold"))
        style.configure("Vertical.TScrollbar", background="#ffd6a6", troughcolor="#fff3dc", arrowcolor="#d9577a")
        style.configure("Horizontal.TProgressbar", background="#d9577a", troughcolor="#ffe7bd", bordercolor="#ffe7bd", lightcolor="#d9577a", darkcolor="#d9577a")

    def load_background_image(self):
        path = resource_path("Nibble_background.jpg")
        if not os.path.exists(path):
            return
        try:
            from PIL import Image, ImageTk
            self.bg_source_image = Image.open(path).convert("RGB")
            self.ImageTk = ImageTk
        except Exception:
            self.bg_source_image = None

    def install_background(self, win):
        label = self.tk.Label(win, bd=0, bg="#fff3dc")
        label.place(x=0, y=0, relwidth=1, relheight=1)
        label.lower()
        win._nibble_bg_label = label
        win._nibble_bg_photo = None
        win.bind("<Configure>", lambda event, target=win: self.refresh_window_background(target, event), add="+")
        self.refresh_window_background(win)

    def refresh_window_background(self, win, event=None):
        if self.bg_source_image is None or not hasattr(win, "_nibble_bg_label"):
            return
        if event is not None and event.widget is not win:
            return
        width = max(win.winfo_width(), 1)
        height = max(win.winfo_height(), 1)
        try:
            from PIL import Image
            img = self.bg_source_image.copy()
            src_w, src_h = img.size
            scale = max(width / src_w, height / src_h)
            new_size = (max(int(src_w * scale), 1), max(int(src_h * scale), 1))
            img = img.resize(new_size, Image.LANCZOS)
            left = max((new_size[0] - width) // 2, 0)
            top = max((new_size[1] - height) // 2, 0)
            img = img.crop((left, top, left + width, top + height))
            veil = Image.new("RGB", (width, height), "#fff3dc")
            img = Image.blend(veil, img, 0.72)
            win._nibble_bg_photo = self.ImageTk.PhotoImage(img)
            win._nibble_bg_label.configure(image=win._nibble_bg_photo)
            win._nibble_bg_label.lower()
        except Exception:
            pass

    def refresh_background(self, event=None):
        self.refresh_window_background(self.root, event)

    def build_ui(self):
        tk = self.tk
        ttk = self.ttk

        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=3)
        root.rowconfigure(3, weight=1)

        self.install_background(root)

        top = ttk.Frame(root, padding=(12, 12, 12, 6))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        self.labels["novel_url"] = ttk.Label(top, text=gui_text("novel_url"))
        self.labels["novel_url"].grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(top, textvariable=self.url_var).grid(row=0, column=1, sticky="ew")

        self.novelpia_frame = ttk.LabelFrame(top, text=gui_text("novelpia_login_box"), padding=(10, 6, 10, 8))
        self.novelpia_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.novelpia_frame.columnconfigure(1, weight=1)
        self.labels["novelpia_profile"] = ttk.Label(self.novelpia_frame, text=gui_text("novelpia_profile"))
        self.labels["novelpia_profile"].grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(self.novelpia_frame, textvariable=self.novelpia_profile_var, state="readonly").grid(row=0, column=1, sticky="ew")
        self.labels["novelpia_login_help"] = ttk.Label(
            self.novelpia_frame,
            text=gui_text("novelpia_login_help"),
            wraplength=760,
        )
        self.labels["novelpia_login_help"].grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        novelpia_buttons = ttk.Frame(self.novelpia_frame)
        novelpia_buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        for key, command in [
            ("novelpia_open_login", self.open_novelpia_login_browser),
            ("novelpia_check_login", self.check_novelpia_login),
            ("novelpia_open_profile", self.open_novelpia_profile_folder),
        ]:
            btn = ttk.Button(novelpia_buttons, text=gui_text(key), command=command)
            btn.pack(side="left", padx=(0, 8))
            self.buttons[key] = btn
        self.refresh_novelpia_profile_label()

        buttons = ttk.Frame(root, padding=(12, 0, 12, 8))
        buttons.grid(row=1, column=0, sticky="ew")

        self.action_buttons = []
        for key, command in [
            ("scrape", self.start_scrape),
            ("convert", self.start_convert),
            ("translate_tool", self.open_translate_window),
            ("polish_tool", self.open_polish_window),
            ("settings", self.open_settings),
            ("reset_driver", self.reset_driver_path),
            ("clear_log", self.clear_log),
        ]:
            btn = ttk.Button(buttons, text=gui_text(key), command=command)
            btn.pack(side="left", padx=(0, 8))
            self.buttons[key] = btn
            if key != "clear_log":
                self.action_buttons.append(btn)
        for key in ("novelpia_open_login", "novelpia_check_login", "novelpia_open_profile"):
            self.action_buttons.append(self.buttons[key])

        self.pause_button = ttk.Button(buttons, text=gui_text("pause"), command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=(8, 0))
        self.buttons["pause"] = self.pause_button

        self.stop_button = ttk.Button(buttons, text=gui_text("stop_translation"), command=self.stop_translation, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        self.buttons["stop_translation"] = self.stop_button

        log_frame = ttk.Frame(root, padding=(12, 0, 12, 8))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            height=24,
            state="disabled",
            bg="white",
            fg="#4b2a24",
            insertbackground="#d9577a",
            relief="solid",
            bd=1,
            padx=10,
            pady=8,
            font=("Consolas", 10),
        )
        yscroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=yscroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self.active_glossary_frame = ttk.LabelFrame(root, text=gui_text("current_glossary"), padding=(12, 6, 12, 8))
        self.active_glossary_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.active_glossary_frame.columnconfigure(0, weight=1)
        self.active_glossary_frame.rowconfigure(1, weight=1)
        active_toolbar = ttk.Frame(self.active_glossary_frame)
        active_toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.active_glossary_search_label = ttk.Label(active_toolbar, text=gui_text("search_glossary"))
        self.active_glossary_search_label.pack(side="left", padx=(0, 6))
        ttk.Entry(active_toolbar, textvariable=self.active_glossary_search_var, width=28).pack(side="left")
        self.active_glossary_tree = ttk.Treeview(
            self.active_glossary_frame,
            columns=("type", "src", "dst", "info", "active"),
            show="headings",
            height=6,
        )
        for col, key, width in [
            ("type", "term_type", 70),
            ("src", "term_src", 190),
            ("dst", "term_dst", 190),
            ("info", "term_info", 300),
            ("active", "term_active", 70),
        ]:
            self.active_glossary_tree.heading(col, text=gui_text(key))
            self.active_glossary_tree.column(col, width=width, anchor="w")
        active_scroll = ttk.Scrollbar(self.active_glossary_frame, orient="vertical", command=self.active_glossary_tree.yview)
        self.active_glossary_tree.configure(yscrollcommand=active_scroll.set)
        self.active_glossary_tree.grid(row=1, column=0, sticky="nsew")
        active_scroll.grid(row=1, column=1, sticky="ns")
        self.active_glossary_tree.bind("<Double-1>", self.edit_active_glossary_selected)
        self.active_glossary_search_var.trace_add("write", lambda *_: self.refresh_active_glossary_tree())
        self.active_glossary_frame.grid_remove()

        progress_frame = ttk.Frame(root, padding=(12, 0, 12, 8))
        progress_frame.grid(row=4, column=0, sticky="ew")
        progress_frame.columnconfigure(0, weight=1)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(progress_frame, textvariable=self.progress_var).grid(row=1, column=0, sticky="w")

        status = ttk.Frame(root, padding=(12, 0, 12, 10))
        status.grid(row=5, column=0, sticky="ew")
        ttk.Label(status, textvariable=self.status_var).pack(side="left")

    def set_busy(self, busy):
        state = "disabled" if busy else "normal"
        for btn in self.action_buttons:
            btn.configure(state=state)
        self.status_var.set(gui_text("running") if busy else gui_text("ready"))

    def refresh_language(self):
        self.root.title(gui_text("title"))
        for key, label in self.labels.items():
            label.configure(text=gui_text(key))
        for key, button in self.buttons.items():
            button.configure(text=gui_text(key))
        self.novelpia_frame.configure(text=gui_text("novelpia_login_box"))
        self.active_glossary_frame.configure(text=gui_text("current_glossary"))
        self.active_glossary_search_label.configure(text=gui_text("search_glossary"))
        for col, key in [
            ("type", "term_type"),
            ("src", "term_src"),
            ("dst", "term_dst"),
            ("info", "term_info"),
            ("active", "term_active"),
        ]:
            self.active_glossary_tree.heading(col, text=gui_text(key))
        self.pause_button.configure(text=gui_text("resume") if self.pause_event.is_set() else gui_text("pause"))
        if self.progress_bar["value"] == 0:
            self.progress_var.set(gui_text("progress_idle"))
        if not (self.worker and self.worker.is_alive()):
            self.status_var.set(gui_text("ready"))
        self.refresh_novelpia_profile_label()

    def center_window(self, win, width=None, height=None):
        win.update_idletasks()
        width = width or win.winfo_width()
        height = height or win.winfo_height()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        x = parent_x + max((parent_w - width) // 2, 0)
        y = parent_y + max((parent_h - height) // 2, 0)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def machine_glossary_path_for(self, source_type, output_path):
        if not output_path:
            return ""
        if source_type == "EPUB":
            base, _ = os.path.splitext(output_path)
            return base + "_machine_glossary.json"
        return os.path.join(output_path, "_machine_glossary.json")

    def manual_glossary_path_for(self, source_type, output_path):
        if not output_path:
            return ""
        if source_type == "EPUB":
            base, _ = os.path.splitext(output_path)
            return base + "_manual_glossary.json"
        return os.path.join(output_path, "_manual_glossary.json")

    def append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def refresh_novelpia_profile_label(self):
        try:
            self.novelpia_profile_var.set(get_novelpia_profile_dir())
        except Exception as exc:
            self.novelpia_profile_var.set(str(exc))

    def open_novelpia_login_browser(self):
        def task():
            proc = None
            try:
                proc = open_novelpia_regular_chrome_login()
                print(gui_text("novelpia_login_manual_opened") + "\n")
                print(gui_text("novelpia_login_ready"))
                input(gui_text("novelpia_login_ready"))
            finally:
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                print(gui_text("novelpia_browser_closed"))

        self.run_worker(task)

    def check_novelpia_login(self):
        def task():
            driver = None
            try:
                driver = create_plain_chrome_driver(create_novelpia_chrome_options())
                driver.get("https://novelpia.com/")
                if driver.get_cookie("LOGINKEY"):
                    print(gui_text("novelpia_login_detected") + "\n")
                else:
                    print(gui_text("novelpia_login_missing") + "\n")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        self.run_worker(task)

    def open_novelpia_profile_folder(self):
        try:
            path = get_novelpia_profile_dir()
            self.refresh_novelpia_profile_label()
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror(gui_text("error_title"), str(exc), parent=self.root)

    def poll_queues(self):
        from tkinter import simpledialog, messagebox

        while True:
            try:
                kind, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self.append_log(payload)
            elif kind == "progress":
                self.update_translation_progress(*payload)
            elif kind == "glossary_update":
                items, glossary_path = payload
                self.apply_machine_glossary_update(items, glossary_path)
            elif kind == "done":
                self.set_busy(False)
                self.translation_running = False
                self.pause_event.clear()
                self.stop_event.clear()
                self.pause_button.configure(state="disabled", text=gui_text("pause"))
                self.stop_button.configure(state="disabled")
                if payload:
                    messagebox.showerror(gui_text("error_title"), payload)
                else:
                    messagebox.showinfo(gui_text("done_title"), gui_text("done"))

        while True:
            try:
                req = self.prompt_queue.get_nowait()
            except queue.Empty:
                break
            answer = simpledialog.askstring(gui_text("input_required"), req["prompt"], parent=self.root)
            req["answer"] = "" if answer is None else answer
            req["event"].set()

        self.root.after(100, self.poll_queues)

    def apply_machine_glossary_update(self, items, glossary_path=None):
        if self.active_machine_entries is None:
            return
        added = merge_glossary_entries(self.active_machine_entries, items)
        visible_added = added or len(items or [])
        if visible_added and self.active_refresh_terms:
            self.active_refresh_terms()
        if visible_added:
            self.refresh_active_glossary_tree()
        if visible_added:
            self.append_log(gui_text("log_machine_glossary_visible_update").format(added=visible_added))

    def refresh_active_glossary_tree(self):
        tree = self.active_glossary_tree
        tree.delete(*tree.get_children())
        manual_entries = self.active_manual_entries or []
        machine_entries = self.active_machine_entries or []
        query = self.active_glossary_search_var.get().strip().lower()
        for prefix, label_key, entries in [
            ("manual", "term_type_manual", manual_entries),
            ("machine", "term_type_machine", machine_entries),
        ]:
            type_label = gui_text(label_key)
            for idx, item in enumerate(entries):
                haystack = " ".join([
                    type_label,
                    str(item.get("src", "")),
                    str(item.get("dst", "")),
                    str(item.get("info", "")),
                ]).lower()
                if query and query not in haystack:
                    continue
                tree.insert("", "end", iid=f"{prefix}:{idx}", values=(
                    type_label,
                    item.get("src", ""),
                    item.get("dst", ""),
                    item.get("info", ""),
                    "Y" if item.get("is_active", 1) else "N",
                ))
        if manual_entries or machine_entries or self.translation_running:
            self.active_glossary_frame.grid()
        else:
            self.active_glossary_frame.grid_remove()

    def edit_glossary_term_dialog(self, data, index, parent=None, refresh_callback=None, save_path=None):
        from tkinter import messagebox
        if data is None:
            return
        is_new = index is None
        item = {"src": "", "dst": "", "info": "", "lock": 0, "is_active": 1} if is_new else dict(data[index])
        dialog = self.tk.Toplevel(parent or self.root)
        dialog.title(gui_text("add_term") if is_new else gui_text("edit_term"))
        dialog.configure(bg="#fff3dc")
        dialog.transient(parent or self.root)
        dialog.grab_set()

        src_var = self.tk.StringVar(value=item.get("src", ""))
        dst_var = self.tk.StringVar(value=item.get("dst", ""))
        info_var = self.tk.StringVar(value=item.get("info", ""))
        active_var = self.tk.BooleanVar(value=bool(item.get("is_active", 1)))

        frame = self.ttk.Frame(dialog, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        for row, (key, var) in enumerate([("term_src", src_var), ("term_dst", dst_var), ("term_info", info_var)]):
            self.ttk.Label(frame, text=gui_text(key)).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            self.ttk.Entry(frame, textvariable=var, width=48).grid(row=row, column=1, sticky="ew", pady=4)
        self.ttk.Checkbutton(frame, text=gui_text("term_active"), variable=active_var).grid(row=3, column=1, sticky="w", pady=4)

        def commit():
            new_item = {
                "src": src_var.get().strip(),
                "dst": dst_var.get().strip(),
                "info": info_var.get().strip(),
                "lock": int(item.get("lock", 0) or 0),
                "is_active": 1 if active_var.get() else 0,
            }
            if not new_item["src"] or not new_item["dst"]:
                return
            if is_new:
                data.append(new_item)
            elif 0 <= index < len(data):
                data[index] = new_item
            if save_path:
                try:
                    save_glossary_file(save_path, data)
                except Exception as e:
                    self.append_log(gui_text("log_machine_glossary_failed").format(error=e) + "\n")
            if refresh_callback:
                refresh_callback()
            self.refresh_active_glossary_tree()
            dialog.destroy()

        def delete_current():
            if is_new:
                dialog.destroy()
                return
            if not messagebox.askyesno(gui_text("delete_confirm_title"), gui_text("delete_confirm"), parent=dialog):
                return
            if 0 <= index < len(data):
                data.pop(index)
            if save_path:
                try:
                    save_glossary_file(save_path, data)
                except Exception as e:
                    self.append_log(gui_text("log_machine_glossary_failed").format(error=e) + "\n")
            if refresh_callback:
                refresh_callback()
            self.refresh_active_glossary_tree()
            dialog.destroy()

        buttons = self.ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(10, 0))
        if not is_new:
            self.ttk.Button(buttons, text=gui_text("delete_term"), command=delete_current).pack(side="left", padx=(0, 8))
        self.ttk.Button(buttons, text=gui_text("save"), command=commit).pack(side="left", padx=(0, 8))
        self.ttk.Button(buttons, text=gui_text("cancel"), command=dialog.destroy).pack(side="left")
        self.center_window(dialog)

    def edit_active_glossary_selected(self, event=None):
        if event is not None:
            row_id = self.active_glossary_tree.identify_row(event.y)
            if row_id:
                self.active_glossary_tree.selection_set(row_id)
        selected = self.active_glossary_tree.selection()
        if not selected:
            return
        prefix, _, raw_index = selected[0].partition(":")
        if not raw_index.isdigit():
            return
        index = int(raw_index)
        if prefix == "machine":
            self.edit_glossary_term_dialog(
                self.active_machine_entries,
                index,
                parent=self.root,
                refresh_callback=self.refresh_active_glossary_tree,
                save_path=self.active_machine_glossary_path,
            )
        else:
            self.edit_glossary_term_dialog(
                self.active_manual_entries,
                index,
                parent=self.root,
                refresh_callback=self.refresh_active_glossary_tree,
                save_path=self.active_manual_glossary_path,
            )

    def update_translation_progress(self, current, total, name, start_time, completed):
        percent = int((current / total) * 100) if total else 0
        elapsed_seconds = time.time() - start_time
        avg_seconds = elapsed_seconds / completed if completed else 0
        self.progress_bar.configure(value=percent, maximum=100)
        display_name = str(name)
        if len(display_name) > 48:
            display_name = display_name[:45] + "..."
        self.progress_var.set(gui_text("progress_status").format(
            current=current,
            total=total,
            name=display_name,
            elapsed=format_duration(elapsed_seconds),
            avg=format_duration(avg_seconds),
        ))

    def toggle_pause(self):
        if not self.translation_running:
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text=gui_text("pause"))
            self.append_log(gui_text("log_translation_resumed"))
        else:
            self.pause_event.set()
            self.pause_button.configure(text=gui_text("resume"))
            self.append_log(gui_text("log_translation_paused"))

    def stop_translation(self):
        if not self.translation_running:
            return
        self.stop_event.set()
        self.pause_event.clear()
        self.pause_button.configure(text=gui_text("pause"))
        self.stop_button.configure(state="disabled")
        self.append_log(gui_text("log_translation_stop_requested"))

    def gui_input(self, prompt=""):
        event = threading.Event()
        req = {"prompt": clean_gui_output(prompt).strip(), "answer": "", "event": event}
        self.prompt_queue.put(req)
        event.wait()
        return req["answer"]

    def run_worker(self, target):
        if self.worker and self.worker.is_alive():
            return
        self.set_busy(True)

        def wrapper():
            old_stdout, old_stderr, old_input = sys.stdout, sys.stderr, builtins.input
            writer = TkLogWriter(self.log_queue)
            sys.stdout = writer
            sys.stderr = writer
            builtins.input = self.gui_input
            error = None
            try:
                target()
            except Exception:
                error = traceback.format_exc()
                print(error)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                builtins.input = old_input
                self.log_queue.put(("done", error))

        self.worker = threading.Thread(target=wrapper, daemon=True)
        self.worker.start()

    def start_scrape(self):
        url = self.url_var.get().strip()
        if not url:
            from tkinter import messagebox
            messagebox.showwarning(gui_text("missing_url_title"), gui_text("missing_url"))
            return
        self.run_worker(lambda: gui_scrape_novel(url))

    def start_convert(self):
        from tkinter import filedialog

        folder = filedialog.askdirectory(parent=self.root, initialdir=os.getcwd(), title=gui_text("select_folder"))
        if not folder:
            return
        title = os.path.basename(folder.rstrip("\\/")) or "Novel"
        self.run_worker(lambda: save_as_epub(folder, title))

    def open_settings(self):
        from tkinter import ttk, filedialog, messagebox

        win = self.tk.Toplevel(self.root)
        win.title(gui_text("settings"))
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        fmt = self.tk.StringVar(value=SETTINGS.get("download_format", "epub"))
        translate = self.tk.BooleanVar(value=bool(SETTINGS.get("translate", False)))
        theme = self.tk.StringVar(value=SETTINGS.get("theme", "purplepink"))
        current_lang = SETTINGS.get("gui_language", "zh")
        language = self.tk.StringVar(value="English" if current_lang == "en" else "中文")
        configured_novelpia_profile = str(SETTINGS.get("novelpia_profile_dir", "") or "").strip()
        try:
            displayed_novelpia_profile = configured_novelpia_profile or auto_novelpia_profile_dir()
        except Exception:
            displayed_novelpia_profile = configured_novelpia_profile
        novelpia_profile = self.tk.StringVar(value=displayed_novelpia_profile)
        novelpia_delay_min = self.tk.StringVar(value=str(SETTINGS.get("novelpia_delay_min", 4.0)))
        novelpia_delay_max = self.tk.StringVar(value=str(SETTINGS.get("novelpia_delay_max", 7.0)))

        frame = ttk.Frame(win, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=gui_text("download_format")).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Combobox(frame, textvariable=fmt, values=["txt", "epub"], state="readonly", width=24).grid(row=0, column=1, pady=5)

        ttk.Label(frame, text=gui_text("translate")).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Checkbutton(frame, variable=translate).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(frame, text=gui_text("theme")).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Combobox(frame, textvariable=theme, values=FADE_THEMES, state="readonly", width=24).grid(row=2, column=1, pady=5)

        ttk.Label(frame, text=gui_text("language")).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Combobox(frame, textvariable=language, values=["中文", "English"], state="readonly", width=24).grid(row=3, column=1, pady=5)

        ttk.Label(frame, text=gui_text("novelpia_profile_dir")).grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=novelpia_profile, width=46).grid(row=4, column=1, sticky="ew", pady=5)
        def auto_find_novelpia_profile():
            try:
                path = auto_novelpia_profile_dir()
                novelpia_profile.set(path)
                messagebox.showinfo(
                    gui_text("done_title"),
                    gui_text("novelpia_auto_found").format(path=path),
                    parent=win,
                )
            except Exception as exc:
                messagebox.showerror(gui_text("error_title"), str(exc), parent=win)

        profile_buttons = ttk.Frame(frame)
        profile_buttons.grid(row=4, column=2, padx=(8, 0), pady=5)
        ttk.Button(
            profile_buttons,
            text=gui_text("novelpia_auto_find"),
            command=auto_find_novelpia_profile,
        ).pack(side="left")
        ttk.Button(
            profile_buttons,
            text=gui_text("browse"),
            command=lambda: novelpia_profile.set(
                filedialog.askdirectory(
                    parent=win,
                    initialdir=os.path.dirname(novelpia_profile.get()) if novelpia_profile.get() else os.getcwd(),
                    title=gui_text("novelpia_profile_dir"),
                )
                or novelpia_profile.get()
            ),
        ).pack(side="left", padx=(6, 0))

        ttk.Label(frame, text=gui_text("novelpia_delay_min")).grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=novelpia_delay_min, width=12).grid(row=5, column=1, sticky="w", pady=5)

        ttk.Label(frame, text=gui_text("novelpia_delay_max")).grid(row=6, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=novelpia_delay_max, width=12).grid(row=6, column=1, sticky="w", pady=5)

        def save():
            try:
                delay_min = float(novelpia_delay_min.get())
                delay_max = float(novelpia_delay_max.get())
            except ValueError:
                messagebox.showwarning(gui_text("invalid_number_title"), gui_text("invalid_number"), parent=win)
                return
            if delay_min < 2:
                delay_min = 2.0
            if delay_max < delay_min:
                delay_max = delay_min
            SETTINGS["download_format"] = fmt.get()
            SETTINGS["translate"] = translate.get()
            SETTINGS["theme"] = theme.get()
            SETTINGS["gui_language"] = "en" if language.get() == "English" else "zh"
            SETTINGS["novelpia_profile_dir"] = novelpia_profile.get().strip()
            SETTINGS["novelpia_delay_min"] = delay_min
            SETTINGS["novelpia_delay_max"] = delay_max
            save_config()
            self.refresh_language()
            self.refresh_novelpia_profile_label()
            messagebox.showinfo(gui_text("saved_title"), gui_text("settings_saved"), parent=win)
            win.destroy()

        button_row = ttk.Frame(frame)
        button_row.grid(row=7, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(button_row, text=gui_text("save"), command=save).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text=gui_text("cancel"), command=win.destroy).pack(side="left")
        self.center_window(win, 680, 360)

    def open_translate_window(self):
        from tkinter import ttk, filedialog, messagebox, simpledialog

        win = self.tk.Toplevel(self.root)
        win.title(gui_text("translate_tool"))
        win.configure(bg="#fff3dc")
        win.minsize(1080, 640)
        self.install_background(win)
        win.transient(self.root)
        win.grab_set()
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)

        manual_entries = []
        machine_entries = []
        self.active_machine_entries = machine_entries

        api_base = self.tk.StringVar(value=SETTINGS.get("llm_api_base", "https://api.openai.com/v1/chat/completions"))
        api_key = self.tk.StringVar(value=SETTINGS.get("llm_api_key", ""))
        model = self.tk.StringVar(value=SETTINGS.get("llm_model", "gpt-4o-mini"))
        source_type = self.tk.StringVar(value=SETTINGS.get("last_translate_source_type", "TXT Folder"))
        source_path = self.tk.StringVar(value=SETTINGS.get("last_translate_source_path", ""))
        output_path = self.tk.StringVar(value=SETTINGS.get("last_translate_output_path", ""))
        glossary_view = self.tk.StringVar(value=gui_text("manual_glossary"))
        glossary_modes = ("both", "manual", "machine", "none")
        glossary_mode_keys = {
            "both": "glossary_use_both",
            "manual": "glossary_use_manual",
            "machine": "glossary_use_machine",
            "none": "glossary_use_none",
        }

        def glossary_mode_label(mode):
            return gui_text(glossary_mode_keys.get(mode, "glossary_use_both"))

        def glossary_mode_from_label(label):
            for mode in glossary_modes:
                if label == glossary_mode_label(mode):
                    return mode
            return "both"

        saved_glossary_mode = SETTINGS.get("last_translate_glossary_mode", "both")
        if saved_glossary_mode not in glossary_modes:
            saved_glossary_mode = "both"
        glossary_mode = self.tk.StringVar(value=glossary_mode_label(saved_glossary_mode))
        search_var = self.tk.StringVar()
        auto_glossary = self.tk.BooleanVar(value=False)
        if source_type.get() not in {"TXT Folder", "EPUB"}:
            source_type.set("TXT Folder")

        form = ttk.Frame(win, padding=12)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        rows = [
            ("api_base", api_base, False),
            ("api_key", api_key, True),
        ]
        for row, (key, var, secret) in enumerate(rows):
            ttk.Label(form, text=gui_text(key)).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            ttk.Entry(form, textvariable=var, show="*" if secret else "").grid(row=row, column=1, sticky="ew", pady=3)

        ttk.Label(form, text=gui_text("model")).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=3)
        model_combo = ttk.Combobox(form, textvariable=model, values=[model.get()] if model.get() else [], width=32)
        model_combo.grid(row=2, column=1, sticky="w", pady=3)

        def test_api_models():
            test_button.configure(state="disabled")
            self.status_var.set(gui_text("running"))

            def worker():
                try:
                    models = fetch_llm_models(api_base.get().strip(), api_key.get().strip())
                    self.root.after(0, lambda: on_models_loaded(models, None))
                except Exception as e:
                    self.root.after(0, lambda: on_models_loaded([], e))

            threading.Thread(target=worker, daemon=True).start()

        def on_models_loaded(models, error):
            test_button.configure(state="normal")
            if not (self.worker and self.worker.is_alive()):
                self.status_var.set(gui_text("ready"))
            if error:
                messagebox.showerror(gui_text("error_title"), f"{gui_text('api_unavailable')}\n{error}", parent=win)
                return
            model_combo.configure(values=models, state="readonly")
            if model.get() not in models:
                model.set(models[0])
            messagebox.showinfo(gui_text("done_title"), gui_text("models_loaded"), parent=win)

        test_button = ttk.Button(form, text=gui_text("test_api"), command=test_api_models)
        test_button.grid(row=2, column=2, padx=(8, 0), pady=3)

        ttk.Label(form, text=gui_text("source_type")).grid(row=3, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Combobox(form, textvariable=source_type, values=["TXT Folder", "EPUB"], state="readonly", width=18).grid(row=3, column=1, sticky="w", pady=3)

        ttk.Label(form, text=gui_text("source_path")).grid(row=4, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=source_path).grid(row=4, column=1, sticky="ew", pady=3)

        def browse_source():
            if source_type.get() == "EPUB":
                path = filedialog.askopenfilename(parent=win, title=gui_text("select_source"), filetypes=[("EPUB", "*.epub"), ("All files", "*.*")])
            else:
                path = filedialog.askdirectory(parent=win, title=gui_text("select_source"))
            if path:
                source_path.set(path)
                if not output_path.get():
                    if source_type.get() == "EPUB":
                        base, _ = os.path.splitext(path)
                        output_path.set(base + "_translated.epub")
                    else:
                        output_path.set(path.rstrip("\\/") + "_translated")
                persist_translate_paths()
                load_current_machine_glossary(show_log=True)

        ttk.Button(form, text=gui_text("browse"), command=browse_source).grid(row=4, column=2, padx=(8, 0), pady=3)

        ttk.Label(form, text=gui_text("output_path")).grid(row=5, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=output_path).grid(row=5, column=1, sticky="ew", pady=3)

        def browse_output():
            if source_type.get() == "EPUB":
                path = filedialog.asksaveasfilename(parent=win, title=gui_text("select_output"), defaultextension=".epub", filetypes=[("EPUB", "*.epub")])
            else:
                path = filedialog.askdirectory(parent=win, title=gui_text("select_output"))
            if path:
                output_path.set(path)
                persist_translate_paths()
                load_current_machine_glossary(show_log=True)

        ttk.Button(form, text=gui_text("browse"), command=browse_output).grid(row=5, column=2, padx=(8, 0), pady=3)

        mid = ttk.Frame(win, padding=(12, 0, 12, 8))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(mid)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        actions_toolbar = ttk.Frame(mid)
        actions_toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        ttk.Label(toolbar, text=gui_text("glossary_view")).pack(side="left", padx=(0, 6))
        view_combo = ttk.Combobox(
            toolbar,
            textvariable=glossary_view,
            values=[gui_text("manual_glossary"), gui_text("machine_glossary")],
            state="readonly",
            width=14,
        )
        view_combo.pack(side="left", padx=(0, 8))

        ttk.Label(toolbar, text=gui_text("glossary_use")).pack(side="left", padx=(0, 6))
        use_combo = ttk.Combobox(
            toolbar,
            textvariable=glossary_mode,
            values=[glossary_mode_label(mode) for mode in glossary_modes],
            state="readonly",
            width=16,
        )
        use_combo.pack(side="left", padx=(0, 8))

        ttk.Label(toolbar, text=gui_text("search_glossary")).pack(side="left", padx=(0, 6))
        search_entry = ttk.Entry(toolbar, textvariable=search_var, width=24)
        search_entry.pack(side="left", padx=(0, 8))

        ttk.Checkbutton(toolbar, text=gui_text("auto_glossary"), variable=auto_glossary).pack(side="left", padx=(0, 10))

        tree = ttk.Treeview(mid, columns=("src", "dst", "info", "active"), show="headings", height=12)
        for col, key, width in [
            ("src", "term_src", 190),
            ("dst", "term_dst", 190),
            ("info", "term_info", 240),
            ("active", "term_active", 70),
        ]:
            tree.heading(col, text=gui_text(key))
            tree.column(col, width=width, anchor="w")
        yscroll = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.grid(row=2, column=0, sticky="nsew")
        yscroll.grid(row=2, column=1, sticky="ns")

        def refresh_terms():
            tree.delete(*tree.get_children())
            data = machine_entries if glossary_view.get() == gui_text("machine_glossary") else manual_entries
            query = search_var.get().strip().lower()
            for idx, item in enumerate(data):
                haystack = " ".join([
                    str(item.get("src", "")),
                    str(item.get("dst", "")),
                    str(item.get("info", "")),
                ]).lower()
                if query and query not in haystack:
                    continue
                tree.insert("", "end", iid=str(idx), values=(
                    item.get("src", ""),
                    item.get("dst", ""),
                    item.get("info", ""),
                    "Y" if item.get("is_active", 1) else "N",
                ))

        self.active_refresh_terms = refresh_terms

        def persist_translate_paths():
            SETTINGS["last_translate_source_type"] = source_type.get()
            SETTINGS["last_translate_source_path"] = source_path.get().strip()
            SETTINGS["last_translate_output_path"] = output_path.get().strip()
            save_config()

        def load_current_machine_glossary(show_log=False):
            machine_path = self.machine_glossary_path_for(source_type.get(), output_path.get().strip())
            self.active_machine_glossary_path = machine_path
            if not machine_path or not os.path.exists(machine_path):
                refresh_terms()
                self.refresh_active_glossary_tree()
                return
            try:
                loaded = load_glossary_file(machine_path)
                machine_entries.clear()
                machine_entries.extend(loaded)
                refresh_terms()
                self.refresh_active_glossary_tree()
                if show_log:
                    self.append_log(gui_text("log_machine_glossary_loaded").format(path=machine_path, count=len(machine_entries)))
            except Exception as e:
                self.append_log(gui_text("log_machine_glossary_failed").format(error=e) + "\n")

        def refresh_default_output_for_source():
            src = source_path.get().strip()
            if not src:
                return
            current_out = output_path.get().strip()
            if current_out:
                return
            if source_type.get() == "EPUB":
                base, _ = os.path.splitext(src)
                output_path.set(base + "_translated.epub")
            else:
                output_path.set(src.rstrip("\\/") + "_translated")

        def on_translate_source_changed(*_):
            refresh_default_output_for_source()
            persist_translate_paths()
            load_current_machine_glossary(show_log=True)

        source_type.trace_add("write", on_translate_source_changed)
        def on_translate_path_changed(*_):
            persist_translate_paths()
            load_current_machine_glossary(show_log=False)

        source_path.trace_add("write", on_translate_path_changed)
        output_path.trace_add("write", on_translate_path_changed)
        refresh_default_output_for_source()
        self.active_manual_entries = manual_entries
        self.active_machine_entries = machine_entries
        load_current_machine_glossary(show_log=False)

        def close_translate_window():
            if self.active_refresh_terms is refresh_terms:
                self.active_refresh_terms = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", close_translate_window)

        def import_terms():
            path = filedialog.askopenfilename(parent=win, title=gui_text("import_glossary"), filetypes=[("JSON", "*.json"), ("All files", "*.*")])
            if not path:
                return
            try:
                target = machine_entries if glossary_view.get() == gui_text("machine_glossary") else manual_entries
                target.clear()
                target.extend(load_glossary_file(path))
                if target is manual_entries:
                    self.active_manual_glossary_path = path
                else:
                    self.active_machine_glossary_path = path
                refresh_terms()
                self.refresh_active_glossary_tree()
                print(f"Imported glossary: {path} ({len(target)} terms)\n")
            except Exception as e:
                messagebox.showerror(gui_text("error_title"), str(e), parent=win)

        def export_terms():
            path = filedialog.asksaveasfilename(parent=win, title=gui_text("export_glossary"), defaultextension=".json", filetypes=[("JSON", "*.json")])
            if not path:
                return
            try:
                data = machine_entries if glossary_view.get() == gui_text("machine_glossary") else manual_entries
                save_glossary_file(path, data)
                print(f"Exported glossary: {path}\n")
            except Exception as e:
                messagebox.showerror(gui_text("error_title"), str(e), parent=win)

        def edit_style_guide():
            dialog = self.tk.Toplevel(win)
            dialog.title(gui_text("style_guide"))
            dialog.configure(bg="#fff3dc")
            dialog.transient(win)
            dialog.grab_set()
            dialog.columnconfigure(0, weight=1)
            dialog.rowconfigure(0, weight=1)

            text_box = self.tk.Text(dialog, wrap="word", width=72, height=16, bg="#fffaf2", fg="#4b2a24", insertbackground="#d9577a", padx=8, pady=8)
            text_box.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            text_box.insert("1.0", SETTINGS.get("translation_style", ""))

            buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
            buttons.grid(row=1, column=0, sticky="e")

            def save_style():
                SETTINGS["translation_style"] = text_box.get("1.0", "end").strip()
                save_config()
                messagebox.showinfo(gui_text("saved_title"), gui_text("style_saved"), parent=dialog)
                dialog.destroy()

            ttk.Button(buttons, text=gui_text("save"), command=save_style).pack(side="left", padx=(0, 8))
            ttk.Button(buttons, text=gui_text("cancel"), command=dialog.destroy).pack(side="left")
            self.center_window(dialog, 680, 360)

        def edit_glossary_guide():
            dialog = self.tk.Toplevel(win)
            dialog.title(gui_text("glossary_guide"))
            dialog.configure(bg="#fff3dc")
            dialog.transient(win)
            dialog.grab_set()
            dialog.columnconfigure(0, weight=1)
            dialog.rowconfigure(0, weight=1)

            default_text = (
                "Extract a concise glossary from this Korean novel passage and its Chinese translation.\n"
                "Focus on character names, nicknames, game terms, industry terms, proper nouns, skills, organizations, and repeated special terms.\n"
                "Do not include common words, particles, full sentences, or punctuation-only items. Limit to 30 items."
            )
            text_box = self.tk.Text(dialog, wrap="word", width=72, height=16, bg="#fffaf2", fg="#4b2a24", insertbackground="#d9577a", padx=8, pady=8)
            text_box.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            text_box.insert("1.0", SETTINGS.get("glossary_extraction_guide", "") or default_text)

            buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
            buttons.grid(row=1, column=0, sticky="e")

            def save_glossary_guide():
                SETTINGS["glossary_extraction_guide"] = text_box.get("1.0", "end").strip()
                save_config()
                messagebox.showinfo(gui_text("saved_title"), gui_text("glossary_guide_saved"), parent=dialog)
                dialog.destroy()

            ttk.Button(buttons, text=gui_text("save"), command=save_glossary_guide).pack(side="left", padx=(0, 8))
            ttk.Button(buttons, text=gui_text("cancel"), command=dialog.destroy).pack(side="left")
            self.center_window(dialog, 680, 360)

        def edit_term(index=None):
            data = machine_entries if glossary_view.get() == gui_text("machine_glossary") else manual_entries
            save_path = self.active_machine_glossary_path if data is machine_entries else self.active_manual_glossary_path
            self.edit_glossary_term_dialog(data, index, parent=win, refresh_callback=refresh_terms, save_path=save_path)

        def edit_selected():
            selected = tree.selection()
            if selected:
                edit_term(int(selected[0]))

        def delete_selected():
            data = machine_entries if glossary_view.get() == gui_text("machine_glossary") else manual_entries
            selected = sorted((int(x) for x in tree.selection()), reverse=True)
            for idx in selected:
                if 0 <= idx < len(data):
                    data.pop(idx)
            refresh_terms()
            self.refresh_active_glossary_tree()
            save_path = self.active_machine_glossary_path if data is machine_entries else self.active_manual_glossary_path
            if save_path:
                try:
                    save_glossary_file(save_path, data)
                except Exception as e:
                    print(gui_text("log_machine_glossary_failed").format(error=e))

        for key, command in [
            ("import_glossary", import_terms),
            ("export_glossary", export_terms),
            ("style_guide", edit_style_guide),
            ("glossary_guide", edit_glossary_guide),
            ("add_term", lambda: edit_term(None)),
            ("delete_term", delete_selected),
        ]:
            ttk.Button(actions_toolbar, text=gui_text(key), command=command).pack(side="left", padx=(0, 8))

        def edit_tree_row(event=None):
            if event is not None:
                row_id = tree.identify_row(event.y)
                if row_id:
                    tree.selection_set(row_id)
            edit_selected()

        tree.bind("<Double-1>", edit_tree_row)
        glossary_view.trace_add("write", lambda *_: refresh_terms())
        search_var.trace_add("write", lambda *_: refresh_terms())

        bottom = ttk.Frame(win, padding=(12, 0, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")

        def start_translation():
            if self.worker and self.worker.is_alive():
                messagebox.showwarning(gui_text("error_title"), gui_text("task_running"), parent=win)
                return
            if not api_key.get().strip() or not model.get().strip() or not source_path.get().strip() or not output_path.get().strip():
                messagebox.showwarning(gui_text("error_title"), gui_text("missing_translate_config"), parent=win)
                return
            SETTINGS["llm_api_base"] = api_base.get().strip()
            SETTINGS["llm_api_key"] = api_key.get().strip()
            SETTINGS["llm_model"] = model.get().strip()
            SETTINGS["last_translate_source_type"] = source_type.get()
            SETTINGS["last_translate_source_path"] = source_path.get().strip()
            SETTINGS["last_translate_output_path"] = output_path.get().strip()
            selected_glossary_mode = glossary_mode_from_label(glossary_mode.get())
            SETTINGS["last_translate_glossary_mode"] = selected_glossary_mode
            save_config()
            api_config = {
                "api_base": SETTINGS["llm_api_base"],
                "api_key": SETTINGS["llm_api_key"],
                "model": SETTINGS["llm_model"],
                "style_guide": SETTINGS.get("translation_style", ""),
                "glossary_guide": SETTINGS.get("glossary_extraction_guide", ""),
            }
            src = source_path.get().strip()
            out = output_path.get().strip()
            manual_snapshot = list(manual_entries) if selected_glossary_mode in {"both", "manual"} else []
            machine_snapshot = machine_entries
            use_machine_glossary = selected_glossary_mode in {"both", "machine"}
            manual_path = self.active_manual_glossary_path or self.manual_glossary_path_for(source_type.get(), out)
            machine_path = self.active_machine_glossary_path or self.machine_glossary_path_for(source_type.get(), out)
            self.active_manual_entries = manual_entries
            self.active_machine_entries = machine_entries
            self.active_manual_glossary_path = manual_path
            self.active_machine_glossary_path = machine_path
            if manual_path:
                try:
                    save_glossary_file(manual_path, manual_entries)
                except Exception as e:
                    print(gui_text("log_machine_glossary_failed").format(error=e))
            if os.path.exists(machine_path):
                try:
                    existing_machine_terms = load_glossary_file(machine_path)
                    merge_glossary_entries(machine_snapshot, existing_machine_terms)
                    refresh_terms()
                except Exception as e:
                    print(f"Could not load existing machine glossary: {e}")
            self.translation_running = True
            self.refresh_active_glossary_tree()
            self.pause_event.clear()
            self.stop_event.clear()
            self.progress_bar.configure(value=0, maximum=100)
            self.progress_var.set(gui_text("progress_idle"))
            self.pause_button.configure(state="normal", text=gui_text("pause"))
            self.stop_button.configure(state="normal")

            def progress_callback(current, total, name, start_time, completed):
                self.log_queue.put(("progress", (current, total, name, start_time, completed)))

            def glossary_callback(items, glossary_path):
                self.log_queue.put(("glossary_update", (items, glossary_path)))

            if source_type.get() == "EPUB":
                self.run_worker(lambda: translate_epub_with_llm(
                    src, out, manual_snapshot, api_config,
                    progress_callback=progress_callback,
                    pause_event=self.pause_event,
                    stop_event=self.stop_event,
                    auto_glossary=auto_glossary.get(),
                    machine_glossary_entries=machine_snapshot,
                    machine_glossary_path=machine_path,
                    use_machine_glossary=use_machine_glossary,
                    glossary_callback=glossary_callback,
                ))
            else:
                self.run_worker(lambda: translate_txt_folder_with_llm(
                    src, out, manual_snapshot, api_config,
                    progress_callback=progress_callback,
                    pause_event=self.pause_event,
                    stop_event=self.stop_event,
                    auto_glossary=auto_glossary.get(),
                    machine_glossary_entries=machine_snapshot,
                    machine_glossary_path=machine_path,
                    use_machine_glossary=use_machine_glossary,
                    glossary_callback=glossary_callback,
                ))
            try:
                win.grab_release()
            except Exception:
                pass
            try:
                win.transient("")
                win.iconify()
            except Exception:
                win.withdraw()
            self.root.lift()

        ttk.Button(bottom, text=gui_text("start_translate"), command=start_translation).pack(side="right")
        self.center_window(win, 1180, 700)

    def open_polish_window(self):
        from tkinter import ttk, filedialog, messagebox

        win = self.tk.Toplevel(self.root)
        win.title(gui_text("polish_tool"))
        win.configure(bg="#fff3dc")
        win.minsize(860, 420)
        self.install_background(win)
        win.transient(self.root)
        win.grab_set()
        win.columnconfigure(0, weight=1)
        win.rowconfigure(2, weight=1)

        api_base = self.tk.StringVar(value=SETTINGS.get("llm_api_base", "https://api.openai.com/v1/chat/completions"))
        api_key = self.tk.StringVar(value=SETTINGS.get("llm_api_key", ""))
        model = self.tk.StringVar(value=SETTINGS.get("llm_model", "gpt-4o-mini"))
        saved_source_path = SETTINGS.get("last_polish_source_path", "")
        saved_translation_path = SETTINGS.get("last_polish_translation_path", "")
        saved_output_path = SETTINGS.get("last_polish_output_path", "")
        source_path = self.tk.StringVar(value=saved_source_path if os.path.isdir(saved_source_path) else "")
        translation_path = self.tk.StringVar(value=saved_translation_path if os.path.isdir(saved_translation_path) else "")
        saved_output_is_folder = (
            saved_output_path
            and not str(saved_output_path).lower().endswith(".txt")
            and os.path.normcase(os.path.abspath(saved_output_path))
            != os.path.normcase(os.path.abspath(saved_translation_path or "."))
        )
        output_path = self.tk.StringVar(value=saved_output_path if saved_output_is_folder else "")
        saved_extra_paths = SETTINGS.get("last_polish_extra_glossary_paths", [])
        if not isinstance(saved_extra_paths, list):
            saved_extra_paths = []
        extra_glossary_paths = [str(path) for path in saved_extra_paths if str(path).strip()]
        default_glossary_text = self.tk.StringVar()
        extra_glossary_text = self.tk.StringVar()
        glossary_split = self.tk.BooleanVar(value=bool(SETTINGS.get("polish_glossary_split", False)))
        glossary_lines = self.tk.StringVar(value=str(SETTINGS.get("polish_glossary_lines", 80)))
        symbol_split = self.tk.BooleanVar(value=bool(SETTINGS.get("polish_symbol_split", False)))
        symbol_lines = self.tk.StringVar(value=str(SETTINGS.get("polish_symbol_lines", 80)))
        text_split = self.tk.BooleanVar(value=bool(SETTINGS.get("polish_text_split", True)))
        text_lines = self.tk.StringVar(value=str(SETTINGS.get("polish_text_lines", 80)))

        form = ttk.Frame(win, padding=12)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text=gui_text("api_base")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=api_base).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(form, text=gui_text("api_key")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=api_key, show="*").grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Label(form, text=gui_text("model")).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=3)
        model_combo = ttk.Combobox(form, textvariable=model, values=[model.get()] if model.get() else [], width=32)
        model_combo.grid(row=2, column=1, sticky="w", pady=3)

        def test_api_models():
            test_button.configure(state="disabled")
            self.status_var.set(gui_text("running"))

            def worker():
                try:
                    models = fetch_llm_models(api_base.get().strip(), api_key.get().strip())
                    self.root.after(0, lambda: on_models_loaded(models, None))
                except Exception as e:
                    self.root.after(0, lambda: on_models_loaded([], e))

            threading.Thread(target=worker, daemon=True).start()

        def on_models_loaded(models, error):
            test_button.configure(state="normal")
            if not (self.worker and self.worker.is_alive()):
                self.status_var.set(gui_text("ready"))
            if error:
                messagebox.showerror(gui_text("error_title"), f"{gui_text('api_unavailable')}\n{error}", parent=win)
                return
            model_combo.configure(values=models, state="readonly")
            if model.get() not in models:
                model.set(models[0])
            messagebox.showinfo(gui_text("done_title"), gui_text("models_loaded"), parent=win)

        test_button = ttk.Button(form, text=gui_text("test_api"), command=test_api_models)
        test_button.grid(row=2, column=2, padx=(8, 0), pady=3)

        def default_output_for_translation(path):
            return default_polish_output_folder(path)

        def refresh_glossary_display(*_):
            paths = default_polish_glossary_paths(translation_path.get().strip())
            default_glossary_text.set(
                " + ".join(os.path.basename(path) for path in paths) or gui_text("no_default_glossary")
            )
            extra_glossary_text.set(" + ".join(os.path.basename(path) for path in extra_glossary_paths))

        def browse_dir(var, title_key, translation=False):
            path = filedialog.askdirectory(parent=win, title=gui_text(title_key))
            if path:
                var.set(path)
                if translation:
                    output_path.set(default_output_for_translation(path))
                refresh_glossary_display()
                persist_polish_paths()

        def browse_output():
            path = filedialog.askdirectory(parent=win, title=gui_text("select_output"))
            if path:
                output_path.set(path)
                persist_polish_paths()

        def import_extra_glossaries():
            paths = filedialog.askopenfilenames(
                parent=win,
                title=gui_text("add_glossary"),
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            )
            for path in paths:
                if path not in extra_glossary_paths:
                    extra_glossary_paths.append(path)
            refresh_glossary_display()
            persist_polish_paths()

        def clear_extra_glossaries():
            extra_glossary_paths.clear()
            refresh_glossary_display()
            persist_polish_paths()

        ttk.Label(form, text=gui_text("source_folder")).grid(row=3, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=source_path).grid(row=3, column=1, sticky="ew", pady=3)
        ttk.Button(form, text=gui_text("browse"), command=lambda: browse_dir(source_path, "select_source")).grid(row=3, column=2, padx=(8, 0), pady=3)

        ttk.Label(form, text=gui_text("translation_path")).grid(row=4, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=translation_path).grid(row=4, column=1, sticky="ew", pady=3)
        ttk.Button(form, text=gui_text("browse"), command=lambda: browse_dir(translation_path, "select_source", translation=True)).grid(row=4, column=2, padx=(8, 0), pady=3)

        ttk.Label(form, text=gui_text("default_glossaries")).grid(row=5, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=default_glossary_text, state="readonly").grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(form, text=gui_text("extra_glossaries")).grid(row=6, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=extra_glossary_text, state="readonly").grid(row=6, column=1, sticky="ew", pady=3)
        extra_buttons = ttk.Frame(form)
        extra_buttons.grid(row=6, column=2, padx=(8, 0), pady=3)
        ttk.Button(extra_buttons, text=gui_text("add_glossary"), command=import_extra_glossaries).pack(side="left")
        ttk.Button(extra_buttons, text=gui_text("clear_glossaries"), command=clear_extra_glossaries).pack(side="left", padx=(6, 0))

        ttk.Label(form, text=gui_text("output_folder")).grid(row=7, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=output_path).grid(row=7, column=1, sticky="ew", pady=3)
        ttk.Button(form, text=gui_text("browse"), command=browse_output).grid(row=7, column=2, padx=(8, 0), pady=3)

        chunk_frame = ttk.LabelFrame(win, text=gui_text("polish_chunk_settings"), padding=10)
        chunk_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        chunk_frame.columnconfigure(0, weight=1)
        ttk.Label(chunk_frame, text=gui_text("polish_chunk_enabled")).grid(row=0, column=1, padx=8)
        ttk.Label(chunk_frame, text=gui_text("polish_lines_per_chunk")).grid(row=0, column=2, padx=8)
        chunk_rows = (
            ("polish_stage_polish", text_split, text_lines),
            ("polish_stage_glossary_check", glossary_split, glossary_lines),
            ("polish_stage_symbol_check", symbol_split, symbol_lines),
        )
        for row_index, (label_key, enabled_var, lines_var) in enumerate(chunk_rows, 1):
            ttk.Label(chunk_frame, text=gui_text(label_key)).grid(row=row_index, column=0, sticky="w", pady=2)
            ttk.Checkbutton(chunk_frame, variable=enabled_var).grid(row=row_index, column=1, pady=2)
            ttk.Entry(chunk_frame, textvariable=lines_var, width=10).grid(row=row_index, column=2, pady=2)

        guide_frame = ttk.LabelFrame(win, text=gui_text("polish_guide"), padding=12)
        guide_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        guide_frame.columnconfigure(0, weight=1)
        guide_frame.rowconfigure(0, weight=1)
        guide_box = self.tk.Text(guide_frame, wrap="word", width=80, height=8, bg="#fffaf2", fg="#4b2a24", insertbackground="#d9577a", padx=8, pady=8)
        guide_box.grid(row=0, column=0, sticky="nsew")
        guide_box.insert("1.0", SETTINGS.get("polish_style", "") or DEFAULT_POLISH_GUIDE)

        def persist_polish_paths():
            SETTINGS["last_polish_source_path"] = source_path.get().strip()
            SETTINGS["last_polish_translation_path"] = translation_path.get().strip()
            SETTINGS["last_polish_output_path"] = output_path.get().strip()
            SETTINGS["last_polish_glossary_path"] = ""
            SETTINGS["last_polish_extra_glossary_paths"] = list(extra_glossary_paths)
            save_config()

        def translation_path_changed(*_):
            refresh_glossary_display()
            if not output_path.get().strip() and translation_path.get().strip():
                output_path.set(default_output_for_translation(translation_path.get().strip()))

        translation_path.trace_add("write", translation_path_changed)
        translation_path_changed()

        bottom = ttk.Frame(win, padding=(12, 0, 12, 12))
        bottom.grid(row=3, column=0, sticky="ew")

        def start_polish():
            if self.worker and self.worker.is_alive():
                messagebox.showwarning(gui_text("error_title"), gui_text("task_running"), parent=win)
                return
            source_folder = source_path.get().strip()
            translation_folder = translation_path.get().strip()
            if not api_key.get().strip() or not model.get().strip() or not source_folder or not translation_folder:
                messagebox.showwarning(gui_text("error_title"), gui_text("missing_polish_config"), parent=win)
                return
            if not os.path.isdir(source_folder) or not os.path.isdir(translation_folder):
                messagebox.showwarning(gui_text("error_title"), gui_text("missing_polish_config"), parent=win)
                return
            translation_files = sorted(list_txt_files(translation_folder))
            if not translation_files:
                messagebox.showwarning(gui_text("error_title"), gui_text("log_no_txt_files"), parent=win)
                return
            missing_names = [
                os.path.basename(path)
                for path in translation_files
                if not os.path.isfile(os.path.join(source_folder, os.path.basename(path)))
            ]
            if missing_names:
                preview = ", ".join(missing_names[:10])
                if len(missing_names) > 10:
                    preview += f" ... (+{len(missing_names) - 10})"
                messagebox.showwarning(
                    gui_text("error_title"),
                    gui_text("missing_source_pairs").format(names=preview),
                    parent=win,
                )
                return
            try:
                stage_chunking = {
                    "glossary_check": {
                        "enabled": glossary_split.get(),
                        "lines": int(glossary_lines.get().strip()),
                    },
                    "symbol_check": {
                        "enabled": symbol_split.get(),
                        "lines": int(symbol_lines.get().strip()),
                    },
                    "polish": {
                        "enabled": text_split.get(),
                        "lines": int(text_lines.get().strip()),
                    },
                }
                if any(settings["lines"] <= 0 for settings in stage_chunking.values()):
                    raise ValueError
            except (TypeError, ValueError):
                messagebox.showwarning(gui_text("error_title"), gui_text("invalid_polish_lines"), parent=win)
                return
            SETTINGS["llm_api_base"] = api_base.get().strip()
            SETTINGS["llm_api_key"] = api_key.get().strip()
            SETTINGS["llm_model"] = model.get().strip()
            SETTINGS["polish_style"] = guide_box.get("1.0", "end").strip()
            SETTINGS["polish_glossary_split"] = stage_chunking["glossary_check"]["enabled"]
            SETTINGS["polish_glossary_lines"] = stage_chunking["glossary_check"]["lines"]
            SETTINGS["polish_symbol_split"] = stage_chunking["symbol_check"]["enabled"]
            SETTINGS["polish_symbol_lines"] = stage_chunking["symbol_check"]["lines"]
            SETTINGS["polish_text_split"] = stage_chunking["polish"]["enabled"]
            SETTINGS["polish_text_lines"] = stage_chunking["polish"]["lines"]
            persist_polish_paths()
            try:
                glossary_entries, _ = load_polish_glossaries(translation_folder, extra_glossary_paths)
            except Exception as e:
                messagebox.showerror(gui_text("error_title"), str(e), parent=win)
                return
            api_config = {
                "api_base": SETTINGS["llm_api_base"],
                "api_key": SETTINGS["llm_api_key"],
                "model": SETTINGS["llm_model"],
                "polish_guide": SETTINGS.get("polish_style", ""),
                "stage_chunking": stage_chunking,
            }
            out = output_path.get().strip() or default_output_for_translation(translation_folder)
            if os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(translation_folder)):
                messagebox.showwarning(gui_text("error_title"), gui_text("invalid_polish_output"), parent=win)
                return
            output_path.set(out)
            persist_polish_paths()
            self.translation_running = True
            self.pause_event.clear()
            self.stop_event.clear()
            self.progress_bar.configure(value=0, maximum=100)
            self.progress_var.set(gui_text("progress_idle"))
            self.pause_button.configure(state="normal", text=gui_text("pause"))
            self.stop_button.configure(state="normal")

            def progress_callback(current, total, name, start_time, completed):
                self.log_queue.put(("progress", (current, total, name, start_time, completed)))

            self.run_worker(lambda: polish_txt_folder_with_llm(
                source_folder,
                translation_folder,
                out,
                glossary_entries,
                api_config,
                progress_callback=progress_callback,
                pause_event=self.pause_event,
                stop_event=self.stop_event,
            ))
            try:
                win.grab_release()
            except Exception:
                pass
            try:
                win.transient("")
                win.iconify()
            except Exception:
                win.withdraw()
            self.root.lift()

        ttk.Button(bottom, text=gui_text("start_polish"), command=start_polish).pack(side="right")
        ttk.Button(bottom, text=gui_text("cancel"), command=win.destroy).pack(side="right", padx=(0, 8))
        self.center_window(win, 1120, 760)

    def reset_driver_path(self):
        global chrome_driver_path
        chrome_driver_path = "NONE"
        save_config()
        self.append_log(gui_text("driver_reset"))

    def on_close(self):
        if self.worker and self.worker.is_alive():
            from tkinter import messagebox
            if not messagebox.askyesno(gui_text("task_running_title"), gui_text("task_running")):
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def is_supported_url(novel_url):
    url_lower = novel_url.lower()
    if "sbxh" in url_lower:
        return True
    return any(site_key in url_lower for site_key in SITE_HANDLERS)


def ensure_chromedriver_for_gui():
    global chrome_driver_path
    if chrome_driver_path not in ("NONE", "C:/Program Files") and os.path.exists(chrome_driver_path):
        return True
    print(f"{T()}[{T2()}!{T()}]{w} ChromeDriver path is missing. Downloading ChromeDriver...")
    new_driver_path = download_chromedriver()
    if not new_driver_path:
        print(f"{r}[{w}X{r}]{w} Failed to download ChromeDriver.")
        return False
    chrome_driver_path = new_driver_path
    save_config()
    return True


def get_novelpia_profile_dir():
    profile_dir = str(SETTINGS.get("novelpia_profile_dir", "") or "").strip()
    if not profile_dir:
        profile_dir = auto_novelpia_profile_dir()
    profile_dir = os.path.abspath(os.path.expanduser(profile_dir))
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def open_novelpia_regular_chrome_login():
    chrome_path = find_chrome_executable()
    profile_dir = get_novelpia_profile_dir()
    args = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--new-window",
        "https://novelpia.com/",
    ]
    return subprocess.Popen(args)


def create_novelpia_chrome_options():
    profile_dir = get_novelpia_profile_dir()
    options = Options()
    options.page_load_strategy = "eager"
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--lang=ko-KR")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    print(_novelpia_text(
        f"Novelpia 浏览器资料目录：{profile_dir}",
        f"Novelpia browser profile: {profile_dir}",
    ))
    return options


def create_plain_chrome_driver(chrome_options):
    global chrome_driver_path

    """
    Start Chrome for non-Cloudflare sites.

    Selenium Manager is tried first so ChromeDriver can match the user's
    installed Chrome version. A configured/bundled driver remains as an offline
    fallback for older setups.
    """
    errors = []

    try:
        print(f"{T()}[{T2()}!{T()}]{w} Starting Chrome with Selenium Manager...")
        return webdriver.Chrome(options=chrome_options)
    except selenium.common.exceptions.WebDriverException as e:
        errors.append(f"Selenium Manager: {e}")

    if chrome_driver_path not in ("NONE", "C:/Program Files") and os.path.exists(chrome_driver_path):
        try:
            print(f"{T()}[{T2()}!{T()}]{w} Falling back to configured ChromeDriver: {chrome_driver_path}")
            driver_service = Service(executable_path=chrome_driver_path, log_path=os.devnull)
            return webdriver.Chrome(service=driver_service, options=chrome_options)
        except selenium.common.exceptions.WebDriverException as e:
            errors.append(f"Configured ChromeDriver: {e}")

    new_driver_path = download_chromedriver()
    if new_driver_path:
        chrome_driver_path = new_driver_path
        save_config()
        try:
            print(f"{T()}[{T2()}!{T()}]{w} Starting Chrome with downloaded ChromeDriver...")
            driver_service = Service(executable_path=chrome_driver_path, log_path=os.devnull)
            return webdriver.Chrome(service=driver_service, options=chrome_options)
        except selenium.common.exceptions.WebDriverException as e:
            errors.append(f"Downloaded ChromeDriver: {e}")

    detail = "\n".join(errors[-3:])
    raise RuntimeError(
        "Could not start Chrome. Please update Chrome, reset ChromeDriver, "
        f"or install a matching ChromeDriver.\n{detail}"
    )


def gui_scrape_novel(novel_url):
    if not is_supported_url(novel_url):
        print(f"{r}[{w}X{r}]{w} Not a supported site. Please enter a valid URL.")
        return

    url_lower = novel_url.lower()
    is_sbxh = "sbxh" in url_lower
    is_novelpia = "novelpia.com" in url_lower
    driver = None

    if is_sbxh:
        print(f"{T()}[{T2()}!{T()}]{w} Launching undetected Chrome for Cloudflare bypass...")
        try:
            chrome_major = get_chrome_major_version()
            print(f"{T()}[{T2()}!{T()}]{w} Detected Chrome major version: {chrome_major}")
            uc_options = uc.ChromeOptions()
            uc_options.add_argument("--disable-blink-features=AutomationControlled")
            uc_options.add_argument("--disable-notifications")
            uc_options.add_argument("--disable-popup-blocking")
            uc_options.add_argument("--start-maximized")
            driver = uc.Chrome(
                options=uc_options,
                headless=False,
                use_subprocess=True,
                version_main=chrome_major,
            )
            configure_sbxh_browser(driver)
        except Exception as e:
            explanation = explain_undetected_chrome_error(e)
            if explanation:
                print(f"{r}[{w}X{r}]{w} {explanation}")
            raise
    elif is_novelpia:
        driver = create_plain_chrome_driver(create_novelpia_chrome_options())
    else:
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.managed_default_content_settings.media_stream": 2,
        })
        driver = create_plain_chrome_driver(chrome_options)

    try:
        dispatch_handler(driver, novel_url)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def run_gui():
    try:
        app = NibbleGUI()
        app.run()
    except ImportError as e:
        print(f"Tkinter is not available: {e}")
        print("Falling back to CLI mode.")
        main()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        main()
    else:
        run_gui()
