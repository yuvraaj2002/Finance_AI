import streamlit as st
import base64
from io import BytesIO
import os
from openai import OpenAI
import pandas as pd
from llama_parse import LlamaParse
import threading
from dotenv import load_dotenv
load_dotenv()

# Custom CSS for styling Streamlit
st.markdown(
    """
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        .top-margin{ margin-top: 4rem; margin-bottom:2rem; }
        .block-button{ padding: 10px; width: 100%; background-color: #c4fcce; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Setting up the llama cloud API for parsing PDF
os.environ["LLAMA_CLOUD_API_KEY"] = st.secrets["LLAMA_CLOUD_API_KEY"]

def initialize_parser():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    parser = LlamaParse(result_type="markdown", language="en")
    return client, parser

client, parser = initialize_parser()

def extract_key_information(page_content):
    prompt = (
        "You are a helpful assistant that extracts specific information from text. "
        "Extract the following fields if present: ITNS No., TAN, Name, Assessment Year, Financial Year, Amount, "
        "CIN, Date of Deposit, and Challan No. "
        "Present the information in a markdown table format. "
        "If a field is not found, include it in the table with the value 'Not found'. "
        "Use the following markdown table format:\n\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        "| ITNS No. | [Value] |\n"
        "| TAN | [Value] |\n"
        "| Name | [Value] |\n"
        "| Assessment Year | [Value] |\n"
        "| Financial Year | [Value] |\n"
        "| Amount (In Rs.) | [Value] |\n"
        "| CIN | [Value] |\n"
        "| Date of Deposit | [Value] |\n"
        "| Challan No. | [Value] |\n"
    )
    
    full_prompt = f"Analyze the following text and present the extracted information in a markdown table without any additional text or explanations:\n\n{page_content}\n\n{prompt}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # You can change this to a different model if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt},
            ],
        )
    except Exception as e:
        st.error(f"An error occurred while processing the document: {e}")
        return None, None

    key_info_md = response.choices[0].message.content
    lines = key_info_md.strip().split("\n")

    # Initialize dictionary to store column names and values
    extracted_data = {
        "ITNS No.": "Not found",
        "TAN": "Not found",
        "Name": "Not found",
        "Assessment Year": "Not found",
        "Financial Year": "Not found",
        "Amount (In Rs.)": "Not found",
        "CIN": "Not found",
        "Date of Deposit": "Not found",
        "Challan No.": "Not found"
    }

    # Iterate over each line in the markdown table to populate the dictionary
    for line in lines[2:]:  # Skip the header lines
        items = line.split("|")
        field_name = items[1].strip()
        field_value = items[2].strip()
        if field_name in extracted_data:
            extracted_data[field_name] = field_value

    return extracted_data

def parse_pdf_document(file, file_name):
    if isinstance(file, BytesIO):
        try:
            docs = parser.load_data(file, extra_info={"file_name": file_name})
            doc_content = ""
            for doc in docs:
                doc_content += doc.text
            return doc_content
        except Exception as e:
            st.error(f"Error while parsing the file '{file_name}': {e}")
            return None
    else:
        st.error("Invalid file type. Please upload a valid PDF document.")
        return None

def challan_processing():
    upload_tab = st.columns(spec=(1.5, 1), gap="large")[0]  # Adjusted to use only one column for upload
    all_rows = []  # Store rows of data
    pdf_data_list = []  # Store PDF data for reuse in display

    with upload_tab:
        st.title("Challan Processing")
        pdf_uploads = st.file_uploader("Upload the Challan PDFs", type="pdf", accept_multiple_files=True)

        if pdf_uploads:
            st.success("PDFs uploaded successfully")

        if st.button("Process All PDFs", use_container_width=True):
            with st.spinner("Processing all PDFs..."):
                threads = []
                for pdf_upload in pdf_uploads:
                    pdf_data = pdf_upload.read()  # Read PDF content only once
                    pdf_file = BytesIO(pdf_data)
                    file_name = pdf_upload.name
                    pdf_data_list.append((pdf_data, file_name))  # Store data and name for display

                    # Create a thread to process each PDF concurrently
                    def process_pdf(pdf_file, file_name):
                        doc_content = parse_pdf_document(pdf_file, file_name)
                        if doc_content:
                            extracted_data = extract_key_information(doc_content)
                            if extracted_data:
                                all_rows.append(extracted_data)

                    thread = threading.Thread(target=process_pdf, args=(pdf_file, file_name))
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()  # Ensure all threads complete

            if all_rows:
                final_df = pd.DataFrame(all_rows)
                st.dataframe(final_df, use_container_width=True)

    # Removed the display tab for PDFs
