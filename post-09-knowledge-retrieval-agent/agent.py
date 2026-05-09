# MIT License, Copyright 2025 Packt

import os
import sys
import time
import numpy as np
import faiss
import litellm
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def check_environment():
    """Validate all required environment variables are present and print active model names."""
    required_variables = {
        "LITELLM_BASE_URL": os.getenv("LITELLM_BASE_URL"),
        "MODEL_NAME": os.getenv("MODEL_NAME"),
        "EMBEDDING_MODEL_NAME": os.getenv("EMBEDDING_MODEL_NAME"),
        "LITELLM_API_KEY": os.getenv("LITELLM_API_KEY"),
    }
    missing = [name for name, value in required_variables.items() if not value]
    if missing:
        print("Missing required environment variables:")
        for name in missing:
            print(f"  - {name}")
        print("Please set them in your .env file and try again.")
        sys.exit(1)
    print(f"Active chat model: {required_variables['MODEL_NAME']}")
    print(f"Active embedding model: {required_variables['EMBEDDING_MODEL_NAME']}")
    return {
        "litellm_base_url": required_variables["LITELLM_BASE_URL"],
        "model_name": required_variables["MODEL_NAME"],
        "embedding_model_name": required_variables["EMBEDDING_MODEL_NAME"],
        "litellm_api_key": required_variables["LITELLM_API_KEY"],
        "docs_dir": os.getenv("DOCS_DIR", "docs"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
        "top_k_results": int(os.getenv("TOP_K_RESULTS", "4")),
    }


def load_documents(docs_dir):
    """Read all .txt files from the given directory and return their contents as a list."""
    if not os.path.isdir(docs_dir):
        print(f"Documents directory '{docs_dir}' does not exist. Please create it and add .txt files.")
        sys.exit(1)
    file_paths = [
        os.path.join(docs_dir, filename)
        for filename in os.listdir(docs_dir)
        if filename.endswith(".txt")
    ]
    if not file_paths:
        print(f"No .txt files found in '{docs_dir}'. Please add documents to the knowledge base.")
        sys.exit(1)
    documents = []
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            documents.append(file_handle.read())
    print(f"Loaded {len(documents)} document(s) from '{docs_dir}'.")
    return documents


def chunk_text(text, chunk_size, chunk_overlap):
    """Split text into overlapping character-based chunks of the given size."""
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 2
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end >= text_length:
            break
        start += chunk_size - chunk_overlap
    return chunks


def _embed_with_retry(texts, embedding_model_name, base_url, api_key, operation_label, max_retries=3):
    """Call the LiteLLM proxy embeddings endpoint with exponential backoff on rate limit errors."""
    import httpx
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": embedding_model_name, "input": texts}
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(
                f"{base_url}/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                if attempt < max_retries:
                    wait_seconds = 2 ** attempt
                    print(f"Rate limit reached during {operation_label}. Retrying in {wait_seconds}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait_seconds)
                else:
                    print(f"Rate limit persists during {operation_label} after {max_retries} attempts.")
                    return None
            else:
                print(f"Connection error during {operation_label}. Is LiteLLM running at the configured URL?")
                return None
        except Exception:
            print(f"Connection error during {operation_label}. Is LiteLLM running at the configured URL?")
            return None
    return None


def build_index(chunks, embedding_model_name, base_url, api_key):
    """Embed all chunks and build a FAISS L2 index for similarity search."""
    print("Embedding chunks for the knowledge base...")
    embeddings = _embed_with_retry(
        texts=chunks,
        embedding_model_name=embedding_model_name,
        base_url=base_url,
        api_key=api_key,
        operation_label="index building",
    )
    if embeddings is None:
        print("Failed to build the knowledge base index. Exiting.")
        sys.exit(1)
    embedding_matrix = np.array(embeddings, dtype=np.float32)
    dimension = embedding_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embedding_matrix)
    print(f"Total chunks embedded and indexed: {len(chunks)}")
    return index


def retrieve_chunks(question, index, chunks, embedding_model_name, base_url, api_key, top_k):
    """Embed the question and retrieve the top_k most similar chunks from the index."""
    question_embeddings = _embed_with_retry(
        texts=[question],
        embedding_model_name=embedding_model_name,
        base_url=base_url,
        api_key=api_key,
        operation_label="question retrieval",
    )
    if question_embeddings is None:
        return []
    question_vector = np.array(question_embeddings, dtype=np.float32)
    distances, indices = index.search(question_vector, min(top_k, len(chunks)))
    retrieved = [chunks[idx] for idx in indices[0] if 0 <= idx < len(chunks)]
    return retrieved


def answer_question(question, retrieved_chunks, client, model_name, max_retries=3):
    """Generate an answer strictly from the retrieved document chunks via LiteLLM."""
    if not retrieved_chunks:
        print("I could not find relevant information in the knowledge base for that question.")
        return

    context = "\n\n".join(retrieved_chunks)
    system_prompt = (
        "You are a document assistant. Answer the user's question using only the information "
        "provided below. Do not add any information from your own knowledge. If the answer "
        "is not in the provided text, say so clearly."
    )
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
            )
            answer = response.choices[0].message.content
            print(answer)
            return
        except Exception as error:
            status_code = getattr(error, "status_code", None) or getattr(error, "http_status", None)
            if status_code == 429:
                if attempt < max_retries:
                    wait_seconds = 2 ** attempt
                    print(f"Rate limit reached during answer generation. Retrying in {wait_seconds}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait_seconds)
                else:
                    print("Rate limit persists during answer generation. Please try again later.")
                    return
            else:
                print("Could not reach the chat model. Is LiteLLM running at the configured URL?")
                return


def main():
    """Run the interactive RAG agent loop."""
    config = check_environment()

    client = OpenAI(
        base_url=config["litellm_base_url"],
        api_key=config["litellm_api_key"],
    )

    documents = load_documents(config["docs_dir"])

    all_chunks = []
    for doc_text in documents:
        all_chunks.extend(chunk_text(doc_text, config["chunk_size"], config["chunk_overlap"]))
    print(f"Total chunks created across all documents: {len(all_chunks)}")

    index = build_index(
        chunks=all_chunks,
        embedding_model_name=config["embedding_model_name"],
        base_url=config["litellm_base_url"],
        api_key=config["litellm_api_key"],
    )

    print("\nKnowledge base is ready. Ask a question or type 'exit' to quit.")
    try:
        while True:
            question = input("\nYour question: ").strip()
            if question.lower() == "exit":
                print("Goodbye.")
                break
            if not question:
                print("Please enter a question.")
                continue
            retrieved = retrieve_chunks(
                question=question,
                index=index,
                chunks=all_chunks,
                embedding_model_name=config["embedding_model_name"],
                base_url=config["litellm_base_url"],
                api_key=config["litellm_api_key"],
                top_k=config["top_k_results"],
            )
            answer_question(
                question=question,
                retrieved_chunks=retrieved,
                client=client,
                model_name=config["model_name"],
            )
    except KeyboardInterrupt:
        print("\nGoodbye.")


if __name__ == "__main__":
    main()