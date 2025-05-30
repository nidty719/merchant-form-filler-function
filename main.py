import functions_framework
import os
import base64
import io
from datetime import datetime

# Using PDFMiner for extracting field positions (optional but helpful for debugging)
try:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

# Using fillpdf for filling the PDF form
from fillpdf import fillpdfs

# Using PyPDF2 and reportlab for creating and merging overlays
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

# --- Configuration ---
TEMPLATE_PDF_PATH = os.path.join(os.path.dirname(__file__), "Nexli App fillable - working.pdf")  # Using the fillable version
OUTPUT_PDF_FILENAME = "filled_form.pdf"
# --- Signature positioning ---
SIGNATURE_X = 350  # Centered position
SIGNATURE_Y = 250  # Higher on the page
SIGNATURE_WIDTH = 200  # Make signature wider
TEXT_X = 350       # Text below signature
TEXT_Y = 230       # Text position
# --- Font configuration ---
FONT_SIZE = 4
CHECKBOX_SIZE = 10

# Signature positioning (updated based on the form layout)
SIGNATURE_POSITION = {
    "x": 50,      # X coordinate - moved further left to align with signature line
    "y": 50,      # Y coordinate - moved down to better align with signature line
    "width": 350,  # Width adjusted to better fit the signature line
    "page": 0     # Page index (0-based)
}

# Check if PDF is fillable on startup - this will log the field names
try:
    if os.path.exists(TEMPLATE_PDF_PATH):
        fields = fillpdfs.get_form_fields(TEMPLATE_PDF_PATH)
        print(f"PDF form fields found in template: {fields}")
    else:
        print(f"Warning: Template PDF '{TEMPLATE_PDF_PATH}' not found.")
except Exception as e:
    print(f"Warning: Error checking PDF form fields: {e}")

# Special fields that require custom handling
CHECKBOX_FIELDS = [
    "bankAccountOpen90Days",
    "isBusinessForSale", 
    "filedBankruptcy", 
    "hasTaxLiens", 
    "isUSCitizenPermanentResident",
    "ownOrRent",
    "agreeToTerms"
]

# Field mapping from input fields to PDF form fields1
FIELD_MAPPING = {
    # Text Fields
    "legalBusinessName": "Text_1",
    "dbaName": "Text_2",
    "physicalAddress": "Text_3",
    "city": "Text_4",
    "state": "Text_5",
    "zipCode": "Text_6",
    "businessPhone": "Text_7",
    "businessFax": "Text_8",
    "businessEmail": "Text_9",
    "estimatedMonthlySales": "Text_10",
    "estimatedMonthlyCCSales": "Text_11",
    "businessStartDate": "Text_12",
    "bankingInstitution": "Text_13",
    "timeRemainingOnLeaseMortgage": "Text_14",
    "businessType": "Text_15",
    "landlordAgentName": "Text_16",
    "landlordAgentPhone": "Text_17",
    "numberOfLocations": "Text_18",
    "federalTaxId": "Text_19",
    "amountRequested": "Text_20",
    "intendedUseOfMoney": "Text_21",
    "typeOfEntity": "Text_22",
    "authorizedSignerName": "Text_23",
    "authorizedSignerTitle": "Text_40",  # Added mapping for signer title
    
    # Principal Owner Information section
    "ownershipPercentage": "Text_25",  # % Ownership field
    "score": "Text_26",  # Score field
    "principalOwnerName": "Text_27",  # Principal Owner Name
    "ssn": "Text_28",  # Social Security #
    "dob": "Text_29",  # D.O.B
    "homeAddress": "Text_30",  # Home Address
    "homeCity": "Text_31",  # City
    "homeState": "Text_32",  # State
    "homeZipCode": "Text_33",  # Zip
    "homePhone": "Text_34",  # Home Phone
    "mobilePhone": "Text_35",  # Mobile
    "timeAtHomeAddress": "Text_36",  # How Long at Home Address
    "timeAtPreviousHomeAddress": "Text_37",  # Number of years at previous home address
    "estimatedAnnualIncome": "Text_38",  # Estimated Current Annual Income
    "signatureDate": "Text_39",  # Signature Date
    
    # Checkboxes - Yes/No pairs
    "bankAccountOpen90Days": ["Checkbox_1", "Checkbox_2"],  # Yes/No pair
    "isBusinessForSale": ["Checkbox_3", "Checkbox_4"],      # Yes/No pair
    "filedBankruptcy": ["Checkbox_5", "Checkbox_6"],       # Yes/No pair
    "hasTaxLiens": ["Checkbox_7", "Checkbox_8"],           # Yes/No pair
    "isUSCitizenPermanentResident": ["Checkbox_9", "Checkbox_10"],  # Yes/No pair
    "ownOrRent": ["Checkbox_11", "Checkbox_12"],           # Own/Rent pair
    "agreeToTerms": ["Checkbox_13", "Checkbox_14"]         # Yes/No pair
}

