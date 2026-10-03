# setup_lazada.py
import undetected_chromedriver as uc
import time
import os

def login_to_lazada():
    # This creates a folder named 'lazada_profile' in your project
    path = os.path.join(os.getcwd(), "lazada_profile")
    
    # This tells Chrome to save all your login data here
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={path}") 
    
    print(f"📂 Creating/Loading Profile at: {path}")
    print("🚀 Opening Browser... Please Log In manually!")

    driver = uc.Chrome(options=options, use_subprocess=True, version_main=143)
    
    # Go to login page
    driver.get("https://member.lazada.com.my/user/login")

    print("-------------------------------------------------")
    print("👉 ACTION REQUIRED: Log in to Lazada in the browser.")
    print("👉 Once you are logged in and see the Homepage, CLOSE this window.")
    print("-------------------------------------------------")
    
    # Keeps script running so you have time to login
    try:
        while True:
            time.sleep(1)
            if not driver.service.process.poll() is None: # Check if browser is closed
                break
    except KeyboardInterrupt:
        driver.quit()

if __name__ == "__main__":
    login_to_lazada()