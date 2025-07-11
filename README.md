# AI Notes Summarizer 📚✨

A simple web app that takes input via text, PDF, or image and generates:
- A concise summary
- Key points
- 3–5 MCQs

## 🛠 Tech Stack
- Flask (Python)
 PyMuPDF for PDF text extraction
- pytesseract + Pillow for image OCR
- reportlab for PDF generation (requires a Unicode font file like DejaVuSans.ttf for full character support)
 
## 🔑 API Key
This application requires a Gemini API key. It is currently hardcoded in `app.py`. For production use, consider using environment variables.

## 🚀 How to Run
```bash
pip install -r requirements.txt
python app.py
