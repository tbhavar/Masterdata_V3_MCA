from playwright.sync_api import sync_playwright
import json
import time

def connect_to_chrome():
    AUTH_FILE = "auth_state.json"
    with sync_playwright() as p:
        try:
            # Connect to the existing chrome instance
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("Successfully connected to your Chrome browser!")
            
            # Access the already open page or create a new one
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            print("Waiting for you to log in to MCA...")
            print("Once you are on the MCA Dashboard, please wait 5 seconds...")
            
            # Extract state
            time.sleep(10) # Give user time to ensure they are on the right page
            state = context.storage_state()
            with open(AUTH_FILE, "w") as f:
                f.write(json.dumps(state, indent=2))
            
            print(f"SUCCESS! Session saved to {AUTH_FILE}")
            print("You can now close the debug Chrome window.")
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            print("Ensure you started Chrome with --remote-debugging-port=9222")

if __name__ == "__main__":
    connect_to_chrome()
