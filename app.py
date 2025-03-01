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

def get_form_fields(url):
    """Extract form fields from a Google Form URL."""
    driver = create_driver()
    
    try:
        driver.get(url)
        time.sleep(3)  # Initial wait for form to load
        
        # Find all form questions
        questions = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
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
        time.sleep(3)  # Initial wait for form to load
        
        # Process each form field
        questions = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
        
        for question in questions:
            try:
                question_text = question.find_element(By.CSS_SELECTOR, 'div[role="heading"] span.M7eMe').text
                
                # Find matching answer in form_data
                if question_text in form_data:
                    answer = form_data[question_text]
                    
                    # Handle text input
                    try:
                        input_field = question.find_element(By.CSS_SELECTOR, 'input[type="text"]')
                        input_field.send_keys(answer)
                        continue
                    except:
                        pass
                    
                    # Handle radio buttons
                    try:
                        radio_group = question.find_element(By.CSS_SELECTOR, 'div[role="radiogroup"]')
                        radio_button = radio_group.find_element(
                            By.CSS_SELECTOR, 
                            f'div[role="radio"][data-value="{answer}"]'
                        )
                        radio_button.click()
                    except:
                        pass
                        
            except Exception as e:
                print(f"Error filling question: {str(e)}")
        
        # Submit form
        submit_button = driver.find_element(
            By.XPATH, 
            '//div[@role="button"]//span[text()="Submit"]'
        )
        submit_button.click()
        time.sleep(2)  # Wait for submission
        
        return True
        
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
            return jsonify({'error': 'Failed to submit form'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
