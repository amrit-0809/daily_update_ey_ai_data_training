
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


# Project directory
PROJECT_DIR = Path(__file__).resolve().parent

CHROMA_DIR = PROJECT_DIR / "chroma_db"

COLLECTION_NAME = "company_documents"


# Load embedding model
print("Loading embedding model for retrieval...")

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# Connect to persistent ChromaDB
chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)


# Search function
def search_chunks(question, top_k=3):

    # Generate question embedding
    question_embedding = embedding_model.encode(
        [question]
    ).tolist()

    # Search ChromaDB
    results = collection.query(
        query_embeddings=question_embedding,
        n_results=min(top_k, collection.count()),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    matches = []

    for i, text in enumerate(results["documents"][0]):

        matches.append({

            "id": results["ids"][0][i],

            "text": text,

            "source": results["metadatas"][0][i]["source"],

            "distance": results["distances"][0][i]

        })

    return matches