# Method to add signature to the PDF
def add_signature_to_pdf(input_pdf_path, output_pdf_path, signature_image_path, signature_hash=None, signature_date=None):
    """Add signature image to PDF as an overlay"""
    
    # Load the input PDF
    template_pdf = PdfReader(input_pdf_path)
    output_pdf = PdfWriter()
    
    # Create overlay with signature
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Load and process the signature image
    signature_image = Image.open(signature_image_path)
    
    # Ensure we preserve transparency
    if signature_image.mode != 'RGBA':
        signature_image = signature_image.convert('RGBA')
    
    # Create a white background layer
    background = Image.new('RGBA', signature_image.size, (255, 255, 255, 0))
    
    # Composite the image onto the transparent background
    signature_image = Image.alpha_composite(background, signature_image)
    
    # Calculate aspect ratio
    img_width, img_height = signature_image.size
    aspect = img_height / float(img_width)
    
    # Position information
    x = SIGNATURE_POSITION["x"]
    y = SIGNATURE_POSITION["y"]
    width = SIGNATURE_POSITION["width"]
    height = width * aspect * 0.25  # Made signature height even smaller (25% of proportional height)
    
    # Add the signature to the canvas
    sig_image_reader = ImageReader(signature_image)
    can.drawImage(sig_image_reader, x, y, width=width, height=height, mask='auto')
    
    # Save the canvas
    can.save()
    packet.seek(0)
    
    # Create overlay PDF
    overlay_pdf = PdfReader(packet)
    
    # Apply overlay to the first page (or specified page)
    page_idx = SIGNATURE_POSITION["page"]
    if 0 <= page_idx < len(template_pdf.pages):
        page = template_pdf.pages[page_idx]
        page.merge_page(overlay_pdf.pages[0])
        output_pdf.add_page(page)
        
        # Add all other pages unchanged
        for i in range(len(template_pdf.pages)):
            if i != page_idx:
                output_pdf.add_page(template_pdf.pages[i])
    else:
        # If page index is invalid, just add all pages unchanged
        for i in range(len(template_pdf.pages)):
            output_pdf.add_page(template_pdf.pages[i])
    
    # Write output PDF
    with open(output_pdf_path, "wb") as output_stream:
        output_pdf.write(output_stream)
    
    return True

