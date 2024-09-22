import streamlit as st
import fitz  # PyMuPDF library for handling PDFs
from collections import deque
import boto3
import json
import speech_recognition as sr
import tempfile
import os
import io
import base64

class DoubtSolver:
    def __init__(self, pdf_file, context_size=5):
        self.pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        self.current_page = 0
        self.context_size = context_size
        self.context = deque(maxlen=context_size)

        # Initialize AWS Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='ap-south-1')  # Change this to your preferred region

        # Initialize AWS Polly client
        self.polly = boto3.client('polly', region_name='ap-south-1')  # Change this to your preferred region

        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()

        # Update context with initial pages
        for _ in range(min(context_size, len(self.pdf_document))):
            self.update_context()

    def next_page(self):
        if self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.update_context()
            return True
        return False
    

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_context()
            return True
        return False

    def update_context(self):
        page_content = self.pdf_document[self.current_page].get_text()
        self.context.append((self.current_page, page_content))

    def get_current_page_content(self):
        return self.pdf_document[self.current_page].get_text()

    def get_current_page_image(self):
        page = self.pdf_document[self.current_page]
        pix = page.get_pixmap()
        img = pix.tobytes("png")
        return img

    def answer_question(self, question):
        context = "\n\n".join([f"Page {page+1}:\n{content}" for page, content in self.context])
        message_content = f"""Context from the PDF:\n\n {context}\n\nQuestion: {question}
                            \n\n Please answer the question based on the context provided above. If the answer is not fully contained in the context, you may use your general knowledge to provide a more comprehensive answer. 
                            However, clearly distinguish between information from the context and additional information you're providing. If you're using information beyond the given context, please state so explicitly.keep your answer within 100 words"""

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

        streaming_response = self.bedrock.invoke_model_with_response_stream(
            modelId='anthropic.claude-3-haiku-20240307-v1:0', 
            body=json.dumps(request_body)
        )

        full_answer = ""
        for event in streaming_response.get("body", []):
            chunk = json.loads(event.get("chunk", {}).get("bytes", b"{}").decode())
            if chunk.get("type") == "content_block_delta":
                text_chunk = chunk.get("delta", {}).get("text", "")
                full_answer += text_chunk
                yield text_chunk

        return full_answer

    def explain_concept(self):
        current_page_content = self.pdf_document[self.current_page].get_text()
        #st.write(current_page_content)
        message_content = f"""Context from the PDF:\n\n Page {self.current_page + 1}:\n{current_page_content}\n\n 
        please explain the slide to student, as an teacher very crisp in less than 150 words"""
        #st.write(message_content)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0,
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

        streaming_response = self.bedrock.invoke_model_with_response_stream(
            modelId='anthropic.claude-3-haiku-20240307-v1:0', 
            body=json.dumps(request_body)
        )

        full_explanation = ""
        for event in streaming_response.get("body", []):
            chunk = json.loads(event.get("chunk", {}).get("bytes", b"{}").decode())
            if chunk.get("type") == "content_block_delta":
                text_chunk = chunk.get("delta", {}).get("text", "")
                full_explanation += text_chunk
                yield text_chunk

        return full_explanation

    def convert_text_to_speech(self, text):
        response = self.polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId="Joanna"  # You can choose other voices supported by AWS Polly
        )
        return response['AudioStream'].read()

    def listen_for_question(self):
        with sr.Microphone() as source:
            st.write("Listening... Speak your question.")
            audio = self.recognizer.listen(source)
        
        try:
            question = self.recognizer.recognize_google(audio)
            return question
        except sr.UnknownValueError:
            return "Speech recognition could not understand the audio"
        except sr.RequestError:
            return "Could not request results from the speech recognition service"
        
    
    def process_teaching(doubt_solver):
        st.write("Processing teaching...")
        explanation_placeholder = st.empty()
        full_explanation = ""
        for token in doubt_solver.explain_concept():
            full_explanation += token
            explanation_placeholder.markdown(f"### Explanation:\n{full_explanation}")

        if full_explanation:
            audio_bytes = doubt_solver.convert_text_to_speech(full_explanation)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            autoplay_audio(tmp_file_path)
            os.unlink(tmp_file_path)  # Delete the temporary file

    def process_question(doubt_solver, question):
        st.write("Processing your question...")
        answer_placeholder = st.empty()
        full_answer = ""
        for token in doubt_solver.answer_question(question):
            full_answer += token
            answer_placeholder.markdown(f"### Answer:\n{full_answer}")

        if full_answer:
            audio_bytes = doubt_solver.convert_text_to_speech(full_answer)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            autoplay_audio(tmp_file_path)
            os.unlink(tmp_file_path)  # Delete the temporary file


