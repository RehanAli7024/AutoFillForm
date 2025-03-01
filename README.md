# Google Form Automation API

This Flask application provides a REST API to automate Google Form interactions using undetected-chromedriver.

## Features

- Extract form fields and their types from a Google Form URL
- Automatically fill and submit forms with provided data
- Support for text inputs and radio button fields
- Headless browser operation

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

## API Endpoints

### 1. Get Form Fields
- **Endpoint**: `/get-fields`
- **Method**: POST
- **Body**:
```json
{
    "url": "your-google-form-url"
}
```

### 2. Submit Form
- **Endpoint**: `/submit-form`
- **Method**: POST
- **Body**:
```json
{
    "url": "your-google-form-url",
    "data": {
        "Question 1": "answer1",
        "Question 2": "yes"
    }
}
```

## Example Usage

```python
import requests

# Get form fields
response = requests.post('http://localhost:5000/get-fields', 
    json={'url': 'your-form-url'})
print(response.json())

# Submit form
form_data = {
    'url': 'your-form-url',
    'data': {
        'Name': 'John Doe',
        'Do you like ice cream?': 'yes'
    }
}
response = requests.post('http://localhost:5000/submit-form', 
    json=form_data)
print(response.json())
