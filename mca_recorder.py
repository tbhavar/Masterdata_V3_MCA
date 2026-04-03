import time
import json
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def record_session():
    AUTH_FILE = "auth_state.json"
    LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"
    
    with sync_playwright() as p:
        # Launch headed browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        # Apply stealth to mask automation
        Stealth().apply_stealth_sync(page)
        
        print(f"Navigating to {LOGIN_URL}...")
        page.goto(LOGIN_URL)
        
        print("\n" + "="*50)
        print("ACTION REQUIRED:")
        print("1. Please complete the login manually (Username, Password, Captcha, OTP).")
        print("2. Once you are successfully logged in (and reach the dashboard/home page),")
        print("   wait for 5 seconds for the script to capture the session.")
        print("="*50 + "\n")
        
        # Simple detection for successful login (URL change or sign-out presence)
        # We also check for redirections to home.html which might happen if detected.
        
        try:
            # Wait for user to complete login (timeout 5 minutes)
            # We look for something that appears ONLY after login, like "Sign out" or "Welcome"
            # Or just wait for the URL to no longer be the login page.
            while True:
                current_url = page.url
                if "fologin.html" not in current_url and "login.html" not in current_url:
                    # Check if it reached home.html (might be a redirect-back or final landing)
                    # For MCA V3, the dashboard is often /content/mca/global/en/home.html after login too
                    # So we check if there's a sign-out button.
                    if page.query_selector("a:text('Signout')") or page.query_selector("a:text('Log Out')"):
                         print("Login detected! Capturing session state...")
                         break
                
                time.sleep(2)
                
            # Extra wait to ensure cookies are settled
            time.sleep(5)
            
            # Save storage state
            context.storage_state(path=AUTH_FILE)
            print(f"SUCCESS: Session saved to {AUTH_FILE}")
            
        except Exception as e:
            print(f"Error during recording: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    record_session()
