import streamlit as st
import re
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import PineconeHybridSearchRetriever
from pinecone import Pinecone, ServerlessSpec  # Use Pinecone class and ServerlessSpec
from pinecone_text.sparse import BM25Encoder
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_community.document_loaders import PyMuPDFLoader
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile

# For reranking
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Load environment variables
load_dotenv()

# Cache the large components for faster reuse
@st.cache_resource
def load_bm25_encoder():
    return BM25Encoder().default()

@st.cache_resource
def load_pinecone_client():
    return Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

@st.cache_resource
def load_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@st.cache_resource
def load_embedding_model():
    return OpenAIEmbeddings(api_key=os.getenv('OPENAI_API_KEY'))

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

class DataProcessing:

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=250)
        self.bm25 = load_bm25_encoder()

        # Initialize Pinecone client
        self.pinecone_client = load_pinecone_client()

        self.index_name = "rag-finance"
        self.embedding_model = load_embedding_model()

        # Initialize OpenAI client
        self.client = load_openai_client()

        # Check if the index exists before using it
        if self.index_name not in self.pinecone_client.list_indexes().names():
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=1536,
                metric='dotproduct',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
        self.index = self.pinecone_client.Index(self.index_name)

        # Initialize the reranker and retriever
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=4)
        self.retriever = None

    def initialize_compression_retriever(self):
        """Initialize compression retriever using the base retriever"""
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor, base_retriever=self.retriever
        )

    def get_youtube_id(self, url):
        """Extract YouTube video ID from URL"""
        regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        match = re.match(regex, url)
        return match.group(6) if match else None

    def process_youtube(self, youtube_id, corpus):
        """Process YouTube transcript and add it to corpus"""
        try:
            result = YouTubeTranscriptApi.get_transcript(youtube_id)
            yt_captions = " ".join(item['text'] for item in result)
            chunks = self.splitter.create_documents([yt_captions])
            for chunk in chunks:
                corpus.append(chunk.page_content)
        except (YouTubeTranscriptApi.TranscriptsDisabled, YouTubeTranscriptApi.NoTranscriptFound):
            st.error("Transcript is disabled or not found for this video.")

    def process_pdf(self, pdf_file, corpus):
        """Process PDF file and add text chunks to corpus"""
        if pdf_file is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(pdf_file.getvalue())
                    tmp_file_path = tmp_file.name

                loader = PyMuPDFLoader(tmp_file_path)
                data = loader.load()
                os.unlink(tmp_file_path)

                content = "".join(doc.page_content for doc in data)
                chunks = self.splitter.create_documents([content])
                for chunk in chunks:
                    corpus.append(chunk.page_content)
            except Exception as e:
                st.error(f"An error occurred while processing the PDF: {str(e)}")

    def process_whatsapp(self, text, corpus):
        """Process WhatsApp text conversation and add it to corpus"""
        pattern = r"(?<=^\d{2}/\d{2}/\d{2}), \d{1,2}:\d{2}(?:\u202f)?(?:am|pm) -"
        processed_lines = [
            re.sub(pattern, '', line).strip()
            for line in text.splitlines()
            if '<Media omitted>' not in line and line.strip()
        ]
        complete_text = "\n".join(processed_lines)
        chunks = self.splitter.create_documents([complete_text])
        for chunk in chunks:
            corpus.append(chunk.page_content)

    def improve_query(self, user_query):
        """
        This function takes a user's raw query in Hinglish (Hindi + English) and improves it to make it clearer, more detailed, and optimal for document retrieval systems.
        It uses the OpenAI API to generate a response based on the context and query, refining the query by adding clarity, removing ambiguity, and adding any missing context.
        The intent of the question remains the same while enhancing its clarity.

        Args:
            user_query (str): The user's raw query in Hinglish (Hindi + English).

        Returns:
            str: The optimized query for document retrieval systems.
        """

        # Define the prompt template with Hinglish support and date rephrasing instructions
        prompt_template = f"""
        ### Task Description:
        You are an assistant that specializes in improving user questions to make them clearer, more detailed, and optimal for document retrieval systems. 
        You will be provided with a user's raw query in Hinglish (Hindi + English). Your task is to rephrase the query by making it more specific, removing ambiguity, and adding any missing context that can help the system provide the best possible answer. 
        Make sure the intent of the question remains the same while enhancing its clarity.

        ### Instructions:
        1. Take the user's raw query, which may be in Hinglish (Hindi + English).
        2. If the query is vague, refine it by adding clarity and ensuring all parts of the question are meaningful.
        3. Make the query as specific as possible without changing the original intent.
        4. If necessary, add any additional context that could assist the retrieval system in providing the best response.
        5. If the query asks to summarize the discussion about a specific date, rephrase the date in the format DD/MM/YY. For example, "28 June, 2024" should become "28/06/24".

        ### Input:
        User's Raw Query: "{user_query}"

        ### Output:
        Query:
        """

        # Call the OpenAI API to generate the response based on context and query
        response = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Replace this with the actual model if needed
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt_template}
                    ],
                    temperature=0.7,
                    top_p=1,
                    n=1
                )
        
        # Extract the optimized query from the response
        optimized_query = response.choices[0].message.content.strip()
        return optimized_query

    def generate_response(self, context_data, query):
        """
        Generate a prompt for the GPT-4-mini model to provide a clear, accurate, and well-structured response
        based on the query and the given context data, with a heading "AI Response:".

        Args:
            context_data (str): The context data that serves as input for the model.
            query (str): The specific query provided by the user.

        Returns:
            str: The generated response from GPT-4-mini.
        """

        # Create a prompt that instructs the AI to respond with a heading "AI Response:" before the actual output
        prompt_template = f"""
        You are an intelligent assistant (GPT-4-mini) tasked with providing a detailed, accurate, and concise response
        based on the following context and query:

        Context:
        \"{context_data}\"

        Query:
        \"{query}\"

        Guidelines:
        1. Begin your response with the heading: **AI Response:**
        2. Carefully analyze both the context and the query to generate a comprehensive and relevant response.
        3. Ensure that the response is well-structured, uses clear language, and is factually accurate.
        4. If the context or query is unclear or ambiguous, politely ask the user for clarification or to rephrase the question.

        Example response formats:
        - "AI Response: Based on the context provided and your query, here is the relevant information..."
        - "AI Response: The context and query provided are unclear. Could you please rephrase the question or provide more specific information?"

        Please provide your response below.
        """

        try:
            # Call the OpenAI API to generate the response based on context and query
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Replace this with the actual model if needed
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt_template}
                ],
                temperature=0.7,
                top_p=1,
                n=1
            )

            # Extract the generated response text
            generated_response = response.choices[0].message.content.strip()
            return generated_response

        except Exception as e:
            return f"An error occurred while generating the response: {str(e)}"


