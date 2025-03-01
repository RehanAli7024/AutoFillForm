from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def log_request_info():
    """Log details about each incoming request."""
    logger.info('Headers: %s', dict(request.headers))
    logger.info('Body: %s', request.get_data())

def get_chrome_options():
    """Configure Chrome options for both local and production environments."""
    options = Options()
    options.add_argument('--headless=new')  # Updated headless argument
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    return options

def create_driver():
    """Create and return a Chrome driver instance."""
    options = get_chrome_options()
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Chrome driver created successfully")
        return driver
    except Exception as e:
        logger.error(f"Error creating driver: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def wait_and_find_element(driver, by, value, timeout=10):
    """Wait for an element to be present and return it."""
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))
    except TimeoutException:
        logger.error(f"Timeout waiting for element: {by}={value}")
        raise
    except Exception as e:
        logger.error(f"Error finding element {by}={value}: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def wait_and_find_elements(driver, by, value, timeout=10):
    """Wait for elements to be present and return them."""
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_all_elements_located((by, value)))
    except TimeoutException:
        logger.error(f"Timeout waiting for elements: {by}={value}")
        raise
    except Exception as e:
        logger.error(f"Error finding elements {by}={value}: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def verify_form_submission(driver):
    """Verify form submission using multiple possible confirmation indicators."""
    try:
        # Try different possible confirmation messages
        confirmation_texts = [
            "Your response has been recorded",
            "Thanks for filling",
            "Form submitted",
            "Response submitted",
            "Thank you"
        ]
        
        for text in confirmation_texts:
            try:
                confirmation = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{text}')]"))
                )
                logger.info(f"Found confirmation message: {text}")
                return True
            except:
                continue

        # Check if URL changed to the submission confirmation page
        if "formResponse" in driver.current_url:
            logger.info("Found submission confirmation in URL")
            return True

        # Check if form elements are no longer present
        try:
            driver.find_element(By.CSS_SELECTOR, 'div[role="listitem"]')
            logger.info("Form elements still present - submission might have failed")
            return False
        except NoSuchElementException:
            logger.info("Form elements no longer present - likely submitted successfully")
            return True

        return False
    except Exception as e:
        logger.error(f"Error verifying submission: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_form_fields(url):
    """Extract form fields from a Google Form URL."""
    driver = create_driver()
    
    try:
        logger.info(f"Loading form URL: {url}")
        driver.get(url)
        
        # Wait for questions to load
        questions = wait_and_find_elements(driver, By.CSS_SELECTOR, 'div[role="listitem"]')
        logger.info(f"Found {len(questions)} questions")
        form_fields = []
        
        for index, question in enumerate(questions):
            try:
                # Get question text
                question_text = question.find_element(By.CSS_SELECTOR, 'div[role="heading"] span.M7eMe').text
                logger.info(f"Processing question {index + 1}: {question_text}")
                
                # Determine field type
                field_type = "text"  # default type
                
                # Check for radio buttons
                try:
                    radio_group = question.find_element(By.CSS_SELECTOR, 'div[role="radiogroup"]')
                    field_type = "radio"
                    # Get radio options
                    options = [opt.get_attribute('data-value') for opt in 
                             radio_group.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')]
                    logger.info(f"Radio options: {options}")
                except:
                    # Check for text input
                    try:
                        question.find_element(By.CSS_SELECTOR, 'input[type="text"]')
                        field_type = "text"
                        logger.info("Found text input field")
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
                logger.error(f"Error processing question {index + 1}: {str(e)}")
                logger.error(traceback.format_exc())
                
        return form_fields
    
    finally:
        driver.quit()

def fill_form(url, form_data):
    """Fill and submit a Google Form with provided data."""
    driver = create_driver()
    
    try:
        logger.info(f"Loading form URL: {url}")
        driver.get(url)
        
        # Wait for form to load
        questions = wait_and_find_elements(driver, By.CSS_SELECTOR, 'div[role="listitem"]')
        logger.info(f"Found {len(questions)} questions")
        
        for question in questions:
            try:
                # Wait for question text to be visible
                question_text = wait_and_find_element(question, By.CSS_SELECTOR, 'div[role="heading"] span.M7eMe').text
                logger.info(f"Processing question: {question_text}")
                
                # Find matching answer in form_data
                if question_text in form_data:
                    answer = form_data[question_text]
                    logger.info(f"Filling answer: {answer}")
                    
                    # Handle text input
                    try:
                        input_field = wait_and_find_element(question, By.CSS_SELECTOR, 'input[type="text"]')
                        input_field.clear()
                        input_field.send_keys(answer)
                        # Wait for text to be entered
                        WebDriverWait(driver, 5).until(
                            lambda d: input_field.get_attribute('value') == answer
                        )
                        logger.info("Text input filled successfully")
                        continue
                    except Exception as e:
                        logger.error(f"Error with text input: {str(e)}")
                        logger.error(traceback.format_exc())
                    
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
                        time.sleep(1)
                        radio_button.click()
                        # Wait for radio button to be selected
                        WebDriverWait(driver, 5).until(
                            lambda d: radio_button.get_attribute('aria-checked') == 'true'
                        )
                        logger.info("Radio button selected successfully")
                    except Exception as e:
                        logger.error(f"Error with radio button: {str(e)}")
                        logger.error(traceback.format_exc())
                else:
                    logger.info(f"No answer provided for question: {question_text}")
                        
            except Exception as e:
                logger.error(f"Error filling question: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Find and scroll to submit button
        try:
            # Try different possible submit button selectors
            submit_selectors = [
                '//div[@role="button"]//span[text()="Submit"]',
                '//div[@role="button"]//span[text()="Send"]',
                '//div[@role="button"][contains(@class, "submit")]'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = wait_and_find_element(driver, By.XPATH, selector, timeout=3)
                    logger.info(f"Found submit button with selector: {selector}")
                    break
                except:
                    continue
            
            if not submit_button:
                logger.error("Could not find submit button")
                return False
            
            # Scroll and click
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)
            submit_button.click()
            logger.info("Clicked submit button")
            
            # Verify submission
            time.sleep(2)  # Wait for submission to process
            if verify_form_submission(driver):
                logger.info("Form submission verified")
                return True
            else:
                logger.error("Could not verify form submission")
                return False
            
        except Exception as e:
            logger.error(f"Error during form submission: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
    except Exception as e:
        logger.error(f"Error filling form: {str(e)}")
        logger.error(traceback.format_exc())
        return False
        
    finally:
        driver.quit()

@app.route('/get-fields', methods=['POST'])
def extract_fields():
    """Endpoint to extract fields from a Google Form."""
    try:
        if not request.is_json:
            logger.error("Request does not contain JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        logger.info(f"Received form extraction request: {data}")
        
        if 'url' not in data:
            logger.error("Missing required fields in request")
            return jsonify({'error': 'Missing URL'}), 400
            
        url = data['url']
        try:
            fields = get_form_fields(url)
            return jsonify({'fields': fields})
        except Exception as e:
            logger.error(f"Error extracting form fields: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/submit-form', methods=['POST'])
def submit_form():
    """Endpoint to submit a Google Form."""
    try:
        if not request.is_json:
            logger.error("Request does not contain JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        logger.info(f"Received form submission request: {data}")
        
        if 'url' not in data or 'data' not in data:
            logger.error("Missing required fields in request")
            return jsonify({'error': 'Missing URL or form data'}), 400
            
        url = data['url']
        form_data = data['data']
        
        try:
            success = fill_form(url, form_data)
            if success:
                logger.info("Form submitted successfully")
                return jsonify({'message': 'Form submitted successfully'})
            else:
                logger.error("Form submission verification failed")
                return jsonify({'error': 'Failed to submit form - could not verify submission'}), 500
        except Exception as e:
            logger.error(f"Error during form submission: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
