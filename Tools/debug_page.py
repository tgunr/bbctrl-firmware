#!/usr/bin/env python3
"""
Debug script for bbctrl web interface
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_page_info(driver, filename):    
    # Save page source
    with open(f"{filename}.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    
    # Save screenshot
    driver.save_screenshot(f"{filename}.png")
    
    # Save all elements
    with open(f"{filename}_elements.txt", "w") as f:
        # Get all elements
        elements = driver.find_elements(By.XPATH, "//*")
        f.write(f"Found {len(elements)} elements in total\n\n")
        
        # Write element details
        for i, elem in enumerate(elements[:100]):  # Limit to first 100 elements
            try:
                tag = elem.tag_name
                elem_id = elem.get_attribute('id') or ''
                classes = elem.get_attribute('class') or ''
                text = elem.text.strip() if elem.text else ''
                
                f.write(f"{i+1}. <{tag}")
                if elem_id:
                    f.write(f" id='{elem_id}'")
                if classes:
                    f.write(f" class='{classes}'")
                f.write(">")
                if text:
                    f.write(f"\n   Text: {text[:100]}")
                f.write("\n\n")
            except Exception as e:
                f.write(f"Error getting element {i+1}: {str(e)}\n\n")

def main():
    print("Starting debug session...")
    
    # Set up Firefox options
    options = webdriver.FirefoxOptions()
    options.add_argument("--start-maximized")
    
    try:
        # Initialize WebDriver
        print("Initializing Firefox WebDriver...")
        driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
        
        # Navigate to bbctrl controller
        url = "http://bbctrl.local"
        print(f"Navigating to {url}...")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(5)
        
        # Save initial page info
        print("Saving initial page info...")
        save_page_info(driver, "initial_page")
        
        # Check for login form
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            if login_button.is_displayed():
                print("\n=== LOGIN DETECTED ===")
                print("Please log in manually and press Enter to continue...")
                input()
                time.sleep(2)
                save_page_info(driver, "after_login")
        except:
            pass
        
        # Save final page info
        print("\nSaving final page info...")
        save_page_info(driver, "final_page")
        
        print("\nDebug files saved to:")
        print(f"- initial_page.html/png/txt")
        print(f"- final_page.html/png/txt")
        
        print("\nDebug session complete. The browser will remain open for inspection.")
        print("Close the browser window when done.")
        
        # Keep browser open
        input("Press Enter to close the browser...")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
