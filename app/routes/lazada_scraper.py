from fastapi import APIRouter, HTTPException, Query, Body
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import re
import asyncio
import os
import json
from urllib.parse import unquote
from typing import Optional

router = APIRouter()

# ---------------------------
# Helpers
# ---------------------------
def _extract_price_from_url(url: str):
    try:
        decoded = unquote(url)
        matches = re.findall(r'(?:displayPrice|shopPrice|voucherPrice|price)[:=](\d+)', decoded)
        candidates = []
        for m in matches:
            val = float(m)
            if val > 100: val = val / 100.0
            candidates.append(val)
        if candidates: return min(candidates)
    except: pass
    return None

def _clean_price(text):
    if not text: return 0.0
    clean = re.sub(r"[^\d.]", "", text)
    try: return float(clean)
    except: return 0.0

# ---------------------------------------------------------
#  SETUP: LAZADA PROFILE
# ---------------------------------------------------------
def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    options.page_load_strategy = 'normal'
    
    # [CRITICAL] Use the persistent 'lazada_profile' folder
    profile_path = os.path.join(os.getcwd(), "lazada_profile")
    
    driver = uc.Chrome(
        options=options, 
        use_subprocess=True, 
        version_main=143,           
        user_data_dir=profile_path 
    )
    return driver

# ---------------------------------------------------------
#  ENDPOINT 1: SEARCH (Unchanged)
# ---------------------------------------------------------
@router.get("/lazada/search", summary="Search Lazada")
async def search_lazada(keyword: str = Query(..., description="Search keyword")):
    driver = None
    try:
        loop = asyncio.get_event_loop()
        
        def run_scraper():
            driver = setup_driver()
            url = f"https://www.lazada.com.my/catalog/?q={keyword}"
            print(f"DEBUG: Lazada Search Loading '{keyword}'...")
            driver.get(url)
            
            # Wait & Scroll to trigger data loading
            time.sleep(3) 
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            html_source = driver.page_source
            driver.quit()
            return html_source

        html_source = await loop.run_in_executor(None, run_scraper)
        
        results = []
        soup = BeautifulSoup(html_source, "html.parser")

        # --- STRATEGY A: JSON HUNTING (Best Data) ---
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "window.pageData=" in script.string:
                try:
                    json_text = script.string.replace("window.pageData=", "").strip()
                    if json_text.endswith(";"): json_text = json_text[:-1]
                    
                    data = json.loads(json_text)
                    list_items = data.get("mods", {}).get("listItems", [])
                    
                    print(f"DEBUG: Found {len(list_items)} items in JSON.")
                    
                    for item in list_items[:15]:
                        name = item.get("name") or item.get("title") or item.get("itemTitle") or "Unknown Product"
                        price = float(item.get("price", 0))
                        if price == 0: price = float(item.get("originalPrice", 0))
                        
                        link = item.get("productUrl", "")
                        if link and not link.startswith("http"): link = f"https:{link}"
                        
                        img = item.get("image", "")
                        if not img or "data:image" in img:
                            thumbs = item.get("thumbs", [])
                            if thumbs and len(thumbs) > 0:
                                img = thumbs[0].get("image", "")
                        if not img: img = ""

                        results.append({
                            "name": name,
                            "price": price,
                            "link": link,
                            "image": img,
                            "source": "lazada"
                        })
                    break 
                except: pass

        # --- STRATEGY B: HTML FALLBACK (If JSON failed) ---
        if not results:
            print("⚠️ JSON not found. Switching to HTML Fallback.")
            potential_items = soup.find_all("div", {"data-qa-locator": "product-item"})
            
            for item in potential_items[:15]:
                try:
                    name_tag = item.find("a", title=True) 
                    if name_tag:
                        name = name_tag["title"]
                    else:
                        links = item.find_all("a")
                        name = "Unknown Product"
                        for l in links:
                            txt = l.get_text(strip=True)
                            if len(txt) > 10:
                                name = txt
                                break

                    link_tag = item.find("a")
                    href = link_tag.get("href") if link_tag else ""
                    if href and not href.startswith("http"): href = f"https:{href}"

                    price_tag = item.find("span", string=re.compile(r"RM"))
                    price = 0.0
                    if price_tag:
                        price = float(re.sub(r"[^\d.]", "", price_tag.get_text()))

                    img_tag = item.find("img")
                    img = ""
                    if img_tag:
                        img = img_tag.get("src", "")
                        if "data:image" in img:
                            img = img_tag.get("data-src") or ""

                    results.append({
                        "name": name,
                        "price": price,
                        "link": href,
                        "image": img,
                        "source": "lazada"
                    })
                except: continue

        return {"keyword": keyword, "count": len(results), "products": results}

    except Exception as e:
        if driver: 
            try: driver.quit() 
            except: pass
        return {"error": str(e), "count": 0, "products": []}

