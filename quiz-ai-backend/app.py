import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set your OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            if page_text := page.extract_text():
                text += page_text
    return text

def generate_questions_with_gpt4(text, quiz_type, difficulty, num_questions, num_options):
    prompt = f"""
You are an AI quiz generator.

Create {num_questions} {quiz_type.lower()} questions from the following content, with each question having {num_options} answer options. 
Make the quiz difficulty: {difficulty}.

Return the output in this JSON format:

[
  {{
    "question": "...",
    "options": ["..."],
    "correctAnswer": "..."
  }},
  ...
]

Content:
\"\"\"
{text[:3000]}
\"\"\"
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    answer = response['choices'][0]['message']['content']

    try:
        start = answer.find("[")
        end = answer.rfind("]") + 1
        return json.loads(answer[start:end])
    except Exception as e:
        return [{"question": "Error parsing GPT response", "options": [], "correctAnswer": str(e)}]

@app.route("/api/generate", methods=["POST"])
def generate_quiz():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if not (file and allowed_file(file.filename)):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    text = extract_text_from_pdf(filepath)

    # Quiz settings
    quiz_type = request.form.get('type', 'Multiple Choice')
    difficulty = request.form.get('difficulty', 'Medium')
    num_questions = int(request.form.get('questions', 5))
    num_options = int(request.form.get('options', 4))

    questions = generate_questions_with_gpt4(text, quiz_type, difficulty, num_questions, num_options)

    return jsonify({"questions": questions})

if __name__ == "__main__":
    app.run(debug=True)

