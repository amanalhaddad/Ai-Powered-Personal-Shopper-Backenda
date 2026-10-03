# FILE: app/routes/search.py
from fastapi import APIRouter, HTTPException
from app.services.recommender import recommender_service 
from app.routes.scraper import search_shopee, ingest_shopee_item 
from app.routes.lazada_scraper import ingest_lazada_item, search_lazada 
from app.services.user_service import user_service
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from google import genai 
import asyncio
import json
import traceback

router = APIRouter() 

# --- SETUP AI ---
chat_client = None
MODEL_NAME = 'gemini-2.5-flash-lite'

if settings.GOOGLE_API_KEY:
    chat_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# --- 1. SEARCH ENDPOINT (GET) ---
@router.get("/", summary="Semantic Search")
async def semantic_search(query: str, top_k: int = 5):
    try:
        results = await recommender_service.search_products(query=query, top_k=top_k)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. ANALYZE ENDPOINT (POST) ---
class AnalyzeRequest(BaseModel):
    query: str
    product_url: str
    html_content: Optional[str] = None 

@router.post("/analyze")
async def analyze_product(request: AnalyzeRequest):
    try:
        product_details = {}
        if "lazada" in request.product_url:
            product_details = await ingest_lazada_item(request.product_url, request.html_content)
        elif "shopee" in request.product_url:
            product_details = await ingest_shopee_item(request.product_url, request.html_content)
        
        if "error" in product_details:
             raise HTTPException(status_code=400, detail=product_details['error'])

        try:
            ai_advice = await recommender_service.generate_buying_advice(
                user_query=request.query, 
                product_data=product_details
            )
        except Exception as e:
            print(f"⚠️ AI Advice Error: {e}")
            ai_advice = "This product looks good based on the specs (AI unavailable)."

        return {"product_name": product_details.get("name"), "ai_advice": ai_advice, "full_specs": product_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. SMART CHAT ENDPOINT ---
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None 

@router.post("/chat", summary="Chat with AI Shopper")
async def chat_with_shopper(request: ChatRequest):
    try:
        if not chat_client:
             raise HTTPException(status_code=503, detail="AI Service unavailable.")

        user_id = request.user_id
        user_msg = request.message
        
        # A. Session Management
        session_id = request.session_id
        if not session_id:
            session_id = await user_service.create_session(user_id, user_msg)
        
        await user_service.add_message(session_id, "user", user_msg)

        # B. INTENT DETECTION
        keyword = None
        brand = None
        
        try:
            intent_prompt = f"""
            User said: "{user_msg}"
            Task: Extract the shopping keyword AND any specific brand name.
            Output JSON: {{ "keyword": "search term", "brand": "brand name or null" }}
            """
            
            intent_resp = chat_client.models.generate_content(
                model=MODEL_NAME, 
                contents=intent_prompt,
                config={'response_mime_type': 'application/json'}
            )
            intent_data = json.loads(intent_resp.text)
            keyword = intent_data.get("keyword")
            brand = intent_data.get("brand")
            
        except Exception as e:
            print(f"⚠️ Intent Error (Quota/Model): {e}")
            keyword = user_msg
            brand = None

        products = []
        ai_reply = ""
        
        if keyword:
            print(f"DEBUG: 🕵️ Keyword: {keyword} | Brand: {brand}")
            
            # STEP 1: Check Memory
            products = await recommender_service.search_products(query=keyword, brand=brand, top_k=4)
            
            if products:
                ai_reply = f"I found these relevant items from our history:"
            else:
                # STEP 2: Live Scraping (STAGGERED)
                print("DEBUG: 📉 Launching Scrapers...")
                
                async def delayed_lazada(k):
                    await asyncio.sleep(4) # 4s delay to prevent browser conflict
                    return await search_lazada(k)

                results = await asyncio.gather(
                    search_shopee(keyword), 
                    delayed_lazada(keyword),
                    return_exceptions=True
                )
                
                shopee_res = results[0] if isinstance(results[0], dict) else {}
                lazada_res = results[1] if isinstance(results[1], dict) else {}

                s_items = shopee_res.get("products", [])
                l_items = lazada_res.get("products", [])

                # -----------------------------------------------------
                # NEW: AI "JUDGE" STEP (LOGICAL FILTERING) 🧠
                # -----------------------------------------------------
                selected_products = []
                
                # COMBINE ALL ITEMS (Do not filter by price yet!)
                # We send ALL candidates to Gemini so it can filter out junk/cases.
                candidates = s_items + l_items

                if candidates:
                    try:
                        print(f"DEBUG: Sending {len(candidates)} items to AI for judging...")
                        
                        # Prepare simplified data for AI to save tokens
                        candidates_json = json.dumps([{
                            "id": i, 
                            "name": p["name"], 
                            "price": p["price"], 
                            "source": p["source"]
                        } for i, p in enumerate(candidates)])

                        judge_prompt = f"""
                        User Request: "{user_msg}" (Search: {keyword})
                        
                        Here are {len(candidates)} scraped items:
                        {candidates_json}
                        
                        Your Task as a Smart Shopper:
                        1. FILTER OUT JUNK: Ignore phone cases, screen protectors, accessories, or "deposit only" listings if the user asked for the main device (let this be applicable to all meaning fetch only what user wants and nothing else)
                        2. VERIFY MODEL: If user asked for "iPhone 16", DO NOT pick "iPhone 15". If user asked for "Pro", ensure it is "Pro" (let this me corelated to all products and not just Iphone)
                        3. SELECT 4 ITEMS:
                           - EXACTLY 2 from 'shopee'.
                           - EXACTLY 2 from 'lazada'.
                           - Pick the CHEAPEST VALID options (Logic > Price).
                        
                        Output JSON: {{ "selected_ids": [id1, id2, id3, id4] }}
                        """

                        judge_resp = chat_client.models.generate_content(
                            model=MODEL_NAME, 
                            contents=judge_prompt,
                            config={'response_mime_type': 'application/json'}
                        )
                        selection_data = json.loads(judge_resp.text)
                        
                        for idx in selection_data.get("selected_ids", []):
                            if idx < len(candidates):
                                selected_products.append(candidates[idx])
                        
                        print(f"✅ AI Selected {len(selected_products)} logical items.")

                    except Exception as ai_e:
                        print(f"⚠️ AI Judge Failed: {ai_e}")
                        # Fallback: Sort by price, take top 2 valid-looking ones
                        s_items.sort(key=lambda x: x['price'])
                        l_items.sort(key=lambda x: x['price'])
                        selected_products = s_items[:2] + l_items[:2]
                
                else:
                    print("⚠️ No products found to judge.")

                # Process Final Selection
                seen_urls = set()
                for p in selected_products:
                    if p["link"] not in seen_urls and len(products) < 4:
                        seen_urls.add(p["link"])
                        platform_name = p.get("source", "Unknown").title()
                        img_url = p.get("image", "")

                        products.append({
                            "title": p["name"],
                            "price": p["price"],
                            "url": p["link"],
                            "image": img_url,
                            "platform": platform_name
                        })
                        
                        # Save to Memory
                        asyncio.create_task(recommender_service.add_product(
                            title=p["name"],
                            description=f"Scraped from {platform_name} for: {keyword}",
                            price=p["price"],
                            brand=f"{platform_name} Seller",
                            url=p["link"],
                            image_url=img_url,
                            session_id=session_id
                        ))

                if products:
                    try:
                        summary_prompt = f"""
                        User: "{user_msg}"
                        I found these products:
                        {json.dumps(products)}
                        
                        Write a short, helpful response recommending these options.
                        Mention the price difference between Shopee and Lazada.
                        """
                        reply_resp = chat_client.models.generate_content(
                            model=MODEL_NAME, 
                            contents=summary_prompt
                        )
                        ai_reply = reply_resp.text
                    except:
                        ai_reply = f"I found these top deals for '{keyword}' on Shopee and Lazada:"
                else:
                    ai_reply = f"I searched both platforms but couldn't find good matches. Try refining your keyword?"

        else:
            # JUST CHATTING
            try:
                chat_prompt = f"User said: '{user_msg}'. Reply helpfully. Short."
                chat_resp = chat_client.models.generate_content(
                    model=MODEL_NAME, 
                    contents=chat_prompt
                )
                ai_reply = chat_resp.text
            except Exception as e:
                ai_reply = "I'm having trouble connecting to the AI brain right now."

        await user_service.add_message(session_id, "ai", ai_reply, products=products)

        return {
            "reply": ai_reply, 
            "products": products, 
            "session_id": session_id
        }

    except Exception as e:
        print("❌ CRITICAL SERVER ERROR:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))