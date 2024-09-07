# Luna's Book Translator - README

## Project Overview

**Luna's Book Translator** is an AI-powered tool designed to translate books (in PDF or TXT format) from one language to another using OpenAI's GPT models. The project leverages Gradio for a simple, user-friendly interface, allowing users to upload a book, choose the source and target languages, and translate the book chunk by chunk. The translation process also includes reviewing for coherence and consistency at regular intervals to ensure high-quality output.

## Features

- **Multi-language Support:** Translate books between languages such as English, Spanish, French, German, and Italian.
- **Chunk-Based Translation:** Efficiently handles large books by dividing them into manageable chunks for translation.
- **Coherence Review:** Automatically reviews translated chunks to ensure coherence and consistency.
- **Gradio Interface:** User-friendly interface to upload a book, select languages, and initiate translation.
- **Real-time Progress Tracking:** Displays the translation progress in real-time.

## Requirements

- Python 3.8+
- OpenAI API Key
- Dependencies:
  - `os`
  - `time`
  - `json`
  - `requests`
  - `gradio`
  - `pydantic`
  - `PyPDF2`
  - `python-docx`

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/lunas-book-translator.git
    cd lunas-book-translator
    ```

2. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Set your OpenAI API key as an environment variable:
    ```bash
    export OPENAI_API_KEY='your_openai_api_key'
    ```

4. Replace the placeholders `TRANSLATOR_ASSISTANT_ID` and `REVIEWER_ASSISTANT_ID` in the code with your actual assistant IDs from OpenAI.

## How to Use

1. **Launch the app:**
   Run the following command to launch the Gradio interface:
   ```bash
   python translator.py
   ```

2. **Upload the book:**  
   Choose a PDF or TXT file you want to translate.

3. **Select source and target languages:**  
   Pick the languages you want to translate the book from and to (e.g., Spanish to English).

4. **Start the translation:**  
   The app will process the book, translating it chunk by chunk while displaying the real-time progress. Reviews for coherence will happen automatically at regular intervals.

5. **Save the translated book:**  
   Once the translation is complete, the translated book will be saved as a `.docx` file in the specified folder.

## Example Usage

```python
# Sample code for translation
from gradio import Progress

# Call the translate_book function
translate_book("path_to_book.pdf", "English", "Spanish", progress=Progress())
```

## Notes

- Ensure you have configured the OpenAI API key correctly.
- The tool currently supports books in PDF and TXT formats only.
- Reviews for coherence happen every 10 pages by default and can be adjusted in the `Config` class.

## Future Enhancements

- Support for additional file formats (e.g., EPUB).
- Ability to translate books in real-time without chunk-based processing.
- More customization options for chunk size and review intervals.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For questions or suggestions, feel free to reach out at `your.email@example.com`.
