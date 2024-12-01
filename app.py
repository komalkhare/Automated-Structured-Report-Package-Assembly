import streamlit as st
import json
import PyPDF2
from PIL import Image
from fpdf import FPDF
import pytesseract
import tempfile

# Configure Tesseract OCR path if needed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust as necessary

# Function to create the report structure based on the checklist
def generate_report_structure(sections):
    structure = {section["title"]: [] for section in sections}
    return structure

# Function to populate the report with extracted content
def populate_report(structure, base_documents, checklist):
    for section in checklist["sections"]:
        section_title = section["title"]
        
        # Extract pages if specified
        if "ExtractPages" in section:
            for doc in section["ExtractPages"]:
                file_name = doc.get("file")
                if file_name in base_documents:
                    file_type = doc.get("type", "pdf").lower()  # Default to PDF if type is not specified
                    if file_type == "pdf":
                        extracted_content = extract_pages(base_documents[file_name], doc["pages"])
                    elif file_type in ["png", "jpg", "jpeg"]:
                        extracted_content = extract_text_from_image(base_documents[file_name])
                    else:
                        extracted_content = f"Unsupported file type: {file_type}"
                    
                    structure[section_title].append(extracted_content)
                else:
                    structure[section_title].append(f"File '{file_name}' not found.")
        
        # Add placeholders if specified
        if "GeneratePlaceholder" in section:
            structure[section_title].append(section["GeneratePlaceholder"])
    
    return structure

# Function to extract content from a PDF
def extract_pages(pdf_file, pages):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        extracted_text = ""
        if pages:
            for page_num in pages:
                extracted_text += pdf_reader.pages[page_num - 1].extract_text()  # Pages are 0-indexed
        else:
            for page in pdf_reader.pages:
                extracted_text += page.extract_text()
        return extracted_text
    except Exception as e:
        return f"Error extracting pages: {e}"

# Function to extract text from an image using pytesseract
def extract_text_from_image(image_file):
    try:
        image = Image.open(image_file)
        extracted_text = pytesseract.image_to_string(image)
        return extracted_text
    except Exception as e:
        return f"Error extracting text from image: {e}"

# Function to generate a PDF with Unicode support
def generate_pdf_with_navigation(structure, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("ArialUnicode", "", "Arial Unicode MS.TTF", uni=True)  # Ensure the font is available
    pdf.set_font("ArialUnicode", size=12)
    
    for section, content in structure.items():
        pdf.add_page()
        pdf.set_font("ArialUnicode", size=16)
        pdf.cell(200, 10, txt=section, ln=True, align='C')
        pdf.ln(10)  # Add space
        pdf.set_font("ArialUnicode", size=12)
        
        for item in content:
            safe_text = item.replace("•", "-").encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 10, txt=safe_text)
    
    pdf.output(output_path)

# Function to validate the report structure
def validate_report(structure, checklist):
    for section in checklist["sections"]:
        section_title = section["title"]
        if section_title not in structure or not structure[section_title]:
            return False, f"Missing content for section: {section_title}"
    return True, "Validation Passed"

# Streamlit app interface
st.title("Automated Structured Report Package Assembly")

# Upload base documents
st.sidebar.header("Upload Base Documents")
base_documents = {}
uploaded_files = st.sidebar.file_uploader("Upload PDFs and Images", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
for uploaded_file in uploaded_files:
    base_documents[uploaded_file.name] = uploaded_file

# Input checklist
st.sidebar.header("Define Checklist")
checklist_input = st.sidebar.text_area("Checklist JSON", height=300)

if st.sidebar.button("Generate Report"):
    if not checklist_input:
        st.error("Please provide a checklist.")
    else:
        try:
            # Parse the checklist JSON
            checklist = json.loads(checklist_input)

            # Validate checklist structure
            if "sections" not in checklist or not isinstance(checklist["sections"], list):
                st.error("Invalid checklist format. Ensure it includes a 'sections' key with a list of sections.")
            else:
                # Generate structure and populate content
                structure = generate_report_structure(checklist["sections"])
                populated_structure = populate_report(structure, base_documents, checklist)

                # Validate the report
                valid, message = validate_report(populated_structure, checklist)
                if valid:
                    st.success(message)

                    # Generate PDF
                    output_path = "generated_report.pdf"
                    generate_pdf_with_navigation(populated_structure, output_path)

                    # Provide download link
                    with open(output_path, "rb") as f:
                        st.download_button("Download Report", f, file_name="report.pdf")
                else:
                    st.error(message)
        except json.JSONDecodeError:
            st.error("Invalid JSON format. Please check your checklist input.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
