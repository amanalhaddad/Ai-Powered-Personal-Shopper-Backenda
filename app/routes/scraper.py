from fastapi import APIRouter, Query, Body
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import re
import asyncio
import os
import random
import json
from typing import Optional

router = APIRouter()

# ---------------------------------------------------------
#  SETUP: NINJA MODE 🥷 (Anti-Detection)
# ---------------------------------------------------------
def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    options.page_load_strategy = 'normal'

    # [STEALTH] Randomize Window Size
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    # [STEALTH] Disable Automation Flags
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    
    # [CRITICAL] Use the persistent profile
    profile_path = os.path.join(os.getcwd(), "shopee_profile")
    
    driver = uc.Chrome(
        options=options, 
        use_subprocess=True, 
        version_main=143,           
        user_data_dir=profile_path 
    )
    return driver

# ---------------------------------------------------------
#  ENDPOINT 1: SEARCH (Now with Puzzle Detection!)
# ---------------------------------------------------------
@router.get("/shopee/search", summary="Search Shopee")
async def search_shopee(keyword: str = Query(..., description="Search keyword")):
    driver = None
    try:
        loop = asyncio.get_event_loop()
        
        def run_scraper():
            driver = setup_driver()
            url = f"https://shopee.com.my/search?keyword={keyword}"
            print(f"DEBUG: Search Loading '{keyword}'...")
            driver.get(url)
            
            # [FIX] Give page time to load
            time.sleep(5)

            # [FIX] Smart Puzzle Detector (Added back!)
            # It checks for 15 seconds. If a slider appears, it waits for you.
            for i in range(15):
                src = driver.page_source.lower()
                if "slider" in src or "verification" in src or "shopee-captcha" in src:
                    print(f"⚠️ PUZZLE DETECTED! Please solve it manually... ({i+1}/15)")
                    time.sleep(2)
                else:
                    break # No puzzle? Good to go.

            print("DEBUG: Puzzle clear. Scrolling safely...")
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(1.0, 2.0))
            
            html_source = driver.page_source
            driver.quit()
            return html_source

        html_source = await loop.run_in_executor(None, run_scraper)

        # --- STEP A: SURGICAL CUT ---
        split_keyword = "Sort by"
        if split_keyword in html_source:
            split_index = html_source.find(split_keyword)
            html_source = html_source[split_index:]

        # --- STEP B: LINK HUNTER ---
        soup = BeautifulSoup(html_source, "html.parser")
        results = []
        unique_urls = set()

        potential_items = soup.find_all("a", href=lambda href: href and "-i." in href)

        for link_tag in potential_items:
            try:
                url = link_tag.get("href")
                if not url or url in unique_urls: continue
                
                card = link_tag.find_parent("div")
                if not card: card = link_tag.parent.parent
                
                text_content = card.get_text(separator=" ", strip=True)
                
                price = 0.0
                match = re.search(r"RM\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text_content)
                if match: price = float(match.group(1).replace(",", ""))
                
                if price == 0: continue

                img_tag = card.find("img")
                img = img_tag.get("src") if img_tag else ""
                
                raw_title = text_content.split("RM")[0][:100].strip()
                clean_name = re.sub(r"Ad\s|Local Seller|Preferred|Mall", "", raw_title).strip()

                unique_urls.add(url)
                results.append({
                    "name": clean_name,
                    "price": price,
                    "link": f"https://shopee.com.my{url}" if not url.startswith("http") else url,
                    "image": img,
                    "source": "shopee"
                })
                if len(results) >= 15: break 
            except Exception as e:
                continue

        return {"keyword": keyword, "count": len(results), "products": results}

    except Exception as e:
        if driver: 
            try: driver.quit() 
            except: pass
        return {"error": str(e), "count": 0, "products": []}

# ---------------------------------------------------------
#  ENDPOINT 2: INGEST (Hybrid Mode + Puzzle Detection)
# ---------------------------------------------------------
@router.post("/shopee/ingest", summary="Get Product Details")
async def ingest_shopee_item(
    url: str = Query(..., description="Product URL"),
    html_source: Optional[str] = Body(None, description="Optional: Raw HTML from extension")
):
    driver = None
    try:
        loop = asyncio.get_event_loop()

        # HELPER: Selenium Logic (Only runs if HTML is missing)
        def run_browser_scraper():
            driver = setup_driver()
            print(f"DEBUG: Selenium Visiting -> {url}")
            driver.get(url)
            
            # [FIX] Give page time to load
            time.sleep(5)

            # [FIX] Smart Puzzle Detector
            for i in range(15): 
                src = driver.page_source.lower()
                if "slider" in src or "verification" in src or "shopee-captcha" in src:
                    print(f"⚠️ PUZZLE DETECTED! Please solve it manually... ({i+1}/15)")
                    time.sleep(2) 
                else:
                    break 

            print("DEBUG: Scrolling to load details...")
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 700);")
                time.sleep(random.uniform(0.5, 1.5))
            
            src = driver.page_source
            driver.quit()
            return src

        # [LOGIC SWITCH]
        if html_source:
            print("DEBUG: Using provided HTML (Extension Mode) ⚡")
            final_html = html_source
        else:
            print("DEBUG: No HTML provided (Swagger Mode) 🐢")
            final_html = await loop.run_in_executor(None, run_browser_scraper)
            
        # --- PARSING LOGIC (Shared) ---
        soup = BeautifulSoup(final_html, "html.parser")
        
        data = {
            "url": url, 
            "source": "shopee",
            "name": "",
            "price": 0,
            "price_range": "", 
            "currency": "MYR",
            "rating": "N/A",
            "reviews": "0", 
            "stock": "Unknown",
            "description": "",
            "image": ""
        }

        page_text = soup.get_text(separator=" ") 

        # LAYER 1: JSON-LD
        script_tag = soup.find("script", {"type": "application/ld+json"})
        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if isinstance(json_data, dict) and json_data.get("@type") == "Product":
                    data["name"] = json_data.get("name", "")
                    data["description"] = json_data.get("description", "")
                    data["image"] = json_data.get("image", "")
                    
                    offers = json_data.get("offers", {})
                    data["price"] = offers.get("price", 0)
                    
                    agg = json_data.get("aggregateRating", {})
                    if agg:
                        data["rating"] = str(agg.get("ratingValue", "N/A"))
                        data["reviews"] = str(agg.get("reviewCount", "0"))
            except: pass

        # LAYER 2: META TAGS
        if not data["name"]:
            og_title = soup.find("meta", property="og:title")
            if og_title: data["name"] = og_title["content"]
        if not data["image"]:
            og_image = soup.find("meta", property="og:image")
            if og_image: data["image"] = og_image["content"]

        # LAYER 3: VISUAL HUNT
        if data["rating"] == "N/A":
            rating_match = re.search(r"(\d\.\d)\s*out of 5", page_text)
            if rating_match: data["rating"] = rating_match.group(1)

        if data["reviews"] == "0":
            local_review_match = re.search(r"Local Review\s*\((\d+)\)", page_text, re.IGNORECASE)
            if local_review_match:
                data["reviews"] = local_review_match.group(1)
            else:
                review_match = re.search(r"(\d+(?:[.,]\d+)?\w?)\s?Ratings", page_text, re.IGNORECASE)
                if review_match: data["reviews"] = review_match.group(1)

        range_match = re.search(r"(RM\s?[\d,.]+\s?-\s?RM\s?[\d,.]+)", page_text)
        if range_match:
            data["price_range"] = range_match.group(1)
        
        if data["price"] == 0:
            price_match = re.search(r"RM\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", page_text)
            if price_match:
                data["price"] = float(price_match.group(1).replace(",", ""))

        if data["stock"] == "Unknown":
            stock_label = soup.find(string=lambda t: t and "Stock" in t and len(t) < 20)
            if stock_label:
                parent = stock_label.find_parent()
                if parent:
                    next_sib = parent.find_next_sibling()
                    if next_sib: data["stock"] = next_sib.get_text(strip=True)

        if not data["description"] or len(data["description"]) < 50:
            desc_label = soup.find(string="Product Description")
            if desc_label:
                container = desc_label.find_parent("div")
                if container and container.parent:
                    full_text = container.parent.get_text(separator="\n").replace("Product Description", "").strip()
                    data["description"] = full_text[:1500] 

        return data

    except Exception as e:
        if driver: 
            try: driver.quit() 
            except: pass
        return {"error": str(e)}