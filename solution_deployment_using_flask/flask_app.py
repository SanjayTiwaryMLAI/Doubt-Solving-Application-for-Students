from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF library for handling PDFs
from collections import deque
import boto3
import json
import base64
import io
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import os

app = Flask(__name__)
CORS(app)

class DoubtSolver:
    def __init__(self, pdf_file, context_size=5):
        self.pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        self.current_page = 0
        self.context_size = context_size
        self.context = deque(maxlen=context_size)
        self.all_slides_content = self.extract_all_slides_content()

        # Initialize AWS Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1')  # Change this to your preferred region

        # Initialize AWS Polly client
        self.polly = boto3.client('polly', region_name='us-east-1')  # Change this to your preferred region

        # Update context with initial pages
        for _ in range(min(context_size, len(self.pdf_document))):
            self.update_context()

    def update_context(self):
        page_content = self.pdf_document[self.current_page].get_text()
        self.context.append((self.current_page, page_content))
    
    def extract_all_slides_content(self):
        all_content = []
        for page_num in range(len(self.pdf_document)):
            content = self.pdf_document[page_num].get_text()
            all_content.append((page_num, content))
        return all_content

    def get_current_page_content(self):
        return self.pdf_document[self.current_page].get_text()

    def get_current_page_image(self):
        page = self.pdf_document[self.current_page]
        pix = page.get_pixmap()
        img = pix.tobytes("png")
        return img


    def answer_question(self, question):
        current_context = "\n\n".join([f"Page {page+1}:\n{content}" for page, content in self.context])
        all_slides = self.all_slides_content
    
        message_content = f"""Current context (recent slides):\n\n{current_context}
    
        Question: {question}
    
        Please answer the question based primarily on the current context provided above. If the answer is not fully contained in the current context, you may refer to the content of all slides to check if the topic will be covered in upcoming slides. 
    
        Guidelines for answering:
        1. If the answer is in the current context, provide it directly.
        2. If the answer is not in the current context but will be covered in a future slide, mention this fact and provide the future slide number. Do not give details from the future slide.
        3. If the answer is not in any slide, state that the topic is not covered in the presentation.
        4. Keep your answer within 150 words.
    
        Full content of all slides (for reference only, do not disclose future content details):
        {json.dumps(all_slides)}
        """
    
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message_content
                        }
                    ]
                }
            ]
        }
    
        response = self.bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0', 
            body=json.dumps(request_body)
        )
    
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']

    # def explain_concept(self):
    #     current_page_content = self.pdf_document[self.current_page].get_text()
    #     message_content = f"""Context from the PDF:\n\n Page {self.current_page + 1}:\n{current_page_content}\n\n 
    #     please explain the slide to student, as an teacher very crisp in less than 150 words"""

    #     request_body = {
    #         "anthropic_version": "bedrock-2023-05-31",
    #         "max_tokens": 1000,
    #         "temperature": 0,
    #         "messages": [
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {
    #                         "type": "text",
    #                         "text": message_content
    #                     }
    #                 ]
    #             }
    #         ]
    #     }

    #     response = self.bedrock.invoke_model(
    #         modelId='anthropic.claude-3-haiku-20240307-v1:0', 
    #         body=json.dumps(request_body)
    #     )

    #     response_body = json.loads(response.get('body').read())
    #     return response_body['content'][0]['text']
        
        
    def explain_concept(self):
        current_page_content = self.pdf_document[self.current_page].get_text()
        message_content = f"""Context from the PDF:\n\n Page {self.current_page + 1}:\n{current_page_content}\n\n 
        As an experienced technical instructor, present this slide's content to your students. Your explanation should:
    
        1. Start with a brief introduction (1-2 sentences) to capture attention and set the context.
        2. Clearly state the main topic or concept (1 sentence).
        3. Explain 2-3 key points or ideas, using simple language and relatable examples where possible.
        4. If applicable, mention any important formulas, diagrams, or code snippets (briefly).
        5. Conclude with a quick summary or takeaway (1-2 sentences).
    
        Your explanation should be concise yet informative, aiming for about 150 words and designed to be delivered in approximately 2 minutes. Use an engaging, conversational tone as if speaking directly to your students."""
    
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.2,  # Slightly increased for more natural language
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message_content
                        }
                    ]
                }
            ]
        }
    
        response = self.bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0', 
            body=json.dumps(request_body)
        )
    
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']    

    def convert_text_to_speech(self, text):
        response = self.polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId="Matthew"  # You can choose other voices supported by AWS Polly
        )
        return response['AudioStream'].read()

doubt_solver = None

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    global doubt_solver
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.pdf'):
        doubt_solver = DoubtSolver(file)
        return jsonify({'message': 'PDF uploaded successfully'}), 200
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/get_page', methods=['GET'])
def get_page():
    global doubt_solver
    if doubt_solver is None:
        return jsonify({'error': 'No PDF uploaded'}), 400
    page_number = int(request.args.get('page', doubt_solver.current_page))
    doubt_solver.current_page = page_number
    doubt_solver.update_context()
    content = doubt_solver.get_current_page_content()
    image = base64.b64encode(doubt_solver.get_current_page_image()).decode('utf-8')
    return jsonify({
        'content': content,
        'image': image,
        'current_page': doubt_solver.current_page + 1,
        'total_pages': len(doubt_solver.pdf_document)
    }), 200

@app.route('/answer_question', methods=['POST'])
def answer_question():
    global doubt_solver
    if doubt_solver is None:
        return jsonify({'error': 'No PDF uploaded'}), 400
    question = request.json.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    answer = doubt_solver.answer_question(question)
    audio = base64.b64encode(doubt_solver.convert_text_to_speech(answer)).decode('utf-8')
    return jsonify({'answer': answer, 'audio': audio}), 200

@app.route('/start_teaching', methods=['GET'])
def start_teaching():
    global doubt_solver
    if doubt_solver is None:
        return jsonify({'error': 'No PDF uploaded'}), 400
    explanation = doubt_solver.explain_concept()
    audio = base64.b64encode(doubt_solver.convert_text_to_speech(explanation)).decode('utf-8')
    return jsonify({'explanation': explanation, 'audio': audio}), 200

@app.route('/listen_for_question', methods=['POST'])
def listen_for_question():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    recognizer = sr.Recognizer()
    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
            file.save(temp_audio_file.name)
            temp_audio_file_path = temp_audio_file.name

        # Use recognizer on the temporary WAV file
        with sr.AudioFile(temp_audio_file_path) as source:
            audio_data = recognizer.record(source)
            question = recognizer.recognize_google(audio_data)

        # Delete the temporary file
        os.unlink(temp_audio_file_path)

        return jsonify({'question': question}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
