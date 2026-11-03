# RAG Frameworks: Harborlight Science Museum

The same two fictional museum documents are searched with three frameworks. Every script uses local `all-MiniLM-L6-v2` embeddings and stops at retrieval, so no LLM or OpenAI call is made.

| Script | Framework | Chunking | Vector store |
|---|---|---|---|
| `01_langchain_museum.py` | LangChain | `RecursiveCharacterTextSplitter`, 150 tokens / 20 overlap (MiniLM tokenizer) | ChromaDB `museum_langchain` |
| `02_llamaindex_museum.py` | LlamaIndex | `SentenceSplitter`, 150 tokens / 20 overlap | ChromaDB `museum_llamaindex` |
| `03_haystack_museum.py` | Haystack | `DocumentSplitter`, 100 words / 15 overlap | `InMemoryDocumentStore` |

## Setup (PyCharm terminal)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

In PyCharm, set the interpreter to `.venv` (Settings → Project → Python Interpreter). The MiniLM model (~90 MB) downloads on the first run.

## Run

```bash
python 01_langchain_museum.py --test                  # all 6 test questions
python 02_llamaindex_museum.py "When does Space Explorers take place?"
python 03_haystack_museum.py                          # interactive prompt
```

Each run rebuilds its collection, so running a script again doesn't add duplicate chunks. Saved outputs from the 6 test questions are in `results/`.

## Results: does a top-2 chunk contain the answer?

| # | Question | LangChain | LlamaIndex | Haystack |
|---|---|---|---|---|
| 1 | Thursday closing time (8:00 PM) | ✅ rank 1 | ✅ rank 1 | ✅ rank 1 |
| 2 | Adult ticket price (18 dollars) | ✅ rank 1 | ❌ | ❌ |
| 3 | Robotics Starter Lab ages (8–12) | ✅ rank 1 | ✅ rank 1 | ✅ rank 1 |
| 4 | Space Explorers timing (first Sunday, 2:00 PM) | ✅ rank 1 | ✅ rank 1 | ✅ rank 1 |
| 5 | Museum cancels a workshop (full refund or free transfer) | ✅ rank 1 | ✅ rank 1 | ✅ rank 1 |
| 6 | Free parking? | no answer exists | no answer exists | no answer exists |

**Why Q2 missed in LlamaIndex and Haystack:** the sentence "General admission for adults … costs 18 dollars" fell at the end of the *opening-hours* chunk. The top match was the following chunk, which lists senior, child, family and student prices but not the adult price. This is a chunk-boundary effect. Larger overlap, or splitting on headings/paragraphs so that "Admission and Tickets" stays together, would fix it.

**Q6 (parking):** all three still returned two chunks with fairly high scores. They matched on "free" and "available" (free Wi-Fi, free wheelchairs, "museum"). Retrieval always returns the nearest *k* chunks, so it can't tell you that no answer exists. You need an LLM that is told to answer only from the context, or a score threshold.

## Comparison

**Which framework felt simplest?** LlamaIndex for the core task. `SimpleDirectoryReader` → `SentenceSplitter` → `VectorStoreIndex` → `as_retriever()` takes few lines, and it records `file_name` metadata automatically. LangChain was close, but you build `Document` objects and metadata by hand. Haystack needed the most code, because every step is an explicit component wired into a pipeline.

**How did the APIs differ?**
- **LangChain:** a toolbox of independent pieces (loader/Document, splitter, embeddings, vector store). You call them in sequence yourself. `similarity_search_with_score` returns a Chroma **distance** (lower is better).
- **LlamaIndex:** index-centric. You configure the embedding model globally through `Settings`, build an index, and ask it for a retriever. It returns `NodeWithScore` objects with a **similarity** score (higher is better).
- **Haystack:** pipeline-centric. You use `add_component` and `connect("a.output", "b.input")`, then `pipeline.run({...})`, and get a dict of outputs. Indexing and querying are separate pipelines. Note that in Haystack 3.x the Sentence-Transformers embedders moved to the separate `sentence-transformers-haystack` package.

**Did all three retrieve useful evidence for the same questions?** Mostly yes. All three found the answer at rank 1 for Q1, Q3, Q4 and Q5. Only LangChain found the adult ticket price (Q2), because of where each splitter cut the text. None of them could signal that Q6 has no answer.

## Notes
- The two `.txt` files in `Documents/` were not supplied in the folder, so they were written to match the PDF's description (fictional data). Parking is intentionally not mentioned.
- The screenshots for submission must be taken by you: run each script with `--test` in PyCharm and capture the Run window. The equivalent text output is in `results/`.
- Optional extension (Haystack Visitor/Workshop routes): not implemented.
