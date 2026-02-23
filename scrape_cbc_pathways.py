"""
Scraper for https://selection.education.go.ke/pathways

Key insight from debugging:
- Page loads with STEM already EXPANDED (tracks visible)
- Clicking a pathway HEADER collapses it (hides tracks)
- To switch pathway: click the COLLAPSED one to open it (which closes the current one)
- Tracks are always the block buttons visible in the currently expanded pathway

Strategy:
  1. Page loads → STEM is open → scrape STEM tracks directly
  2. Click SOCIAL SCIENCES header → it opens, STEM closes → scrape those tracks
  3. Click ARTS & SPORTS SCIENCE header → scrape those tracks

Requirements:
    pip install selenium webdriver-manager pandas beautifulsoup4
"""

import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://selection.education.go.ke/pathways"

# Order matters: STEM is open on page load, then we open the others
PATHWAY_TRACKS = [
    ("STEM",                 ["PURE SCIENCES", "APPLIED SCIENCES", "TECHNICAL STUDIES"]),
    ("SOCIAL SCIENCES",      ["LANGUAGES & LITERATURE", "HUMANITIES & BUSINESS STUDIES"]),
    ("ARTS & SPORTS SCIENCE",["ARTS", "SPORTS"]),
]

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver

def safe_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", element)

def open_pathway(driver, pathway_name):
    """
    Open a pathway by clicking its collapse header.
    Only click if it is currently COLLAPSED (not active).
    If already active/open, do nothing.
    """
    panels = driver.find_elements(By.CSS_SELECTOR, ".ant-collapse-item")
    for panel in panels:
        header = panel.find_elements(By.CSS_SELECTOR, ".ant-collapse-header")
        if not header:
            continue
        header_text = header[0].text.strip().upper()
        # Match pathway name (strip emojis by checking if name is contained)
        if pathway_name.upper() in header_text:
            classes = panel.get_attribute("class")
            if "ant-collapse-item-active" in classes:
                print(f"  ✅ '{pathway_name}' already open")
                return True
            else:
                print(f"  🔓 Opening '{pathway_name}'...")
                safe_click(driver, header[0])
                time.sleep(2.5)
                return True
    print(f"  ❌ Could not find pathway: {pathway_name}")
    return False

def click_track(driver, track_name):
    """Click the track button whose text contains track_name."""
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if track_name.upper() in btn.text.upper():
            safe_click(driver, btn)
            time.sleep(2)
            return True
    print(f"    ❌ Track button not found: {track_name}")
    return False

def wait_for_programs(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(
                By.XPATH, "//*[contains(text(),'Code:') and contains(text(),'Track:')]"
            )) > 0
        )
    except Exception:
        pass
    time.sleep(1)

def scroll_to_load_all(driver):
    last_h = driver.execute_script("return document.body.scrollHeight")
    for _ in range(20):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.7)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h
    driver.execute_script("window.scrollTo(0, 0);")

def parse_programs(driver, pathway_name, track_name):
    records = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    code_pattern = re.compile(r"Code:\s*(\w+)\s*\|\s*Track:\s*(.+)")

    links = soup.find_all("a", href=re.compile(r"^/pathways/[0-9a-f\-]{36}$"))
    for link in links:
        pathway_id = link["href"].split("/pathways/")[1]

        # Walk up to find card container with code info
        card = link.parent
        for _ in range(8):
            if card and code_pattern.search(card.get_text()):
                break
            card = card.parent if card else None
        if not card:
            continue

        lines = [l.strip() for l in card.get_text(separator="\n").splitlines() if l.strip()]
        subjects, code, detected_track = "", "", ""

        for line in lines:
            m = code_pattern.search(line)
            if m:
                code = m.group(1).strip()
                detected_track = m.group(2).strip()
            elif "View Schools" not in line and not subjects and len(line) > 2:
                subjects = line

        if code:
            records.append({
                "pathway":      pathway_name,
                "track":        track_name or detected_track,
                "subjects":     subjects,
                "program_code": code,
                "pathway_id":   pathway_id,
            })
    return records

def scrape():
    driver = init_driver()
    all_records = []

    try:
        print(f"Loading {URL} ...")
        driver.get(URL)
        time.sleep(5)  # wait for full JS render

        for pathway_name, tracks in PATHWAY_TRACKS:
            print(f"\n📚 Pathway: {pathway_name}")
            open_pathway(driver, pathway_name)

            for track_name in tracks:
                print(f"  🔬 Track: {track_name}")
                if not click_track(driver, track_name):
                    continue

                wait_for_programs(driver)
                scroll_to_load_all(driver)

                records = parse_programs(driver, pathway_name, track_name)
                print(f"    📋 {len(records)} programs found")
                all_records.extend(records)

    finally:
        driver.quit()

    return all_records

def save_csv(records, filename="pathways_full.csv"):
    if not records:
        print("\n❌ No records collected.")
        return

    df = pd.DataFrame(records)
    df.drop_duplicates(subset=["program_code"], inplace=True)
    df.sort_values(["pathway", "track", "program_code"], inplace=True)
    df.to_csv(filename, index=False, encoding="utf-8")

    print(f"\n✅ Saved {len(df)} programs to 'pathways_full.csv'")
    print(f"\nBreakdown by pathway & track:")
    print(df.groupby(["pathway", "track"]).size().rename("programs").to_string())
    print(f"\nFirst 5 rows:")
    print(df.head(5).to_string(index=False))

if __name__ == "__main__":
    records = scrape()
    save_csv(records)
