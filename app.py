from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

app = Flask(__name__)

def get_chrome_options():
    """Configure Chrome options for both local and production environments."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')  # Set a proper window size
    return options

def create_driver():
    """Create and return a Chrome driver instance."""
    options = get_chrome_options()
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error creating driver: {str(e)}")
        raise

def wait_and_find_element(driver, by, value, timeout=10):
    """Wait for an element to be present and return it."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located((by, value)))

def wait_and_find_elements(driver, by, value, timeout=10):
    """Wait for elements to be present and return them."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_all_elements_located((by, value)))

def get_form_fields(url):
    """Extract form fields from a Google Form URL."""
    driver = create_driver()
    
    try:
        driver.get(url)
        
        # Wait for questions to load
        questions = wait_and_find_elements(driver, By.CSS_SELECTOR, 'div[role="listitem"]')
        form_fields = []
        
        for index, question in enumerate(questions):
            try:
                # Get question text
                question_text = question.find_element(By.CSS_SELECTOR, 'div[role="heading"] span.M7eMe').text
                
                # Determine field type
                field_type = "text"  # default type
                
                # Check for radio buttons
                try:
                    radio_group = question.find_element(By.CSS_SELECTOR, 'div[role="radiogroup"]')
                    field_type = "radio"
                    # Get radio options
                    options = [opt.get_attribute('data-value') for opt in 
                             radio_group.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')]
                except:
                    # Check for text input
                    try:
                        question.find_element(By.CSS_SELECTOR, 'input[type="text"]')
                        field_type = "text"
                    except:
                        pass
                
                field_info = {
                    "question": question_text,
                    "type": field_type
                }
                
                if field_type == "radio":
                    field_info["options"] = options
                    
                form_fields.append(field_info)
                
            except Exception as e:
                print(f"Error processing question {index + 1}: {str(e)}")
                
        return form_fields
    
    finally:
        driver.quit()

def fill_form(url, form_data):
    """Fill and submit a Google Form with provided data."""
    driver = create_driver()
    
    try:
        driver.get(url)
        
        # Wait for form to load
        questions = wait_and_find_elements(driver, By.CSS_SELECTOR, 'div[role="listitem"]')
        
        for question in questions:
            try:
                # Wait for question text to be visible
                question_text = wait_and_find_element(question, By.CSS_SELECTOR, 'div[role="heading"] span.M7eMe').text
                
                # Find matching answer in form_data
                if question_text in form_data:
                    answer = form_data[question_text]
                    
                    # Handle text input
                    try:
                        input_field = wait_and_find_element(question, By.CSS_SELECTOR, 'input[type="text"]')
                        input_field.clear()  # Clear any existing text
                        input_field.send_keys(answer)
                        # Wait for text to be entered
                        WebDriverWait(driver, 5).until(
                            lambda d: input_field.get_attribute('value') == answer
                        )
                        continue
                    except:
                        pass
                    
                    # Handle radio buttons
                    try:
                        radio_group = wait_and_find_element(question, By.CSS_SELECTOR, 'div[role="radiogroup"]')
                        radio_button = wait_and_find_element(
                            radio_group,
                            By.CSS_SELECTOR, 
                            f'div[role="radio"][data-value="{answer}"]'
                        )
                        # Scroll the radio button into view
                        driver.execute_script("arguments[0].scrollIntoView(true);", radio_button)
                        time.sleep(1)  # Small pause for stability
                        radio_button.click()
                        # Wait for radio button to be selected
                        WebDriverWait(driver, 5).until(
                            lambda d: radio_button.get_attribute('aria-checked') == 'true'
                        )
                    except Exception as e:
                        print(f"Error with radio button: {str(e)}")
                        
            except Exception as e:
                print(f"Error filling question: {str(e)}")
        
        # Find and scroll to submit button
        submit_button = wait_and_find_element(
            driver,
            By.XPATH, 
            '//div[@role="button"]//span[text()="Submit"]'
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(1)  # Small pause for stability
        
        # Click submit
        submit_button.click()
        
        # Wait for submission confirmation
        try:
            confirmation = wait_and_find_element(
                driver,
                By.XPATH,
                '//*[contains(text(), "Your response has been recorded")]',
                timeout=10
            )
            return True
        except:
            print("Could not find submission confirmation")
            return False
        
    except Exception as e:
        print(f"Error submitting form: {str(e)}")
        return False
        
    finally:
        driver.quit()

@app.route('/get-fields', methods=['POST'])
def extract_fields():
    """Endpoint to extract fields from a Google Form."""
    if not request.json or 'url' not in request.json:
        return jsonify({'error': 'No URL provided'}), 400
        
    url = request.json['url']
    try:
        fields = get_form_fields(url)
        return jsonify({'fields': fields})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit-form', methods=['POST'])
def submit_form():
    """Endpoint to submit a Google Form."""
    if not request.json or 'url' not in request.json or 'data' not in request.json:
        return jsonify({'error': 'Missing URL or form data'}), 400
        
    url = request.json['url']
    form_data = request.json['data']
    
    try:
        success = fill_form(url, form_data)
        if success:
            return jsonify({'message': 'Form submitted successfully'})
        else:
            return jsonify({'error': 'Failed to submit form - could not verify submission'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
