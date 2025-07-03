#!/usr/bin/env python3
"""
G-code Stepper for OneFinity Controller

This script reads a G-code file and sends commands one at a time to the OneFinity controller
via its web interface, waiting for user confirmation before sending each command.
"""

import os
import sys
import time
import webbrowser
import requests
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class GCodeStepper:
    def __init__(self, gcode_file=None):
        self.gcode_file = os.path.abspath(gcode_file) if gcode_file else None
        self.base_url = "http://bbctrl.local"
        self.control_url = f"{self.base_url}/#control"
        self.driver = None
        self.commands = []
        self.current_line = 0
        
    def load_gcode(self, gcode_file=None):
        """Load and parse the G-code file, removing comments and empty lines."""
        if gcode_file:
            self.gcode_file = os.path.abspath(gcode_file)
            
        if not self.gcode_file:
            print("Error: No G-code file specified")
            return False
            
        if not os.path.exists(self.gcode_file):
            print(f"Error: File not found: {self.gcode_file}")
            return False
            
        print(f"Loading G-code from: {self.gcode_file}")
        try:
            with open(self.gcode_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
        
        # Filter out comments and empty lines
        for line in lines:
            line = line.strip()
            # Remove inline comments (everything after ';' or '()')
            if ';' in line:
                line = line.split(';', 1)[0].strip()
            if line and not line.startswith('(') and not line.startswith(';'):
                self.commands.append(line)
        
        print(f"Loaded {len(self.commands)} G-code commands from {self.gcode_file}")
        return True
    
    def check_for_errors(self):
        """Check for and handle any error dialogs."""
        try:
            # First try to find and close any error dialogs with more specific selectors
            selectors = [
                ".modal-dialog .btn-primary",  # Standard error dialog
                ".btn-close",                 # Close button (X)
                "button:contains('OK')",       # OK button
                "button:contains('Close')",    # Close button
                ".modal-footer button"         # Any button in modal footer
            ]
            
            for selector in selectors:
                try:
                    # Use JavaScript to find and click the element if present
                    script = f"""
                    var element = document.querySelector('{selector}');
                    if (element && window.getComputedStyle(element).display !== 'none') {{
                        element.click();
                        return true;
                    }}
                    return false;
                    """
                    result = self.driver.execute_script(script)
                    if result:
                        print(f"Closed dialog using selector: {selector}")
                        time.sleep(0.5)  # Give it a moment to close
                except Exception as e:
                    print(f"Tried selector {selector}: {str(e)[:100]}...")
                    continue
            
            # Also try to find and log any error messages
            try:
                error_msgs = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error-message, .modal-body")
                for msg in error_msgs:
                    if msg.is_displayed():
                        print(f"Error message found: {msg.text[:200]}...")
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"Error in check_for_errors: {str(e)[:200]}...")
            return False
            
    def wait_for_element(self, by, value, timeout=10, retries=3):
        """Wait for an element with retries."""
        for attempt in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                if element.is_displayed() and element.is_enabled():
                    return element
            except:
                if attempt == retries - 1:  # Last attempt
                    raise
                print(f"Retrying to find element: {value}...")
                time.sleep(1)
        return None

    def setup_webdriver(self):
        """Initialize the Selenium WebDriver with Firefox."""
        print("Setting up Firefox WebDriver...")
        
        # Set up Firefox options with minimal configuration
        firefox_options = Options()
        
        # Set basic preferences
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        firefox_options.set_preference("dom.webnotifications.enabled", False)
        firefox_options.set_preference("app.update.auto", False)
        firefox_options.set_preference("app.update.enabled", False)
        
        # Set window size
        firefox_options.add_argument("--width=1280")
        firefox_options.add_argument("--height=1024")
        
        try:
            # Let webdriver_manager handle the geckodriver
            service = FirefoxService()
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            
            # Set a reasonable page load timeout
            self.driver.set_page_load_timeout(30)
            
            print(f"Navigating to: {self.control_url}")
            self.driver.get(self.control_url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            time.sleep(5)  # Give it time to load
            
            # Take a screenshot for debugging
            self.driver.save_screenshot("page_loaded.png")
            print("Initial page screenshot saved as page_loaded.png")
            
            # Save page source for debugging
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("Page source saved to page_source.html")
            
            # List all available tabs for debugging
            print("\nAvailable tabs:")
            try:
                tabs = self.driver.find_elements(By.CSS_SELECTOR, ".nav-tabs li a, .tab-pane, [role=tab]")
                for i, tab in enumerate(tabs, 1):
                    print(f"{i}. Text: {tab.text.strip() if tab.text else 'No text'}, "
                          f"ID: {tab.get_attribute('id')}, "
                          f"Classes: {tab.get_attribute('class')}")
            except Exception as e:
                print(f"Error listing tabs: {str(e)[:200]}")
            
            # Check if we need to log in
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                if login_button.is_displayed():
                    print("Login form detected. Please log in manually and press Enter to continue...")
                    input()
                    # Wait for login to complete
                    time.sleep(2)
            except:
                pass  # No login form found
            
            # Try multiple ways to find the MDI tab
            print("\nLooking for MDI tab...")
            mdi_found = False
            
            # Try different selectors for the MDI tab
            selectors = [
                (By.ID, "tab2"),
                (By.CSS_SELECTOR, "[href='#mdi']"),
                (By.CSS_SELECTOR, "a[data-toggle='tab'][href*='mdi']"),
                (By.XPATH, "//a[contains(translate(., 'MDI', 'mdi'), 'mdi')]"),
                (By.XPATH, "//*[contains(translate(., 'MANUAL', 'manual'), 'manual')]"),
                (By.XPATH, "//*[contains(translate(., 'COMMAND', 'command'), 'command')]")
            ]
            
            for by, selector in selectors:
                try:
                    print(f"Trying selector: {by} = {selector}")
                    mdi_tab = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    print(f"Found MDI tab with {by} = {selector}")
                    mdi_tab.click()
                    time.sleep(1)  # Wait for tab to switch
                    mdi_found = True
                    print("MDI tab found and clicked successfully!")
                    break
                except Exception as e:
                    print(f"  - Not found with {by} = {selector}")
            
            if not mdi_found:
                print("Could not find/click MDI tab")
                # Take a screenshot to help with debugging
                self.driver.save_screenshot("mdi_tab_error.png")
                return False
            
            # Look for the G-code viewer textarea
            print("\nLooking for G-code viewer textarea...")
            try:
                # Wait for the textarea to be present and visible
                gcode_viewer = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "gcode-view"))
                )
                print("Found G-code viewer textarea")
                
                # Check if it's visible and enabled
                if gcode_viewer.is_displayed() and gcode_viewer.is_enabled():
                    print("G-code viewer is visible and enabled")
                    self.mdi_input = gcode_viewer
                    
                    # Try to send a test command
                    try:
                        print("Sending test command to verify MDI input...")
                        gcode_viewer.clear()
                        gcode_viewer.send_keys("; Test command")
                        time.sleep(1)  # Wait for any UI updates
                        
                        # Take a screenshot after sending the test command
                        self.driver.save_screenshot("mdi_test_command.png")
                        print("Test command sent. Check mdi_test_command.png to verify.")
                        
                        # Clear the test command
                        gcode_viewer.clear()
                        return True
                        
                    except Exception as e:
                        print(f"Error sending test command: {e}")
                        return False
                else:
                    print("G-code viewer is not visible or enabled")
                    return False
                    
            except Exception as e:
                print(f"Could not find or interact with G-code viewer: {e}")
                
                # List all textareas for debugging
                print("\nAvailable textareas:")
                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                for i, textarea in enumerate(textareas):
                    print(f"  {i+1}. Class: {textarea.get_attribute('class')}")
                    print(f"     ID: {textarea.get_attribute('id')}")
                    print(f"     Visible: {textarea.is_displayed()}")
                    print(f"     Enabled: {textarea.is_enabled()}")
                
                # Take a screenshot for debugging
                self.driver.save_screenshot("mdi_not_found.png")
                print("\nScreenshot saved as mdi_not_found.png")
                
                return False
            
        except Exception as e:
            print(f"Error initializing Firefox WebDriver: {e}")
            print("Please make sure Firefox is installed on your system.")
            print("You can install it with: brew install --cask firefox")
            return False
    
    def send_gcode(self, command):
        """Send a single G-code command to the controller."""
        try:
            mdi_input = self.driver.find_element(By.ID, "mdi-command")
            mdi_input.clear()
            mdi_input.send_keys(command)
            mdi_input.submit()
            print(f"Sent: {command}")
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def run(self, gcode_file=None):
        """Main loop to step through G-code commands."""
        if not self.load_gcode(gcode_file):
            return
        
        if not self.setup_webdriver():
            return
        
        print("\n--- G-code Stepper ---")
        print("Press Enter to send the next command")
        print("Type 'q' and press Enter to quit\n")
        
        while self.current_line < len(self.commands):
            cmd = self.commands[self.current_line]
            print(f"\n[{self.current_line + 1}/{len(self.commands)}] Next command: {cmd}")
            
            user_input = input("Send this command? [Y/n/q]: ").strip().lower()
            
            if user_input == 'q':
                print("\nQuitting...")
                break
            elif user_input in ('', 'y', 'yes'):
                if self.send_gcode(cmd):
                    self.current_line += 1
            else:
                print("Skipping command")
                self.current_line += 1
        
        print("\nFinished stepping through G-code commands.")
        print("You can close the browser window when done.")

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'driver') and self.driver:
            try:
                # Close the browser window but keep the session
                self.driver.minimize_window()
                print("\nBrowser window minimized. You can close it when done.")
                print("Note: The browser will close automatically when you exit this script.")
            except:
                # If minimize fails, just continue
                pass

def main():
    # Check if a file was provided as a command-line argument
    gcode_file = None
    if len(sys.argv) > 1:
        gcode_file = sys.argv[1]
    
    # If no file provided, prompt the user
    while not gcode_file:
        gcode_file = input("Enter the path to your G-code file: ").strip()
        if not gcode_file:
            print("No file specified. Please try again or press Ctrl+C to exit.")
    
    stepper = GCodeStepper()
    try:
        stepper.run(gcode_file)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stepper.cleanup()

if __name__ == "__main__":
    main()
