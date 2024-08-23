import streamlit as st
import fitz  # PyMuPDF library for handling PDFs
from collections import deque
import boto3
import json
import tempfile
import os

class DoubtSolver:
    def __init__(self, pdf_file, context_size=5):
        self.pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        self.current_page = 0
        self.context_size = context_size
        self.context = deque(maxlen=context_size)
        
        # Initialize AWS Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='your-region'  # e.g., 'us-east-1'
        )
        
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

    def answer_question(self, question):
        context = "\n\n".join([f"Page {page+1}:\n{content}" for page, content in self.context])
        message_content = f"Context from the PDF:\n\n{context}\n\nQuestion: {question}\n\nPlease answer the question based on the context provided above. If the answer is not in the context, please say so."

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
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
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

@st.cache_resource
def get_doubt_solver(pdf_file):
    return DoubtSolver(pdf_file)

def main():
    st.set_page_config(page_title="Doubt Solving Application", layout="wide")

    st.title("Doubt Solving Application for Students")
    st.markdown("---")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        doubt_solver = get_doubt_solver(uploaded_file)

        col1, col2 = st.columns([1, 2])

        with col1:
            st.sidebar.title("Navigation")
            page_number = st.sidebar.number_input("Go to page", min_value=1, max_value=len(doubt_solver.pdf_document), value=doubt_solver.current_page + 1, step=1)
            
            if st.sidebar.button("Go"):
                doubt_solver.current_page = page_number - 1
                doubt_solver.update_context()

            st.sidebar.markdown("---")
            st.sidebar.write(f"Total pages: {len(doubt_solver.pdf_document)}")

            if st.sidebar.button("Previous Page"):
                if doubt_solver.previous_page():
                    st.sidebar.success(f"Moved to page {doubt_solver.current_page + 1}")
                else:
                    st.sidebar.warning("You're already on the first page.")

            if st.sidebar.button("Next Page"):
                if doubt_solver.next_page():
                    st.sidebar.success(f"Moved to page {doubt_solver.current_page + 1}")
                else:
                    st.sidebar.warning("You're already on the last page.")

        with col2:
            st.subheader(f"Current Page: {doubt_solver.current_page + 1}")
            st.text_area("Page Content", value=doubt_solver.get_current_page_content(), height=300, disabled=True)

            st.markdown("---")
            st.subheader("Ask a Question")
            question = st.text_input("Enter your question about the current or previous pages:")
            if st.button("Submit Question"):
                if question:
                    with st.spinner("Generating answer..."):
                        answer = doubt_solver.answer_question(question)
                    st.markdown("### Answer:")
                    st.write(answer)
                else:
                    st.warning("Please enter a question.")
    else:
        st.info("Please upload a PDF file to begin.")

if __name__ == "__main__":
    main()