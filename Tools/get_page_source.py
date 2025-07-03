from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time

def get_page_source():
    print("Getting page source...")
    
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.binary_location = "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox"
    
    try:
        # Initialize Firefox WebDriver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Navigate to the OneFinity controller
        url = "http://bbctrl.local"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait a moment for any JavaScript to run
        time.sleep(3)
        
        # Get the page source
        source = driver.page_source
        
        # Save the page source to a file
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(source)
        
        print("\nPage source saved as page_source.html")
        print("\nPage title:", driver.title)
        print("Current URL:", driver.current_url)
        
        # Take a screenshot
        driver.save_screenshot("page_screenshot.png")
        print("Screenshot saved as page_screenshot.png")
        
        # Print some basic info
        print("\n=== Page Info ===")
        print(f"Title: {driver.title}")
        print(f"URL: {driver.current_url}")
        print(f"Source length: {len(source)} characters")
        
        # Find all links on the page
        print("\n=== Links ===")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links[:10]:  # Show first 10 links
            print(f"- {link.text} -> {link.get_attribute('href')}")
        
        # Find all forms on the page
        print("\n=== Forms ===")
        forms = driver.find_elements(By.TAG_NAME, "form")
        for i, form in enumerate(forms, 1):
            print(f"\nForm {i}:")
            print(f"Action: {form.get_attribute('action')}")
            print(f"Method: {form.get_attribute('method')}")
            inputs = form.find_elements(By.TAG_NAME, "input")
            for input_field in inputs:
                print(f"  Input: name='{input_field.get_attribute('name')}' type='{input_field.get_attribute('type')}'")
        
        # Keep the browser open for inspection
        print("\nBrowser will remain open for manual inspection. Close it when done.")
        input("Press Enter to close the browser...")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'driver' in locals():
            driver.save_screenshot("error.png")
            print("Screenshot saved as error.png")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    get_page_source()
