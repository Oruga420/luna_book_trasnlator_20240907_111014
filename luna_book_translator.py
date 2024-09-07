import os
import time
import json
import requests
import gradio as gr
from typing import List, Optional
from pydantic import BaseModel
import PyPDF2
from docx import Document

# OpenAI API Key and Assistant IDs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TRANSLATOR_ASSISTANT_ID = "add your assistant id here"  # Replace with actual ID
REVIEWER_ASSISTANT_ID = "add your assistant id here"  # Replace with actual ID

# Pydantic models
class TranslationProgress(BaseModel):
    current_page: int = 0
    last_reviewed_page: int = 0
    total_pages: int
    status: str = "in_progress"

class TranslationChunk(BaseModel):
    start_page: int
    end_page: int
    content: str

class ReviewResult(BaseModel):
    chunk_id: str
    is_coherent: bool
    comments: Optional[str] = None

class TranslationJob(BaseModel):
    book_id: str
    source_language: str
    target_language: str
    progress: TranslationProgress
    chunks: List[TranslationChunk] = []
    reviews: List[ReviewResult] = []

class Config(BaseModel):
    chunk_size: int = 10
    review_interval: int = 10
    double_review_interval: int = 20

def send_to_openai(assistant_id: str, content: str, instruction: str) -> str:
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
        'OpenAI-Beta': 'assistants=v2'
    }

    # Create a new thread
    thread_response = requests.post('https://api.openai.com/v1/threads', headers=headers)
    if thread_response.status_code != 200:
        raise Exception(f"Error creating thread: {thread_response.text}")
    thread_id = thread_response.json().get('id')

    # Add the message to the thread
    message_data = {'role': 'user', 'content': content}
    message_response = requests.post(f'https://api.openai.com/v1/threads/{thread_id}/messages', headers=headers, json=message_data)
    if message_response.status_code != 200:
        raise Exception(f"Error adding message to thread: {message_response.text}")

    # Run the assistant on the thread
    run_data = {
        'assistant_id': assistant_id,
        'instructions': instruction,
    }
    run_response = requests.post(f'https://api.openai.com/v1/threads/{thread_id}/runs', headers=headers, json=run_data)
    if run_response.status_code != 200:
        raise Exception(f"Error running assistant on thread: {run_response.text}")
    
    run_id = run_response.json().get('id')

    # Poll for the run to complete
    while True:
        run_status_response = requests.get(f'https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}', headers=headers)
        if run_status_response.status_code != 200:
            raise Exception(f"Error checking run status: {run_status_response.text}")
        
        status = run_status_response.json().get('status')
        if status == 'completed':
            break
        elif status in ['failed', 'cancelled', 'expired']:
            raise Exception(f"Run failed with status: {status}")
        
        time.sleep(1)  # Wait before polling again

    # Retrieve the assistant's response
    messages_response = requests.get(f'https://api.openai.com/v1/threads/{thread_id}/messages', headers=headers)
    if messages_response.status_code != 200:
        raise Exception(f"Error retrieving messages: {messages_response.text}")

    messages = messages_response.json().get('data', [])
    assistant_messages = [msg for msg in messages if msg['role'] == 'assistant']
    if assistant_messages and assistant_messages[0].get('content'):
        return assistant_messages[0]['content'][0]['text']['value']
    else:
        raise Exception("No valid response from the assistant.")

