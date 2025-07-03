from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def inspect_page():
    print("Launching Firefox to inspect the page...")
    
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.binary_location = "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox"
    
    try:
        # Initialize Firefox WebDriver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Navigate to the bbctrl controller
        url = "http://bbctrl.local/#control"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        print("\n=== Page Title ===")
        print(driver.title)
        
        print("\n=== All Links ===")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links[:10]:  # Show first 10 links
            print(f"- {link.text} -> {link.get_attribute('href')}")
        
        print("\n=== All Buttons ===")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons[:10]:  # Show first 10 buttons
            print(f"- Button: {button.text} (ID: {button.get_attribute('id')}, Class: {button.get_attribute('class')})")
        
        print("\n=== All Input Fields ===")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for input_field in inputs[:10]:  # Show first 10 inputs
            print(f"- Input: {input_field.get_attribute('name') or input_field.get_attribute('id')} "
                  f"(Type: {input_field.get_attribute('type')}, Value: {input_field.get_attribute('value')})")
        
        print("\n=== Modal Dialogs ===")
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal, [role='dialog']")
        print(f"Found {len(modals)} modal dialogs")
        for i, modal in enumerate(modals, 1):
            print(f"\nModal {i}:")
            print(f"- ID: {modal.get_attribute('id')}")
            print(f"- Class: {modal.get_attribute('class')}")
            print(f"- Visible: {modal.is_displayed()}")
            print(f"- Text: {modal.text[:200]}...")
        
        print("\n=== JavaScript Console Logs ===")
        logs = driver.get_log('browser')
        for log in logs[-5:]:  # Show last 5 log entries
            print(f"- {log['level']}: {log['message']}")
        
        # Keep the browser open for inspection
        print("\nBrowser will remain open for manual inspection. Close it when done.")
        input("Press Enter to close the browser...")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'driver' in locals():
            driver.save_screenshot("page_inspect_error.png")
            print("Screenshot saved as page_inspect_error.png")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    inspect_page()
