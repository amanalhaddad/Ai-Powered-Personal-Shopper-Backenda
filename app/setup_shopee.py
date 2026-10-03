import undetected_chromedriver as uc
import time
import os

def login_to_shopee():
    # [CRITICAL] Points to the SAME profile folder your scraper uses
    path = os.path.join(os.getcwd(), "shopee_profile")
    
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={path}") 
    
    print(f"📂 Loading Profile at: {path}")
    print("🚀 Opening Browser... Please Log In manually!")

    # Open Browser
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=143)
    
    # Go to Login Page
    driver.get("https://shopee.com.my/buyer/login")

    print("-------------------------------------------------")
    print("👉 ACTION REQUIRED: Log in to Shopee.")
    print("👉 Solve any puzzles/sliders.")
    print("👉 Once you are on the HOMEPAGE, close this window.")
    print("-------------------------------------------------")
    
    # Keep script running until you close the browser
    try:
        while True:
            time.sleep(1)
            if not driver.service.process.poll() is None: 
                break
    except KeyboardInterrupt:
        driver.quit()

if __name__ == "__main__":
    login_to_shopee()