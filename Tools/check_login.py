from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def check_login():
    print("Checking for login form...")
    
    # Set up Firefox options
    firefox_options = Options()
    firefox_options.binary_location = "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox"
    
    try:
        # Initialize Firefox WebDriver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Navigate to the OneFinity controller
        url = "http://bbctrl.local/#control"
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Check for login form
        try:
            login_form = driver.find_element(By.TAG_NAME, "form")
            print("\n=== Login Form Found ===")
            print(f"Form action: {login_form.get_attribute('action')}")
            print(f"Form method: {login_form.get_attribute('method')}")
            
            # Find all input fields in the form
            inputs = login_form.find_elements(By.TAG_NAME, "input")
            print("\n=== Form Inputs ===")
            for input_field in inputs:
                print(f"- Name: {input_field.get_attribute('name')}")
                print(f"  Type: {input_field.get_attribute('type')}")
                print(f"  Value: {input_field.get_attribute('value')}")
                print(f"  Required: {input_field.get_attribute('required')}")
                
        except Exception as e:
            print("\nNo login form found on the page")
        
        # Take a screenshot
        driver.save_screenshot("login_page.png")
        print("\nScreenshot saved as login_page.png")
        
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
    check_login()
