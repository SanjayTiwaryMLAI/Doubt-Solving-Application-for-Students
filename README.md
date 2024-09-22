
# Voice-Enabled Doubt Solver

This project is an AI-powered, voice-enabled doubt solver that allows users to navigate through PDF documents, ask questions, and receive explanations using both text and voice inputs.

## Features

- PDF document navigation
- Text and voice input for questions
- AI-powered question answering using AWS Bedrock
- Text-to-speech conversion of answers using AWS Polly
- "Start Teaching" feature that explains the current page content

## Prerequisites

- Python 3.7+
- AWS account with Bedrock and Polly access
- Properly configured AWS credentials

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/voice-enabled-doubt-solver.git
   cd voice-enabled-doubt-solver
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your AWS credentials:
   - Create a file named `~/.aws/credentials` (on Linux/Mac) or `C:\Users\YOUR_USERNAME\.aws\credentials` (on Windows)
   - Add your AWS credentials to this file:
     ```
     [default]
     aws_access_key_id = YOUR_ACCESS_KEY
     aws_secret_access_key = YOUR_SECRET_KEY
     ```

## Usage

1. Start the Flask backend:
   ```
   python flask_app.py
   ```

2. In a separate terminal, start the Streamlit frontend:
   ```
   streamlit run streamlit_app.py
   ```

3. Open your web browser and navigate to the URL provided by Streamlit (usually `http://localhost:8501`)

4. Upload a PDF file, navigate through pages, ask questions using text or voice, and explore the "Start Teaching" feature.

## Project Structure

- `flask_app.py`: Backend Flask application
- `streamlit_app.py`: Frontend Streamlit application
- `requirements.txt`: List of Python dependencies
- `README.md`: Project documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
