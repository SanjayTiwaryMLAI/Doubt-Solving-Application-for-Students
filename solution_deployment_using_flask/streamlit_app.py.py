import streamlit as st
import requests
import base64
import tempfile
import os
from audio_recorder_streamlit import audio_recorder
import io
from pydub import AudioSegment

def main():
    st.set_page_config(page_title="Voice-Enabled Doubt Solver", layout="wide")
    initialize_session_state()
    set_custom_style()
    
    st.markdown('<p class="big-font">AI Teacher and Voice-Enabled Doubt Solver</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")

    if uploaded_file:
        if handle_pdf_upload(uploaded_file):
            display_pdf_content()
            display_question_section()
    else:
        st.info("Please upload a PDF file to begin.")

def initialize_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'total_pages' not in st.session_state:
        st.session_state.total_pages = 1

def set_custom_style():
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

def handle_pdf_upload(uploaded_file):
    files = {'file': ('file.pdf', uploaded_file.getvalue(), 'application/pdf')}
    try:
        response = requests.post('http://localhost:5000/upload_pdf', files=files)
        if response.status_code == 200:
            st.success("PDF uploaded successfully")
            return True
        else:
            st.error(f"Failed to upload PDF: {response.json().get('error', 'Unknown error')}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the Flask server. Make sure it's running.")
        return False

def display_pdf_content():
    col1, col2 = st.columns([1, 3])

    with col1:
        display_navigation()

    with col2:
        display_current_page()

def display_navigation():
    st.markdown("### Navigation")
    page_number = st.number_input("Go to page", min_value=1, value=st.session_state.current_page, step=1, max_value=st.session_state.total_pages)

    if st.button("Go", key="go_button"):
        navigate_to_page(page_number)

    st.markdown(f"**Current page:** {st.session_state.current_page}")
    st.markdown(f"**Total pages:** {st.session_state.total_pages}")
    
    col1_1, col1_2 = st.columns(2)
    with col1_1:
        if st.button("◀ Previous"):
            navigate_to_page(st.session_state.current_page - 1)
    with col1_2:
        if st.button("Next ▶"):
            navigate_to_page(st.session_state.current_page + 1)

def navigate_to_page(page_number):
    if 1 <= page_number <= st.session_state.total_pages:
        st.session_state.current_page = page_number
        st.experimental_rerun()

def display_current_page():
    st.markdown(f"### Current Page: {st.session_state.current_page}")
    
    try:
        response = requests.get(f'http://localhost:5000/get_page?page={st.session_state.current_page-1}')
        if response.status_code == 200:
            page_data = response.json()
            st.session_state.total_pages = page_data['total_pages']
            
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                st.image(f"data:image/png;base64,{page_data['image']}", caption=f"Page {st.session_state.current_page}", use_column_width=True)
            
            with col2_2:
                st.text_area("Page Content", value=page_data['content'], height=400, disabled=True)
        else:
            st.error(f"Failed to get page content: {response.json().get('error', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the Flask server. Make sure it's running.")

def display_question_section():
    st.markdown("### Ask a Question or Start Teaching")
    
    if st.button("Start Teaching"):
        start_teaching()

    st.markdown("### Ask a Question")
    input_mode = st.radio("Choose input method:", ('Text', 'Voice'))

    if input_mode == 'Text':
        handle_text_input()
    else:
        handle_voice_input()

def start_teaching():
    try:
        response = requests.get('http://localhost:5000/start_teaching')
        if response.status_code == 200:
            explanation_data = response.json()
            st.markdown(f"### Explanation:\n{explanation_data['explanation']}")
            play_audio(explanation_data['audio'])
        else:
            st.error(f"Failed to start teaching: {response.json().get('error', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the Flask server. Make sure it's running.")

def handle_text_input():
    question = st.text_input("Enter your question:", "")
    if st.button("Submit Question"):
        if question:
            process_question(question)
        else:
            st.warning("Please enter a question.")

def handle_voice_input():
    audio_bytes = audio_recorder()
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        question = transcribe_audio(audio_bytes)
        if question:
            st.write(f"Recognized: {question}")
            process_question(question)
        else:
            st.error("Failed to recognize speech. Please try again.")
    else:
        st.warning("No audio recorded. Please try again.")

def transcribe_audio(audio_bytes):
    audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        audio.export(temp_audio_file.name, format="wav")
        temp_audio_file_path = temp_audio_file.name

    try:
        files = {'file': ('question.wav', open(temp_audio_file_path, 'rb'), 'audio/wav')}
        response = requests.post('http://localhost:5000/listen_for_question', files=files)
        if response.status_code == 200:
            return response.json()['question']
        else:
            st.error(f"Failed to recognize speech: {response.json().get('error', 'Unknown error')}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the Flask server. Make sure it's running.")
        return None
    finally:
        os.unlink(temp_audio_file_path)

def process_question(question):
    try:
        response = requests.post('http://localhost:5000/answer_question', json={'question': question})
        if response.status_code == 200:
            answer_data = response.json()
            st.markdown(f"### Answer:\n{answer_data['answer']}")
            play_audio(answer_data['audio'])
        else:
            st.error(f"Failed to get answer: {response.json().get('error', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the Flask server. Make sure it's running.")

def play_audio(audio_base64):
    audio_bytes = base64.b64decode(audio_base64)
    st.audio(audio_bytes, format="audio/mp3")

if __name__ == "__main__":
    main()
