# app_qdrant.py
import os
import re
import uvicorn
import pathlib
from typing import List
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from sentence_transformers import SentenceTransformer
import numpy as np

from symspellpy.symspellpy import SymSpell, Verbosity
from rapidfuzz import fuzz
import markdown
from bs4 import BeautifulSoup

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, SearchParams

DOCS_DIR = os.environ.get("DOCS_DIR", "./docs")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "docs_collection"

EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384

app = FastAPI()
model = None
sym_spell = None
qdrant: QdrantClient | None = None

class SearchResult(BaseModel):
    title: str
    link: str

def extract_title_and_text(md_text: str, filename: str):
    html = markdown.markdown(md_text)
    soup = BeautifulSoup(html, features="html.parser")
    h1 = soup.find("h1")
    title = h1.get_text().strip() if h1 else pathlib.Path(filename).stem
    text = soup.get_text(separator=" ", strip=True)
    return title, text

def updload_to_quadrant(docs):
    if docs:
        texts = [d["title"] + "\n" + d["text"] for d in docs]
        embeddings = model.encode(texts, convert_to_numpy=True).astype("float32")

        points = [
            PointStruct(
                id=d["id"],
                vector=embeddings[i].tolist(),
                payload={
                    "title": d["title"],
                    "link": d["link"],
                    "text": d["text"]
                }
            )
            for i, d in enumerate(docs)
        ]
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)

def build_symspell(docs):
    global sym_spell
    max_edit_distance = 2
    prefix_len = 7
    sym_spell = sym_spell or SymSpell(max_edit_distance, prefix_len)
    freq = {}
    token_re = re.compile(r"[a-zA-Z0-9\-']+")

    for d in docs:
        for w in token_re.findall(d["text"].lower()):
            freq[w] = freq.get(w, 0) + 1

    for w, f in freq.items():
        sym_spell.create_dictionary_entry(w, f)

def load_markdown_docs(docs_dir: str):
    docs = []
    count = 0
    for root, _dirs, files in os.walk(docs_dir):
            for f in files:
                if f.endswith(".md"):
                    # limit amount of uploaded documents - for testing, debugging
                    # if (count > 1000):
                    #     break
                    p = os.path.join(root, f)
                    with open(p, "r", encoding="utf-8") as fh:
                        try:
                            md = fh.read()
                        except:
                            print(f"FAILED to load: \"file\": {f}")
                            continue
                    title, text = extract_title_and_text(md[:5000], f)
                    rel = os.path.relpath(p, docs_dir).replace(os.sep, "/")
                    link = f"/docs/{rel}"
                    docs.append({"id": count, "title": title, "text": text, "link": link})
                    if count % 50 == 0:
                        build_symspell(docs)
                        updload_to_quadrant(docs)
                        docs.clear()
                    count += 1
    return docs

def symspell_suggestions(query: str):
    suggestions = [query]
    if not sym_spell:
        print("SymSpell is not active!")
        return suggestions
    res = sym_spell.lookup(query, Verbosity.CLOSEST, max_edit_distance=2)
    for r in res[:5]:
        suggestions.append(r.term)
    tokens = re.findall(r"[a-zA-Z0-9\-']+", query)
    for t in tokens:
        res = sym_spell.lookup(t, Verbosity.CLOSEST, max_edit_distance=2)
        for r in res[:3]:
            new_q = re.sub(re.escape(t), r.term, query)
            suggestions.append(new_q)
    return list(dict.fromkeys(suggestions))

@app.on_event("startup")
def startup():
    global model, qdrant, sym_spell

    model = SentenceTransformer(EMBED_MODEL)
    qdrant = QdrantClient(url=QDRANT_URL)

    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE)
    )

    docs = load_markdown_docs(DOCS_DIR)

def search_qdrant(query: str):

    q_emb = model.encode([query], convert_to_numpy=True).astype("float32")[0]

    return qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=q_emb.tolist(),
        limit=5,
        search_params=SearchParams(hnsw_ef=32)
    )

@app.get("/search", response_model=List[SearchResult])
def search(q: str = Query(...), top: int = 10):
    query = q.strip()
    if not query:
        return []

    candidates = symspell_suggestions(query)
    print(f"query={query}, candidates={candidates}")
    scored = {}
    for cand in candidates:
        hits = search_qdrant(cand)
        for h in hits.points:
            p = h.payload
            title_ratio = fuzz.token_sort_ratio(cand, p["title"])
            text_ratio = fuzz.partial_ratio(cand, p["text"])
            combined = float(h.score) * 0.6 + (title_ratio / 100) * 0.25 + (text_ratio / 100) * 0.15

            key = p["link"]
            if key not in scored or scored[key]["score"] < combined:
                scored[key] = {"title": p["title"], "link": p["link"], "score": combined}

    return [
        SearchResult(title=v["title"], link=v["link"])
        for v in sorted(scored.values(), key=lambda x: x["score"], reverse=True)[:top]
    ]

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())

from fastapi.staticfiles import StaticFiles
if os.path.exists(DOCS_DIR):
    app.mount("/docs", StaticFiles(directory=DOCS_DIR), name="docs")

if __name__ == "__main__":
    uvicorn.run("app_qdrant:app", host="0.0.0.0", port=8000)
