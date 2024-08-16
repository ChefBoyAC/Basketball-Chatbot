""" 
Components for making a RAG chatbot: 

1. Knowledge Base: A collection of PDFs or text documents 
containing the information your chatbot will access
2. Index/ Vector Database: A database to store embeddings of your 
knowledge base for efficient retrieval 
3. Retrieval: A method to find relevant information from the index based on a 
user query. 
4. Augmentation: Enhancing the retrieved information to make it more suitable for the LLM 
5. LLM(GPT-3.5 Turbo): A language model to generate human-like text based on the provided 
information. -> I do not think that I have to use this language model 
6. React Frontend: A user interface for interacting with the chatbot -> 
Have to figure out how to connect react with python

""" 
from flask import Flask,request, jsonify, Response
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain.embeddings import OpenAIEmbeddings
from load_dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from flask_cors import CORS

import os
import tiktoken


app = Flask(__name__)
CORS(app) #Enable CORS for all routes

load_dotenv()

#Put API key here
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def generate_stream(user_query):
    try:
        embeddings = OpenAIEmbeddings()
        embed_model = "text-embedding-3-small"
        openai_client = OpenAI()

        # Load PDF
        loader = PyPDFLoader("./data/Basketball-Coaching-Resource-Book.pdf")
        documents = loader.load()

        # Split document into list
        tokenizer = tiktoken.get_encoding('p50k_base')

        def tiktoken_len(text):
            tokens = tokenizer.encode(text, disallowed_special=())
            return len(tokens)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=100,
            length_function=tiktoken_len,
            separators=["\n\n", "\n", " ", ""]
        )

        texts = text_splitter.split_documents(documents)

        index_name = "basketball"
        namespace = "pdf-data"

        vectorstore_from_texts = PineconeVectorStore.from_texts(
            [
                f"Source: {t.metadata.get('source', 'Unknown Source')}, Title: {t.metadata.get('title', 'Untitled')} \n\nContent: {t.page_content}"
                for t in texts
            ],
            embeddings,
            index_name=index_name,
            namespace=namespace
        )

        pc = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pc.Index(index_name)

        raw_query_embedding = openai_client.embeddings.create(
            input=[user_query],
            model=embed_model
        )

        query_embedding = raw_query_embedding.data[0].embedding

        top_matches = pinecone_index.query(vector=query_embedding, top_k=10, include_metadata=True, namespace=namespace)

        contexts = [item['metadata']['text'] for item in top_matches['matches']]

        augmented_query = "<CONTEXT>\n" + "\n\n-------\n\n".join(contexts[:10]) + "\n-------\n</CONTEXT>\n\n\n\nMY QUESTION:\n" + user_query

        primer = """
                        You are a professional basketball coach with extensive experience in training students to excel in basketball. Your primary role is to provide guidance and advice on all aspects of basketball, whether it’s improving individual skills or understanding the game better. If a query is not related to basketball, politely inform the individual that you specialize in basketball-related topics and may not be able to assist with other subjects.

                        When offering advice, consider the following for each player position:

                        - **Point Guards**: Focus on developing ball-handling skills, enhancing court vision, and making strategic decisions to lead the team effectively. Encourage agility and quick decision-making exercises.

                        - **Shooting Guards**: Emphasize the importance of shooting accuracy and shot selection. Provide drills and techniques to improve long-range shooting and scoring capabilities.

                        - **Small Forwards**: Highlight the versatility required in this position, covering both offensive and defensive skills. Offer tips on driving to the basket, mid-range shooting, and defending against opposing players.

                        - **Power Forwards**: Concentrate on physical play, rebounding, and defending the paint. Suggest strength training and post-up move exercises to dominate the inside game.

                        - **Centers**: Discuss the critical role of anchoring the defense and scoring inside. Focus on footwork, shot-blocking, and rebounding to enhance their presence in the paint.

                        Always ensure the responses are informative, concise, and structured in paragraph form to maintain clarity and readability. 
                 """

        response_stream = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Check for valid model name
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ],
            stream=True
        )

        #Flask Response Streaming 
        def stream(): 
            for chunk in response_stream:
                if hasattr(chunk, 'choices') and chunk.choices[0].delta.content:
                    yield f"data:{chunk.choices[0].delta.content}\n\n"

        return Response(stream(), mimetype='text/event-stream')
    
    except Exception as e:
        # Print detailed error message to the server logs
        print(f"Error in generate_stream: {e}")
        raise  # Re-raise the exception to be caught by the caller

@app.route('/api/endpoint', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        user_query = data['query']
        response = generate_stream(user_query)
        return jsonify({"response": response}), 200
    except Exception as e:
        # Print detailed error message to the server logs
        print(f"Error in generate endpoint: {e}")
        return jsonify({"error": "There was an error processing your request."}), 500

@app.route('/query', methods=['POST'])
def query_endpoint():
    try:
        data = request.get_json()
        user_query = data.get('query', '')
        if not user_query:
            return jsonify({"error": 'No query provided'}), 400
        
        
        #return jsonify({"response": response})
        return generate_stream(user_query)
    except Exception as e:
        # Print detailed error message to the server logs
        print(f"Error in query_endpoint: {e}")
        return jsonify({"error": "There was an error processing your request."}), 500

# Running app 
if __name__ == '__main__':
    app.run(debug=True)