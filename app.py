from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import pytesseract # Make sure to install Tesseract OCR engine and add to PATH or specify tesseract_cmd
from PIL import Image
import google.generativeai as genai
from io import BytesIO
from reportlab.lib.pagesizes import letter # Keep for page size reference if needed elsewhere
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# If Tesseract is not in your PATH, uncomment and set the path to tesseract.exe
# For example, on Windows:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # VERIFY THIS PATH or change it to your actual Tesseract installation path

app = Flask(__name__)

# --- Font Registration for ReportLab ---
# Ensure you have a .ttf font file (e.g., DejaVuSans.ttf) that supports the required characters.
# Place it in a location accessible by your app (e.g., same directory or a 'fonts' folder).
FONT_NAME = "Helvetica"  # Default fallback
try:
    # Replace 'DejaVuSans.ttf' with the actual path to your font file if it's not in the same directory.
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVuSans'
    print("Successfully registered DejaVuSans font.")
except Exception as e:
    print(f"Warning: Could not register DejaVuSans font. Falling back to Helvetica. Error: {e}")
    print("Ensure 'DejaVuSans.ttf' (and optionally 'DejaVuSans-Bold.ttf') is accessible by the application.")
# --- End Font Registration ---

# Set your Gemini API key (Consider using environment variables for API keys)
genai.configure(api_key="AIzaSyBlVwDETm7tK0-ffr-1_M6q9Dm-Eu7xRcU")

# Use a supported model name for generate_content
model = genai.GenerativeModel("gemini-1.5-flash-latest")

def extract_text_from_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        print("ERROR: Tesseract is not installed or not found in PATH/specified_cmd. Please check Tesseract installation.")
        raise # Re-raise the exception to be caught by the main route's error handling

def generate_ai_response(text, language="English"):
    prompt = f"""Summarize the following notes in {language}. Provide key points and generate 3 multiple choice questions:

{text}
"""
    response = model.generate_content(prompt)
    return response.text

@app.route("/", methods=["GET", "POST"])
def index():
    output = ""
    error_message = ""
    if request.method == "POST":
        language = request.form.get("language", "English")
        user_input = request.form.get("notes")
        file = request.files.get("file")
        text = ""

        if user_input:
            text = user_input
        elif file:
            if file.filename.endswith(".pdf"):
                try:
                    text = extract_text_from_pdf(file)
                except Exception as e: # General exception for PDF processing
                    print(f"Error extracting text from PDF: {e}")
                    error_message = "Could not process the PDF file. It might be corrupted or in an unsupported format."
            elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    text = extract_text_from_image(file)
                except pytesseract.TesseractNotFoundError:
                    error_message = "OCR functionality is not available. Please ensure Tesseract OCR is correctly installed and configured."
                except Exception as e: # Other image processing errors
                    print(f"Error extracting text from image: {e}")
                    error_message = "Could not process the image file."
            
            if not text.strip():
                error_message = "Could not extract text from the uploaded file, or the file is empty. Please try a different file."

        if text:
            if not error_message: # Proceed only if no prior extraction error
                try:
                    output = generate_ai_response(text, language)
                    if not output.strip():
                        error_message = "The content could not be summarized. It might be too short, unclear, or not suitable for summarization."
                except Exception as e:
                    print(f"Error during AI response generation: {e}")
                    error_message = "An error occurred while trying to generate the summary. Please try again."
        elif not user_input and not file:
            error_message = "Please enter notes or upload a file."

    return render_template("index.html", output=output, error_message=error_message)

@app.route("/download", methods=["POST"])
def download_pdf():
    try:
        content = request.form["content"]
        buffer = BytesIO()

        left_margin = 72  # 1 inch
        right_margin = 72 # 1 inch
        top_margin = 72   # 1 inch
        bottom_margin = 72 # 1 inch

        doc = SimpleDocTemplate(buffer,
                                pagesize=letter,
                                leftMargin=left_margin,
                                rightMargin=right_margin,
                                topMargin=top_margin,
                                bottomMargin=bottom_margin)

        styles = getSampleStyleSheet()
        # Create a new style or modify an existing one to use the registered font
        # It's often better to create a new style to avoid modifying the global stylesheet
        custom_style = styles['Normal'] # Start with a copy of the 'Normal' style
        custom_style.fontName = FONT_NAME
        custom_style.fontSize = 12 # Set font size directly
        custom_style.leading = 12 * 1.2 # Adjust line spacing (leading) if needed

        story = []
        # Replace newline characters with <br/> tags for Paragraph to interpret as line breaks
        formatted_content = content.replace('\n', '<br/>')
        story.append(Paragraph(formatted_content, custom_style))

        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="summary.pdf", mimetype="application/pdf")
    except Exception as e:
        print(f"Error during PDF generation: {e}")
        return "Error generating PDF. Please check server logs for details.", 500

if __name__ == "__main__":
    app.run(debug=True)
