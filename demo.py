import fitz  # PyMuPDF library for handling PDFs
from collections import deque
import boto3
import json

class DoubtSolver:
    def __init__(self, pdf_path, context_size=5):
        self.pdf_document = fitz.open(pdf_path)
        self.current_page = 0
        self.context_size = context_size
        self.context = deque(maxlen=context_size)
        
        # Initialize AWS Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='ap-south-1'  # e.g., 'us-east-1'
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
        # Prepare the context for Claude
        context = "\n\n".join([f"Page {page+1}:\n{content}" for page, content in self.context])
        
        # Prepare the message for Claude 3 Sonnet
        message_content = f"Context from the PDF:\n\n{context}\n\nQuestion: {question}\n\nPlease answer the question based on the context provided above. If the answer is not in the context, please say so."

        # Prepare the request body
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

        # Call Claude 3 Sonnet model via AWS Bedrock
        response = self.bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

def main():
    pdf_path = "python-course-for-assistant.pdf"
    doubt_solver = DoubtSolver(pdf_path)

    while True:
        print(f"\nCurrent page: {doubt_solver.current_page + 1}")
        print("1. View current page content")
        print("2. Next page")
        print("3. Previous page")
        print("4. Ask a question")
        print("5. Exit")

        choice = input("Enter your choice (1-5): ")

        if choice == '1':
            print(doubt_solver.get_current_page_content())
        elif choice == '2':
            if not doubt_solver.next_page():
                print("You're already on the last page.")
        elif choice == '3':
            if not doubt_solver.previous_page():
                print("You're already on the first page.")
        elif choice == '4':
            question = input("Enter your question: ")
            answer = doubt_solver.answer_question(question)
            print(answer)
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")

    doubt_solver.pdf_document.close()

if __name__ == "__main__":
    main()