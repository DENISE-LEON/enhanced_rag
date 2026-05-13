class Rag:
    #imports:
    import os
    from dotenv import load_dotenv
    from langchain_community.document_loaders import DirectoryLoader,TextLoader, CSVLoader, PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import Chroma
    from langchain.chains import RetrievalQA
 
 #api key 
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    #load docs 
    loaders = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".csv": CSVLoader
}