class TranslationOrchestrator:
    def __init__(self, book_path: str, source_lang: str, target_lang: str):
        self.config = Config()
        self.book_path = book_path
        self.book_content = self.read_book(book_path)
        self.job = TranslationJob(
            book_id=os.path.basename(book_path),
            source_language=source_lang,
            target_language=target_lang,
            progress=TranslationProgress(total_pages=len(self.book_content))
        )

    def read_book(self, book_path: str) -> List[str]:
        _, file_extension = os.path.splitext(book_path)
        if file_extension.lower() == '.pdf':
            return self.read_pdf(book_path)
        elif file_extension.lower() == '.txt':
            return self.read_txt(book_path)
        else:
            raise ValueError("Unsupported file format. Please use PDF or TXT files.")

    def read_pdf(self, pdf_path: str) -> List[str]:
        pages = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pages.append(page.extract_text())
        return pages

    def read_txt(self, txt_path: str) -> List[str]:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Split the content into pages (assuming 3000 characters per page)
            return [content[i:i+3000] for i in range(0, len(content), 3000)]

    def translate_chunk(self, start_page: int, end_page: int, content: str) -> str:
        instruction = f"Translate the following text from {self.job.source_language} to {self.job.target_language}."
        return send_to_openai(TRANSLATOR_ASSISTANT_ID, content, instruction)

    def review_chunk(self, chunk: TranslationChunk, previous_chunk: Optional[TranslationChunk] = None) -> ReviewResult:
        content_to_review = chunk.content
        if previous_chunk:
            content_to_review = f"Previous chunk:\n{previous_chunk.content}\n\nCurrent chunk:\n{chunk.content}"
        
        instruction = "Review the following translated text for coherence and consistency."
        review_result = send_to_openai(REVIEWER_ASSISTANT_ID, content_to_review, instruction)
        
        is_coherent = "coherent" in review_result.lower() and "consistent" in review_result.lower()
        return ReviewResult(chunk_id=f"{chunk.start_page}-{chunk.end_page}", is_coherent=is_coherent, comments=review_result)

    def redo_translation(self, start_page: int, end_page: int) -> None:
        print(f"Redoing translation for pages {start_page} to {end_page}")
        content = "\n".join(self.book_content[start_page-1:end_page])
        translated_content = self.translate_chunk(start_page, end_page, content)
        chunk_index = next(i for i, chunk in enumerate(self.job.chunks) if chunk.start_page == start_page)
        self.job.chunks[chunk_index] = TranslationChunk(start_page=start_page, end_page=end_page, content=translated_content)

    def process_book(self, progress=gr.Progress()) -> str:
        try:
            total_pages = self.job.progress.total_pages
            for i in progress.tqdm(range(0, total_pages, self.config.chunk_size)):
                start_page = i + 1
                end_page = min(i + self.config.chunk_size, total_pages)
                
                content = "\n".join(self.book_content[start_page-1:end_page])
                translated_content = self.translate_chunk(start_page, end_page, content)
                chunk = TranslationChunk(start_page=start_page, end_page=end_page, content=translated_content)
                self.job.chunks.append(chunk)
                
                if len(self.job.chunks) % self.config.review_interval == 0:
                    review_result = self.review_chunk(chunk)
                    self.job.reviews.append(review_result)
                    
                    if not review_result.is_coherent:
                        print(f"Chunk {chunk.start_page}-{chunk.end_page} is not coherent. Redoing the last {self.config.review_interval} pages.")
                        redo_start = max(1, start_page - self.config.review_interval + 1)
                        self.redo_translation(redo_start, end_page)
                
                if len(self.job.chunks) % self.config.double_review_interval == 0:
                    previous_chunk = self.job.chunks[-2]
                    double_review_result = self.review_chunk(chunk, previous_chunk)
                    self.job.reviews.append(double_review_result)
                    
                    if not double_review_result.is_coherent:
                        print(f"Last {self.config.double_review_interval} pages are not coherent. Redoing them.")
                        redo_start = max(1, start_page - self.config.double_review_interval + 1)
                        self.redo_translation(redo_start, end_page)
                
                self.job.progress.current_page = end_page
                progress(end_page / total_pages, desc="Translating")

            self.job.progress.status = "completed"
            translated_content = "\n".join([chunk.content for chunk in self.job.chunks])
            self.save_translation(translated_content)
            return "Book translation completed! Saved to add your saving folder address"
        except Exception as e:
            self.job.progress.status = "failed"
            return f"Book translation failed: {str(e)}"

    def save_translation(self, content: str):
        doc = Document()
        doc.add_paragraph(content)
        filename = f"{self.job.book_id}_{self.job.target_language}.docx"
        save_path = os.path.join("add your saving folder address", filename)
        doc.save(save_path)

def translate_book(book, source_lang, target_lang, progress=gr.Progress()):
    orchestrator = TranslationOrchestrator(book.name, source_lang, target_lang)
    return orchestrator.process_book(progress)

# Gradio interface
iface = gr.Interface(
    fn=translate_book,
    inputs=[
        gr.File(label="Upload Book (PDF or TXT)"),
        gr.Dropdown(choices=["English", "Spanish", "French", "German", "Italian"], label="Source Language"),
        gr.Dropdown(choices=["English", "Spanish", "French", "German", "Italian"], label="Target Language")
    ],
    outputs="text",
    title="Luna's Book Translator",
    description="Upload a book and select languages to translate it!",
)

if __name__ == "__main__":
    iface.queue()  # Enable queuing
    iface.launch(share=True)