import streamlit as st
import os
import base64
import tempfile
from PyPDF2 import PdfReader
import openai
import json
import pandas as pd
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Financial Statement Validator",
    page_icon="📊",
    layout="wide"
)

# Get OpenAI API key from Streamlit secrets
if "openai_api_key" in st.secrets:
    openai.api_key = st.secrets["openai_api_key"]
else:
    st.warning("OpenAI API key not found in Streamlit secrets. Set it in your app's secrets.")

# Initialize session state
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "response" not in st.session_state:
    st.session_state.response = ""
if "response_history" not in st.session_state:
    st.session_state.response_history = []

# Define question categories
categories = {
    "basic": {
        "name": "Basic Validation",
        "description": "All validation questions",
        "questions": [
            "Is the reconcilation of number of equity shares declared and addressed in notes?",
            "Check if all the Notes mentioned in the Financial Statement have been described cearly in Notes OR has a matching notes section?",
            "First determine if this report follows Division 1 or Division 2 (IND AS) standards? Division 2 (IND AS) applies to any listed company OR any unlisted company with net worth > 250 crores for the last 3 financial years. Refer to https://ca2013.com/section-257-net-worth/ for calculating net worth.",
            "Does the Balance Sheet follow the prescribed format with 'Equity and Liabilities' and 'Assets' as the main sections?",
            "Is the Statement of Profit and Loss presented in the format prescribed by Schedule III Division 1?",
            "Are the figures for both current and previous reporting periods provided in the financial statements?",
            "Is there proper cross-referencing between items on the face of the financial statements and the related information in notes?",
            "Based on the company's turnover, are the figures in financial statements appropriately rounded off?",
            "Is the unit of measurement used for rounding stated and used consistently throughout the financial statements?",
            "Are assets properly classified between current and non-current assets according to the 12-month realization criteria?",
            "Is the share capital section providing details of authorized, issued, subscribed, and fully paid-up shares?",
            "For fixed assets, is there a classification showing land, buildings, plant & equipment, furniture & fixtures, vehicles, and office equipment separately?",
            "Is there a reconciliation of gross and net carrying amounts for each class of fixed assets showing additions, disposals, and adjustments?",
            "Are investments classified as trade investments and other investments with proper sub-classifications?",
            "Are the aggregate amounts of quoted and unquoted investments disclosed along with market value of quoted investments?",
            "Is inventory classified into raw materials, work-in-progress, finished goods, stock-in-trade, stores & spares, loose tools, etc.?",
            "Are receivables classified as secured/unsecured and considered good/doubtful?",
            "Are reserves and surplus properly classified into capital reserves, securities premium, debenture redemption reserve, etc.?",
            "Are long-term borrowings classified according to the required categories (bonds/debentures, term loans, etc.)?",
            "Is the classification of secured and unsecured borrowings provided with nature of security specified?",
            "Are details of default in repayment of loans and interest disclosed?",
            "Has the company disclosed details about dues to Micro, Small, and Medium Enterprises?",
            "Are contingent liabilities classified as claims against the company, guarantees, and other money for which the company is contingently liable?",
            "Is revenue from operations shown with separate disclosure of sale of products, services, and other operating revenues?",
            "Is excise duty shown as a deduction from revenue from operations?",
            "Are finance costs properly classified as interest expense, other borrowing costs, etc.?",
            "For consolidated statements, is profit/loss attributable to minority interest and owners of the parent disclosed?",
            "Is the table with details of net assets, profit/loss share for each entity in the group included?",
            "Are financial assets properly classified and measured at amortized cost, fair value through other comprehensive income, or fair value through profit or loss?",
            "Is there disclosure of valuation techniques and inputs used for fair value measurement?",
            "Is other comprehensive income classified correctly into items that will not be reclassified and items that will be reclassified to profit or loss?",
            "Are nature and extent of risks arising from financial instruments and how these are managed properly disclosed?",
            "Is sensitivity analysis for market risks (currency risk, interest rate risk, price risk) provided?",
            "Are right-of-use assets and lease liabilities properly recognized and presented?",
            "Is revenue from contracts with customers recognized in accordance with Ind AS 115?",
            "Are related party relationships and transactions disclosed in accordance with Ind AS 24?"
        ]
    },
    "advanced": {
        "name": "Advanced Validation",
        "description": "Coming Soon",
        "questions": []
    },
    "deepResearch": {
        "name": "Deep Research",
        "description": "Coming Soon",
        "questions": []
    }
}

