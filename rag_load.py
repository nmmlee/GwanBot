import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

def load_rag():
    model = SentenceTransformer("EmbeddingModelFinetuning")

    # 현재 rag_load.py가 있는 디렉토리
    base_dir = os.path.dirname(__file__) 
    index_path = os.path.join(base_dir, "rag_index.faiss")
    metadata_path = os.path.join(base_dir, "rag_metadata.pkl")

    # 벡터 DB 
    index = faiss.read_index(index_path)
    with open(metadata_path, "rb") as f:
        documents, metadatas = pickle.load(f)

    return model, index, documents, metadatas