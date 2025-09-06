from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time

def explore_page():
    print("Launching browser to explore page structure...")
    
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.binary_location = "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox"
    firefox_options.add_argument("--width=1280")
    firefox_options.add_argument("--height=1024")
    
    try:
        # Initialize Firefox WebDriver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Navigate to the bbctrl controller
        url = "http://bbctrl.local/#control"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(5)  # Give it time to fully load
        
        # Take a screenshot
        driver.save_screenshot("explore_page.png")
        print("Screenshot saved as explore_page.png")
        
        # Get all elements with IDs
        print("\n=== Elements with IDs ===")
        elements_with_ids = driver.find_elements(By.XPATH, "//*[@id]")
        for elem in elements_with_ids[:50]:  # Show first 50 elements with IDs
            print(f"- {elem.tag_name}: id='{elem.get_attribute('id')}'")
        
        # Get all buttons and clickable elements
        print("\n=== Buttons and Clickable Elements ===")
        clickables = driver.find_elements(By.CSS_SELECTOR, "button, [role='button'], [onclick], [href]")
        for i, elem in enumerate(clickables[:50]):  # Limit to first 50
            print(f"{i+1}. {elem.tag_name}")
            print(f"   Text: {elem.text}")
            print(f"   ID: {elem.get_attribute('id')}")
            print(f"   Class: {elem.get_attribute('class')}")
            if elem.get_attribute('onclick'):
                print(f"   OnClick: {elem.get_attribute('onclick')}")
        
        # Get all input elements and textareas
        print("\n=== Input Fields and Textareas ===")
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
        for i, elem in enumerate(inputs):
            print(f"{i+1}. {elem.tag_name}")
            print(f"   Type: {elem.get_attribute('type')}")
            print(f"   ID: {elem.get_attribute('id')}")
            print(f"   Name: {elem.get_attribute('name')}")
            print(f"   Class: {elem.get_attribute('class')}")
            print(f"   Placeholder: {elem.get_attribute('placeholder')}")
            print(f"   Value: {elem.get_attribute('value')}")
        
        # Look for any MDI-related elements
        print("\n=== MDI Related Elements ===")
        mdi_elements = driver.find_elements(By.XPATH, "//*[contains(translate(., 'MDI', 'mdi'), 'mdi')]")
        for elem in mdi_elements[:20]:  # Limit to first 20 matches
            print(f"- {elem.tag_name}: {elem.text[:100]}...")
        
        # Look for any G-code related elements
        print("\n=== G-code Related Elements ===")
        gcode_elements = driver.find_elements(By.XPATH, "//*[contains(translate(., 'gcode', 'GCODE'), 'gcode') or contains(., 'G0') or contains(., 'G1')]")
        for elem in gcode_elements[:20]:  # Limit to first 20 matches
            print(f"- {elem.tag_name}: {elem.text[:100]}...")
        
        # Print the page source to a file
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\nPage source saved as page_source.html")
        
        # Keep the browser open for inspection
        print("\nBrowser will remain open for manual inspection. Close it when done.")
        input("Press Enter to close the browser...")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'driver' in locals():
            driver.save_screenshot("explore_error.png")
            print("Screenshot saved as explore_error.png")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    explore_page()
