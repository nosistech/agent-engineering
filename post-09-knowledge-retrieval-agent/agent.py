# MIT License, Copyright 2025 Packt

import os
import sys

import faiss
import httpx
import numpy as np
from dotenv import load_dotenv
from openai import APIError, OpenAI

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_config():
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "EMBEDDING_MODEL_NAME", "LITELLM_API_KEY"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        sys.exit(1)

    return {
        "base_url": os.getenv("LITELLM_BASE_URL").rstrip("/"),
        "chat_model": os.getenv("MODEL_NAME"),
        "embedding_model": os.getenv("EMBEDDING_MODEL_NAME"),
        "api_key": os.getenv("LITELLM_API_KEY"),
        "docs_dir": os.getenv("DOCS_DIR", "docs"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
        "top_k": int(os.getenv("TOP_K_RESULTS", "4")),
    }


def load_documents(docs_dir):
    if not os.path.isdir(docs_dir):
        print(f"Documents directory '{docs_dir}' does not exist.")
        sys.exit(1)

    documents = []
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".txt"):
            path = os.path.join(docs_dir, filename)
            with open(path, encoding="utf-8") as file:
                documents.append(file.read())

    if not documents:
        print(f"No .txt files found in '{docs_dir}'.")
        sys.exit(1)

    print(f"Loaded {len(documents)} document(s) from '{docs_dir}'.")
    return documents


def chunk_text(text, chunk_size, chunk_overlap):
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 2

    step = chunk_size - chunk_overlap
    return [text[start:start + chunk_size] for start in range(0, len(text), step)]


def embed_texts(texts, config):
    response = httpx.post(
        f"{config['base_url']}/v1/embeddings",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json={"model": config["embedding_model"], "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    return [item["embedding"] for item in response.json()["data"]]


def build_index(chunks, config):
    print("Embedding chunks for the knowledge base...")
    embeddings = np.array(embed_texts(chunks, config), dtype=np.float32)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    print(f"Total chunks embedded and indexed: {len(chunks)}")
    return index


def retrieve(question, index, chunks, config):
    question_vector = np.array(embed_texts([question], config), dtype=np.float32)
    _, indices = index.search(question_vector, min(config["top_k"], len(chunks)))
    return [chunks[index_id] for index_id in indices[0] if index_id >= 0]


def answer_question(question, context_chunks, client, config):
    context = "\n\n".join(context_chunks)
    messages = [
        {
            "role": "system",
            "content": (
                "Answer using only the provided context. If the answer is not "
                "in the context, say you could not find it in the documents."
            ),
        },
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    response = client.chat.completions.create(
        model=config["chat_model"],
        messages=messages,
        temperature=0,
    )
    print(response.choices[0].message.content.strip())


def main():
    config = load_config()
    print(f"Active chat model: {config['chat_model']}")
    print(f"Active embedding model: {config['embedding_model']}")

    documents = load_documents(config["docs_dir"])
    chunks = []
    for document in documents:
        chunks.extend(chunk_text(document, config["chunk_size"], config["chunk_overlap"]))

    print(f"Total chunks created across all documents: {len(chunks)}")
    index = build_index(chunks, config)
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"], timeout=60)

    print("\nKnowledge base is ready. Ask a question or type 'exit' to quit.")
    while True:
        question = input("\nYour question: ").strip()
        if question.lower() == "exit":
            print("Goodbye.")
            break
        if not question:
            print("Please enter a question.")
            continue
        answer_question(question, retrieve(question, index, chunks, config), client, config)


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, APIError) as error:
        print(f"Model request failed: {error}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nGoodbye.")