def pdf_to_text(uploaded_file):
    """Extract text from PDF file"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name

    text = ""
    try:
        pdf = PdfReader(temp_path)
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
    finally:
        os.unlink(temp_path)  # Clean up temporary file
    
    return text

def analyze_with_openai(pdf_text, question):
    """Send question and PDF text to OpenAI for analysis"""
    if not openai.api_key:
        return "Error: OpenAI API key not configured. Please set it in Streamlit secrets."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial expert analyzing financial statements. Examine the content from the PDF carefully and provide a detailed answer to the question. Also identify if there needs to be any improvement?"
                },
                {
                    "role": "user",
                    "content": f"Analyze this financial statement text and answer this question: {question}\n\nFinancial Statement Content: {pdf_text[:100000]}"
                }
            ],
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: Failed to get response from OpenAI. {str(e)}"

# App Header
st.title("Financial Statement Validator")
st.markdown("Upload a financial statement PDF and validate compliance")

# Main Application Flow
col1, col2 = st.columns([1, 2])

# Sidebar with file upload and category selection
with col1:
    st.subheader("Upload Financial Statement")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Extract and store PDF text
        if "pdf_text" not in st.session_state or st.session_state.uploaded_file != st.session_state.last_uploaded_file:
            with st.spinner("Processing PDF..."):
                st.session_state.pdf_text = pdf_to_text(uploaded_file)
                st.session_state.last_uploaded_file = uploaded_file
                
        # Category selection
        st.subheader("Validation Categories")
        
        for key, category in categories.items():
            if st.button(f"{category['name']}", key=f"btn_{key}", help=category["description"]):
                st.session_state.selected_category = key
                st.session_state.current_question = None
                st.session_state.response = ""
    
    # If category is selected, show questions
    if st.session_state.selected_category and st.session_state.uploaded_file:
        selected_cat = categories[st.session_state.selected_category]
        
        if len(selected_cat["questions"]) > 0:
            st.subheader(f"{selected_cat['name']} Questions")
            for q in selected_cat["questions"]:
                # Truncate question text for the button
                q_short = q[:50] + "..." if len(q) > 50 else q
                if st.button(q_short, key=f"q_{q_short}"):
                    st.session_state.current_question = q
                    with st.spinner("Analyzing with OpenAI..."):
                        st.session_state.response = analyze_with_openai(st.session_state.pdf_text, q)
                        
                        # Add to history if not already there
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        history_entry = {
                            "question": q,
                            "response": st.session_state.response,
                            "timestamp": timestamp
                        }
                        st.session_state.response_history.append(history_entry)
        else:
            st.info(f"{selected_cat['description']}")

# Main content area showing response
with col2:
    if not st.session_state.uploaded_file:
        st.info("👈 Upload a financial statement PDF file to begin validation")
    elif not st.session_state.selected_category:
        st.info("👈 Select a validation category")
    elif not st.session_state.current_question:
        st.info("👈 Select a validation question")
    else:
        st.subheader("Analysis Result")
        
        # Question & Response
        st.markdown("**Question:**")
        st.info(st.session_state.current_question)
        
        st.markdown("**Analysis:**")
        st.write(st.session_state.response)
        
        # Response History
        if len(st.session_state.response_history) > 1:  # More than just the current response
            st.subheader("Previous Analyses")
            
            # Convert history to DataFrame for display
            history_data = []
            for item in st.session_state.response_history:
                if item["question"] != st.session_state.current_question:  # Skip current question
                    q_short = item["question"][:50] + "..." if len(item["question"]) > 50 else item["question"]
                    r_short = item["response"][:100] + "..." if len(item["response"]) > 100 else item["response"]
                    history_data.append({
                        "Timestamp": item["timestamp"],
                        "Question": q_short,
                        "Response": r_short
                    })
            
            if history_data:
                history_df = pd.DataFrame(history_data)
                st.dataframe(history_df, use_container_width=True)

# Footer
st.markdown("---")
st.caption("""
**Note:** This application uses OpenAI's API to analyze financial statements. 
""")