@functions_framework.http
def fill_pdf_form(request):
    """HTTP Cloud Function to fill a PDF template with data and signature.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be converted to a
        response by Flask.
    """
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    request_json = request.get_json(silent=True)

    # Assuming the input is a list containing one object
    if not isinstance(request_json, list) or not request_json:
         return "Invalid input format: Expected a non-empty list.", 400

    try:
        # Use the first item in the list
        data = request_json[0]
        if 'body' not in data:
             return "Invalid input format: Missing 'body' key.", 400
        
        # Extract data
        form_fields = data.get('body', {})
        signature_base64 = form_fields.get("signatureImageBase64", "")
        signature_hash = form_fields.get("signatureDataHash", "N/A")
        signature_date = form_fields.get("signatureDate", datetime.now().strftime('%Y-%m-%d'))
        
        # Validate signature
        if not signature_base64.startswith('data:image/png;base64,'):
            return "Invalid signature format: Expected 'data:image/png;base64,...'", 400

        # Create temporary paths for file processing
        temp_signature_path = "/tmp/signature.png"
        temp_filled_pdf_path = f"/tmp/{OUTPUT_PDF_FILENAME.replace('.pdf', f'_temp_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf')}"
        output_pdf_path = f"/tmp/{OUTPUT_PDF_FILENAME.replace('.pdf', f'_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf')}"

        # Check if template PDF exists
        if not os.path.exists(TEMPLATE_PDF_PATH):
             return f"Error: Template PDF '{TEMPLATE_PDF_PATH}' not found.", 500

        # Verify the PDF is fillable by checking for form fields
        try:
            available_fields = fillpdfs.get_form_fields(TEMPLATE_PDF_PATH)
            if not available_fields:
                return "Error: The template PDF does not appear to be fillable (no form fields found).", 500
            print(f"Available PDF fields: {available_fields}")
        except Exception as e:
            return f"Error: Could not read form fields from PDF: {e}", 500
        
        # Save signature image
        try:
            signature_base64_data = signature_base64.split(',')[1]
            signature_bytes = base64.b64decode(signature_base64_data)
            with open(temp_signature_path, "wb") as f:
                f.write(signature_bytes)
        except Exception as e:
            return f"Error processing signature: {e}", 500
        
        # Prepare form data to fill the PDF
        pdf_form_data = {}
        
        # Process text fields
        for field_name, value in form_fields.items():
            # Skip signature and other special fields
            if field_name in ["signatureImageBase64", "signatureDataHash"] or field_name in CHECKBOX_FIELDS:
                continue
            
            # Map to PDF field name
            if field_name in FIELD_MAPPING:
                pdf_field_name = FIELD_MAPPING[field_name]
                
                # Truncate very long text values to avoid overflow
                max_length = 40  # Maximum characters for most fields
                
                # Special handling for email which tends to be long
                if field_name == "businessEmail" and len(str(value)) > 30:
                    value = str(value)[:30]
                # Special handling for business type which can be long
                elif field_name == "businessType" and len(str(value)) > 35:
                    value = str(value)[:35]
                # General truncation for all other fields
                elif isinstance(value, str) and len(value) > max_length:
                    value = value[:max_length]
                
                pdf_form_data[pdf_field_name] = value
        
        # Process checkboxes
        for checkbox_field in CHECKBOX_FIELDS:
            if checkbox_field in form_fields:
                value = form_fields[checkbox_field]
                field_pair = FIELD_MAPPING.get(checkbox_field)
                if field_pair:
                    # Convert value to boolean
                    if isinstance(value, bool):
                        is_yes = value
                    else:
                        value_lower = str(value).lower()
                        is_yes = value_lower in ["yes", "true", "1", "on", "own"]
                    
                    # Set Yes/No checkboxes
                    yes_field, no_field = field_pair
                    pdf_form_data[yes_field] = "Yes" if is_yes else "Off"
                    pdf_form_data[no_field] = "Yes" if not is_yes else "Off"
        
        # Add the signature date to the form
        if "signatureDate" in FIELD_MAPPING:
            pdf_form_data[FIELD_MAPPING["signatureDate"]] = signature_date
        
        # Process form data
        try:
            # Fill the PDF form
            fillpdfs.write_fillable_pdf(
                TEMPLATE_PDF_PATH,
                temp_filled_pdf_path,
                pdf_form_data,
                flatten=False  # Keep form fields active
            )
            
            # Add signature date and hash to Text_41 if available
            if signature_date or signature_hash:
                text = ""
                if signature_date:
                    text += f"Signed: {signature_date}"
                if signature_hash:
                    if text:
                        text += " | "
                    text += f"Hash: {signature_hash}"
                
                pdf_form_data['Text_41'] = text
                fillpdfs.write_fillable_pdf(
                    temp_filled_pdf_path,
                    temp_filled_pdf_path,
                    {'Text_41': text},
                    flatten=False
                )
            
            # Add signature to the PDF using our custom method
            add_signature_to_pdf(
                temp_filled_pdf_path,
                output_pdf_path,
                temp_signature_path,
                signature_hash,
                signature_date
            )
            print("Signature added to PDF")
        except Exception as e:
            return f"Error filling PDF form: {e}", 500
            
        # Return the final PDF
        try:
            with open(output_pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # Clean up temporary files
            for temp_file in [temp_signature_path, temp_filled_pdf_path, output_pdf_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return pdf_bytes, 200, {
                'Content-Type': 'application/pdf', 
                'Content-Disposition': f'attachment; filename={OUTPUT_PDF_FILENAME}'
            }
        except Exception as e:
            # Clean up temporary files in case of error
            for temp_file in [temp_signature_path, temp_filled_pdf_path, output_pdf_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            return f"Error reading final PDF: {e}", 500
            
    except Exception as e:
        # General error handling
        # Clean up any temp files if they exist
        for temp_file in ['temp_signature_path', 'temp_filled_pdf_path', 'output_pdf_path']:
            if temp_file in locals() and os.path.exists(locals()[temp_file]):
                os.remove(locals()[temp_file])
        return f"An unexpected error occurred: {e}", 500 