def transcribe_audio_file(audio_file):
    recognizer = sr.Recognizer()
    try:
        # Convert uploaded file to AudioSegment
        audio = AudioSegment.from_file(audio_file)
        # Export as WAV in-memory
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Use recognizer on the WAV file
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        return text
    except Exception as e:
        st.error(f"Error in transcription: {str(e)}")
        return None
    
@st.cache_resource
def get_doubt_solver(pdf_file):
    return DoubtSolver(pdf_file)

def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Voice-Enabled Doubt Solver", layout="wide")

    st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
        color: #4A90E2;
    }
    .stButton>button {
        width: 100%;
    }
    .stTextInput>div>div>input {
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-font">Voice-Enabled Doubt Solver</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")

    if uploaded_file is not None:
        doubt_solver = get_doubt_solver(uploaded_file)

        col1, col2 = st.columns([1, 3])

        with col1:
            st.markdown("### Navigation")
            page_number = st.number_input("Go to page", min_value=1, max_value=len(doubt_solver.pdf_document), value=doubt_solver.current_page + 1, step=1)

            if st.button("Go", key="go_button"):
                doubt_solver.current_page = page_number - 1
                doubt_solver.update_context()

            st.markdown(f"**Total pages:** {len(doubt_solver.pdf_document)}")

            col1_1, col1_2 = st.columns(2)
            with col1_1:
                if st.button("◀ Previous"):
                    if doubt_solver.previous_page():
                        st.success(f"Page {doubt_solver.current_page + 1}")
                    else:
                        st.warning("First page")
            with col1_2:
                if st.button("Next ▶"):
                    if doubt_solver.next_page():
                        st.success(f"Page {doubt_solver.current_page + 1}")
                    else:
                        st.warning("Last page")

        with col2:
            st.markdown(f"### Current Page: {doubt_solver.current_page + 1}")
            
            # Split the page display into two columns
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                # Display the PDF page image
                page_image = doubt_solver.get_current_page_image()
                st.image(page_image, caption=f"Page {doubt_solver.current_page + 1}", use_column_width=True)
            
            with col2_2:
                # Display the page content as text
                st.text_area("Page Content", value=doubt_solver.get_current_page_content(), height=400, disabled=True)

            st.markdown("### Ask a Question or Start Teaching")
            
            teaching_mode = st.button("Start Teaching")
            question_mode = st.button("Start Question")
            
            if teaching_mode:
                doubt_solver.process_teaching()
        
            # Use session state to track the input mode
            if 'input_mode' not in st.session_state:
                st.session_state.input_mode = 'text'

            st.markdown("### Ask a Question")

            # Radio button to choose input mode
            input_mode = st.radio("Choose input method:", ('Text', 'Voice'))

            if input_mode == 'Text':
                question = st.text_input("Enter your question:", "")
                if st.button("Submit Question"):
                    if question:
                        doubt_solver.process_question(question)
                    else:
                        st.warning("Please enter a question.")
            else:  # Voice mode
                if st.button("🎤 Start Listening"):
                    question = doubt_solver.listen_for_question()
                    st.write(f"Recognized: {question}")
                    
                    if question and question not in ["Speech recognition could not understand the audio", "Could not request results from the speech recognition service"]:
                        doubt_solver.process_question(question)
                    else:
                        st.warning("Please try speaking your quest whation again.")

    else:
        st.info("Please upload a PDF file to begin.")


if __name__ == "__main__":
    main()