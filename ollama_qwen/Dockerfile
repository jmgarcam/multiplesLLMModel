FROM ollama/ollama:latest

WORKDIR /root/modelfiles

# 1. Copiamos la carpeta qwen completa
COPY modelfiles/qwen ./qwen

# 2. Damos permisos de ejecución al script dentro de qwen
RUN chmod +x ./qwen/run_ollama_qwen.sh

# 3. ENTRYPOINT apunta al script dentro de qwen
ENTRYPOINT ["./qwen/run_ollama_qwen.sh"]
