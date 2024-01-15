from flask import Flask, request, render_template
import cv2
import numpy as np
import pytesseract
from PIL import Image
import pandas as pd
from fuzzywuzzy import process

app = Flask(__name__)

# Function to read ingredients from Excel files
def read_ingredients_from_excel(file_name):
    return pd.read_excel(file_name, header=None)[0].tolist()

def fuzzy_match_ingredient(ingredient, ingredient_list):
    """Find the closest match for an ingredient in a given list."""
    highest = process.extractOne(ingredient, ingredient_list)
    if highest and highest[1] > 60:  # Assuming a threshold of 60% similarity
        return highest[0]
    return ingredient  # Fallback to the original ingredient if no match found

def clean_percentage(perc_string):
    """Clean the percentage string and convert it to a float."""
    # Remove unwanted characters
    perc_string = perc_string.strip('()% ')
    # Handle empty strings or other non-numeric issues
    try:
        return float(perc_string)
    except ValueError:
        return 0.0  # Return 0.0 if conversion is not possible

# Function to process the uploaded image
def process_uploaded_image(image_path):
    # Read healthy and unhealthy ingredients from Excel
    healthy_ingredients = read_ingredients_from_excel(r'C:\Users\vedan\OneDrive\Desktop\Projects\OCR\healthy.xlsx')
    unhealthy_ingredients = read_ingredients_from_excel(r'C:\Users\vedan\OneDrive\Desktop\Projects\OCR\unhealthy.xlsx')

    def get_string(img_path):
        # Your existing image processing code...
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.dilate(img, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)
        cv2.imwrite("removed_noise.png", img)
        img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        cv2.imwrite(img_path, img)
        result = pytesseract.image_to_string(Image.open(img_path))
        return result

    data = get_string(image_path).strip()

    # Assuming the entire OCR result is the ingredient list
    ingredient_lines = data.split(',')

    healthy_score = 0
    unhealthy_score = 0
    remaining_percentage = 100.0

    for ingredient_line in ingredient_lines:
        parts = ingredient_line.strip().split()
        if len(parts) >= 2:
            percentage_str = parts[-1]
            percentage = clean_percentage(percentage_str)
            ingredient = ' '.join(parts[:-1])
        else:
            percentage = 0.0  # If percentage is not specified, default to 0
            ingredient = ' '.join(parts)

        matched_ingredient = fuzzy_match_ingredient(ingredient, healthy_ingredients + unhealthy_ingredients)

        # Calculate the score and update the remaining percentage
        if matched_ingredient in healthy_ingredients:
            healthy_score += percentage
        elif matched_ingredient in unhealthy_ingredients:
            unhealthy_score -= percentage

        remaining_percentage -= percentage

    # If there's remaining percentage, distribute it equally among ingredients without specified percentages
    if remaining_percentage > 0:
        unknown_percentage = remaining_percentage / len(ingredient_lines)
        healthy_score += unknown_percentage * len(healthy_ingredients)
        unhealthy_score -= unknown_percentage * len(unhealthy_ingredients)

    overall_score = healthy_score + unhealthy_score
    return overall_score

@app.route('/', methods=['GET'])
def landing():
  
    name = request.args.get('name')
    # Do something with the 'name' variable if needed
    if name:
        return render_template('result.html', name=name)
    return render_template('landing.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    name = request.args.get('name', '')  # Retrieve the name from the GET parameters
    if request.method == 'POST':
        if 'image' in request.files:
            image = request.files['image']
            if image:
                image_path = "uploaded_image.png"
                image.save(image_path)
                result = process_uploaded_image(image_path)
                # Pass the 'name' variable along with the 'result' to the template
                return render_template('result.html', result=result, name=name)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)