def chat_with_docs():
    dp_obj = DataProcessing()
    corpus = []

    st.title("Chat with your Data")
    st.write("**********")
    pdf_tab, whatsapp_tab, youtube_tab = st.columns(spec=(1,1,1), gap="large")

    with pdf_tab:
        pdf_upload = st.file_uploader("Choose a PDF file", type="pdf")
        if pdf_upload:
            with st.spinner("Processing PDF..."):
                dp_obj.process_pdf(pdf_upload, corpus)
            st.success("PDF document uploaded and setup")

    with whatsapp_tab:
        chat_upload = st.file_uploader("Upload the WhatsApp chat text file", type="txt")
        if chat_upload:
            raw_text = chat_upload.read().decode("utf-8")
            dp_obj.process_whatsapp(raw_text, corpus)
            st.success("WhatsApp chat uploaded and setup")

    with youtube_tab:
        youtube_link = st.text_input("Enter a YouTube Link")
        youtube_id = dp_obj.get_youtube_id(youtube_link)
        if youtube_id:
            with st.spinner("Processing YouTube transcript..."):
                dp_obj.process_youtube(youtube_id, corpus)
            st.success("YouTube transcript uploaded and setup")

    if corpus:
        with st.spinner("Fitting BM25 and initializing retrievers..."):
            dp_obj.bm25.fit(corpus)
            dp_obj.retriever = PineconeHybridSearchRetriever(
                embeddings=dp_obj.embedding_model,
                sparse_encoder=dp_obj.bm25,
                index=dp_obj.index,
                top_k=5
            )
            dp_obj.initialize_compression_retriever()

        query_input = st.chat_input("Ask your query")
        if query_input:
            improved_query = dp_obj.improve_query(query_input)
            st.chat_message("user").write(f"Original Query: {query_input}")
            st.chat_message("assistant").write(f"Improved Query: {improved_query}")
            sparse_vector = dp_obj.bm25.encode_queries([improved_query])

            if not sparse_vector[0]:
                st.warning("Empty sparse vector. Try a different query.")
            else:
                compressed_docs = dp_obj.compression_retriever.invoke(improved_query)
                context_data = "".join(doc.page_content for doc in compressed_docs)
                with st.spinner("Retrieving context data, processing and generating... This may take a few more seconds..."):
                        response = dp_obj.generate_response(context_data, improved_query)
                st.chat_message("assistant").write(response)
    else:
        st.warning("No documents processed. Please upload or enter content to process.")


chat_with_docs()
