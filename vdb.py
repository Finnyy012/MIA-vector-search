import chromadb
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
from sentence_transformers.quantization import quantize_embeddings
import spacy
from tqdm import tqdm

import utils

class VDB:
    def __init__(self):
        self.embedding_model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1", truncate_dim=512)
        self.chroma_client = chromadb.PersistentClient(path="chroma_persist")
        self.collection_name="MIA"
        self.chroma_client.get_or_create_collection(name=self.collection_name)

    def get_embeddings(self, chunks, url, indices, title):
        embeddings = []
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            embeddings.append(self.embedding_model.encode(chunk))
            metadatas.append({"url":url, "chunk_start":indices[i][0], "chunk_end":indices[i][1], "title":title})
            ids.append((f"{i}-{url}"))
        return embeddings, metadatas, ids

    def get_titles(self):
        metadatas = self.chroma_client.get_collection(self.collection_name).get(include = ["metadatas"])["metadatas"]
        titles = set()
        for m in metadatas:
            titles.add(m['title'])
        return sorted(titles)

    def search_as_query(self, query, top_k=5):
        query_vector = self.embedding_model.encode(query, prompt_name="query")
        return self.chroma_client.get_collection(self.collection_name).query(query_embeddings=query_vector, n_results=top_k)

    def search_similarity(self, query, top_k=5):
        query_vector = self.embedding_model.encode(query)
        return self.chroma_client.get_collection(self.collection_name).query(query_embeddings=query_vector, n_results=top_k)

    def upsert_from_url(self, url):
        nlp = spacy.load("en_core_web_sm")
        urls = utils.find_sub_urls(url)
        title = url[url[:-1].rfind('/'):].replace('/', '')

        embeddings = []
        metadatas = []
        ids = []
        for url in (pbar := tqdm(urls)):
            pbar.set_description(f"Embedding pages")
            pagetext = utils.fetch_webpage(url)
            chunks, indices = utils.chunk_text(nlp, pagetext)
            embedding, metadata, id = self.get_embeddings(chunks, url, indices, title)
            embeddings.extend(embedding)
            metadatas.extend(metadata)
            ids.extend(id)

        self.chroma_client.get_collection(self.collection_name).upsert(
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
