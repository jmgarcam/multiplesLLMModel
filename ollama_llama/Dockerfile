FROM ollama/ollama:latest

WORKDIR /root/modelfiles

# 1. Copiamos la carpeta llama completa
COPY modelfiles/llama ./llama

# 2. Damos permisos de ejecución al script dentro de llama
RUN chmod +x ./llama/run_ollama_llama.sh

# 3. ENTRYPOINT apunta al script dentro de llama
ENTRYPOINT ["./llama/run_ollama_llama.sh"]