# ---------------------------------------------------------
#  ENDPOINT 2: INGEST (Hybrid Mode Enabled ⚡)
# ---------------------------------------------------------
@router.post("/lazada/ingest", summary="Get Product Details")
async def ingest_lazada_item(
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
            time.sleep(3)
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1)
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1)
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

        soup = BeautifulSoup(final_html, "html.parser")

        data = {
            "url": url, 
            "source": "lazada",
            "name": "",
            "price": 0,
            "rating": "N/A",
            "reviews": "0", 
            "stock": "IN STOCK",
            "description": "",
            "image": ""
        }

        # --- LAYER 1: JSON DATA (ModuleData) ---
        scripts = soup.find_all("script")
        module_data = None
        
        for script in scripts:
            if script.string and "__moduleData__" in script.string:
                try:
                    match = re.search(r"__moduleData__\s*=\s*({.*?});", script.string, re.DOTALL)
                    if match:
                        module_data = json.loads(match.group(1))
                        break
                except: pass

        if module_data:
            fields = module_data.get("data", {}).get("root", {}).get("fields", {})
            
            data["name"] = fields.get("product", {}).get("title", "")

            # Price Check (Sale Price vs Original)
            sku_infos = fields.get("skuInfos", {})
            if sku_infos:
                first_sku = next(iter(sku_infos.values()))
                data["price"] = float(first_sku.get("price", {}).get("salePrice", {}).get("value", 0))
            
            if data["price"] == 0:
                price_val = fields.get("price", {}).get("originalPrice", {}).get("value", 0)
                if price_val: data["price"] = float(price_val)

            desc_html = fields.get("product", {}).get("desc", "")
            if desc_html:
                data["description"] = BeautifulSoup(desc_html, "html.parser").get_text(separator="\n").strip()[:1500]

            review_json = fields.get("review", {}).get("ratings", {})
            if review_json:
                data["rating"] = str(review_json.get("average", "N/A"))
                data["reviews"] = str(review_json.get("rateCount", "0"))

            gallery = fields.get("skuGalleries", {}).get("0", [])
            if gallery and len(gallery) > 0:
                data["image"] = gallery[0].get("src", "")

        # --- LAYER 2: VISUAL HUNT ---
        page_text = soup.get_text(separator=" ")

        if data["price"] == 0:
            price_match = re.search(r"RM\s?([\d,]+\.?\d{2})", page_text)
            if price_match:
                data["price"] = _clean_price(price_match.group(1))

        if data["rating"] == "N/A":
            rating_match = re.search(r"(\d\.\d|\d)\s?/\s?5", page_text)
            if rating_match: data["rating"] = rating_match.group(1)

        if data["reviews"] == "0":
            rev_match = re.search(r"Reviews\s?\(\s?(\d+)\s?\)", page_text, re.IGNORECASE)
            if not rev_match:
                rev_match = re.search(r"(\d+)\s?Ratings", page_text, re.IGNORECASE)
            if rev_match: data["reviews"] = rev_match.group(1)

        if not data["image"] or "data:image" in data["image"]:
            img_tag = soup.find("img", class_="pdp-mod-common-image")
            if img_tag: data["image"] = img_tag.get("src", "")

        if not data["name"]:
            h1 = soup.find("h1")
            if h1: data["name"] = h1.get_text(strip=True)

        return data

    except Exception as e:
        if driver: 
            try: driver.quit() 
            except: pass
        return {"error": str(e)}