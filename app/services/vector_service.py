# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer
# from services.job_service import get_all_jobs

# # Load embedding model (offline)
# embedding_model = SentenceTransformer(
#     "sentence-transformers/all-MiniLM-L6-v2"
# )

# dimension = 384
# index = faiss.IndexFlatL2(dimension)

# job_ids = []
# job_texts = []


# def build_faiss_index():
#     global job_ids, job_texts

#     jobs = get_all_jobs()

#     job_ids.clear()
#     job_texts.clear()

#     for job in jobs:
#         text = f"""
#         {job['title']}
#         {job['company']}
#         {job['description']}
#         {job['skills']}
#         {job['location']}
#         """
#         job_ids.append(job["id"])
#         job_texts.append(text)

#     embeddings = embedding_model.encode(
#         job_texts,
#         convert_to_numpy=True
#     )

#     index.reset()
#     index.add(embeddings)


# def semantic_search(query: str, top_k: int = 5):
#     query_embedding = embedding_model.encode([query])
#     distances, indices = index.search(
#         np.array(query_embedding),
#         top_k
#     )

#     return [job_ids[i] for i in indices[0]]



def semantic_search(user_message: str):
    """
    Giả lập tìm kiếm vector
    Sau này thay bằng FAISS / Chroma
    """
    if "CNTT" in user_message or "backend" in user_message:
        return [1]
    return []
