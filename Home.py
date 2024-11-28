import streamlit as st

st.set_page_config(layout="wide")
st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 1.5rem;
                    padding-bottom: 0rem;
                    # padding-left: 2rem;
                    # padding-right:2rem;
                }
                .top-margin{
                    margin-top: 4rem;
                    margin-bottom:2rem;
                }
                .block-button{
                    padding: 10px; 
                    width: 100%;
                    background-color: #c4fcce;
                }
        </style>
        """,
    unsafe_allow_html=True,
)

def app():

    input_tab,image_tab = st.columns(spec=(1.4,1), gap="large")
    with input_tab:
        st.title('Welcome to Our Application!')
        st.write("****")
        st.markdown("""
    <p style="font-size: 1.2rem;">
        Our application offers a suite of powerful modules to simplify and enhance your workflows. 
        The <strong>Challan File Processing</strong> module streamlines the handling of challan files by enabling efficient parsing, validation, and reporting, making financial record management effortless. 
        Meanwhile, the <strong>Chat with Data</strong> module transforms how you interact with information from various sources like WhatsApp, PDFs, and YouTube, using advanced natural language processing to extract insights and facilitate meaningful conversations with your data.
    </p>
    <p style="font-size: 1.2rem;">
        For document and file management, the <strong>Excel File Processing</strong> module provides robust tools for organizing, cleaning, and analyzing spreadsheet data, saving time and reducing manual effort. 
        Additionally, the <strong>NDA Creation</strong> module ensures you can quickly draft professional Non-Disclosure Agreements, tailored to your needs, for safeguarding confidentiality in business or personal contexts. 
        Together, these modules deliver a comprehensive, user-friendly experience designed to optimize productivity and efficiency.
    </p>
""", unsafe_allow_html=True)

app()
