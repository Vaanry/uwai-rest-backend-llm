import os
import faiss
import numpy as np
from langchain.text_splitter import (
    CharacterTextSplitter
)
from langchain_openai import OpenAIEmbeddings

faiss_index = faiss.read_index(os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu_faiss_index.bin"))
menu_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu.txt")

embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
)

with open(menu_file, encoding='utf8') as f:
    menu_doc = f.read()


splitter = CharacterTextSplitter(
    separator="|",
    chunk_size=50,
    chunk_overlap=0, 
    length_function=len, 
    is_separator_regex=False,
)

split_menu = splitter.split_text(menu_doc)


def get_dish(query):
    query_embedding = embeddings_model.embed_query(query)

    _, I = faiss_index.search(np.array([query_embedding], dtype=np.float32), k=2)
    
    result = "\n\n".join([split_menu[idx] for idx in I[0] if idx != -1])
    print(result) #  для дебага
    return result
