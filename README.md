# controlled-news-generation-es

Official implementation for generating synthetic Spanish news to aid AI detection research. This Dockerized pipeline orchestrates Mistral 7B and ChromaDB to produce text under controlled RAG vs. No-RAG conditions. Features automated RSS ingestion, vector embedding, and variable temperature settings for robust dataset reproduction.

---

## Generation methodology

The core purpose of this software is to generate a dataset of synthetic news to aid in the detection of artificial content. The pipeline consists of three main stages:

### 1. Data Acquisition
The process begins with an automated data engine that continuously monitors and ingests real news from a curated list of RSS feeds.
* **Processing:** The system extracts the raw content, sanitizes HTML tags, and normalizes the text.
* **Storage:** These real articles are stored in a NoSQL Database (MongoDB). They serve two critical roles: acting as the source "ground truth" (headlines/descriptions) for generation prompts and populating the vector knowledge base.

### 2. Contextual strategies
The generation engine explores two distinct architectural approaches:
* **NO-RAG (Baseline):** The LLM generates text relying solely on the input headline and its pre-trained internal knowledge, without external access to the article body.
* **RAG (Retrieval-Augmented Generation):** The system queries a Chroma Vector database to retrieve relevant context from the previously ingested real news. This semantic context is injected into the prompt to guide the generation.

### 3. Temperature variations
To analyze the effect of stochastic parameters on text characteristics, the Modelfiles are configured with three distinct temperature levels:
* **T3 (Low [t=0.5]):** Precision and determinism.
* **T2 (Medium [t=0.75]):** Balance between coherence and creativity.
* **T1 (High [t=1]):** High variability and diversity.

**Model used:** Mistral 7B Instruct (via Ollama).

---

## Installation and usage

### Prerequisites
* Docker & Docker Compose
* Python 3.x (for local script execution)
* Ollama (installed locally or accessible via API)
* `.env.test` configuration file

### Quick start

1.  **Initialize network**
    Create the dedicated Docker network:
    ```bash
    ./create_network.sh .env.test
    ```

2.  **Deploy services**
     **Configuration required:** Before deploying, perform the following setups:
    * **Credentials:** Update the `login.txt` files (located in `data_engine/` and `context_manager/`) with your MongoDB credentials. Ensure these credentials also match the environment variables defined in `docker-compose.yml`.
    * **RSS Sources:** Populate `data_engine/rss_newspaper.txt`** with the target newspapers and their RSS feeds using the format `newspaper_name:rss_url` (one entry per line).

    Build and start the container ecosystem (NoRelational DB, Vector DB, Data Engine, LLM API):
    ```bash
    docker compose up -d
    ```

3.  **Create vector database**
    Execute the embedding script to ingest news from the raw database and populate the Chroma Vector database.
    
    **Configuration required:** Before running, open `embeddings/generate_embeddings.py` and configure the following variables:
    * **`IP_API`**: Set this to the IP address where the real news API (`data_engine`) is running.
    * **`start_date`** / **`end_date`**: Define the training window for the RAG knowledge base.

    ```python
    # embeddings/generate_embeddings.py
    IP_API = "localhost"
    start_date = "..."
    end_date = "..."
    ```

    Then run the ingestion script:
    ```bash
    python embeddings/generate_embeddings.py
    ```

4.  **Launch LLMs**
    Register the custom model configurations in Ollama using the provided modelfiles. Execute the following for each experimental condition (T1, T2, T3):

    ```bash
    # Example for NO-RAG T1
    ollama create LLM_resumir_NO_RAG_T1 -f modelfiles/LLM_resumir_NO_RAG_T1.txt

    # Example for RAG T1
    ollama create LLM_resumir_RAG_T1 -f modelfiles/LLM_resumir_RAG_T1.txt
    ```
    *Repeat for T2 and T3 variants.*

5.  **Run generation pipeline**
    **Configuration required:** Open `text_generator/news_generator.py` and configure the network connectivity and simulation timeframe:
    
    * **Service IPs:** Update **`API_IP`** (Real News), **`CHROMADB_IP`** (Vector DB), **`OLLAMA_IP`** (LLM Service), and **`LLM_API_IP`** (Synthetic News API).
    * **Timeframe:** Set the start/end dates and hours.

    ```python
    # text_generator/news_generator.py
    
    # --- Network Configuration ---
    API_IP = "localhost"
    CHROMADB_IP = "localhost"
    OLLAMA_IP = "localhost"
    LLM_API_IP = "localhost"

    # --- Timeframe Configuration ---
    year = 2026
    start_month = 1
    # ... (set end_month, days, and hours)
    ```

    Start the orchestration engine:
    ```bash
    python text_generator/news_generator.py
    ```

---

## Project structure

```text
.
├── context_manager/          
│   ├── login.txt             # User and password of No relational database
│   ├── api_llm_news.py       # API for managing prompt context and history
│   └── Dockerfile            
├── data_engine/              # Real news acquisition & storage
│   ├── api_data_engine.py    # Synthetic news storage and retrieval
│   ├── engine.py             # RSS scraping and MongoDB storage
│   ├── login.txt             # User and password of No relational database
│   ├── run.sh                # Launches ingestion and API services
│   ├── rss_newspaper.txt     # List of rss newspaper url
│   └── Dockerfile  
├── embeddings/               # Vectorization logic (Chroma DB interaction)
│   └── generate_embeddings   # Populate Chroma vector database
├── modelfiles/               # Ollama configuration files for Mistral 7B
│   ├── LLM_resumir_NO_RAG_T[1-3].txt
│   └── LLM_resumir_RAG_T[1-3].txt
├── norelational_db/          # MongoDB Docker configuration 
├── text_generator/           # Main generation pipeline
│   ├── news_generator.py     # Synthetic data generation engine
│   └── ollama_execution.py   # LLM prompt execution wrapper
├── vector_db/                # Chroma DB Docker configuration
├── docker-compose.yml        # Service orchestration
├── create_network.sh         # Network setup script
```
