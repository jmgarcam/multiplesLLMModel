FROM ollama/ollama:latest

WORKDIR /root/modelfiles

# 1. Copiamos la carpeta mistral completa
COPY modelfiles/mistral ./mistral

# 2. Damos permisos de ejecución al script dentro de mistral
RUN chmod +x ./mistral/run_ollama_mistral.sh

# 3. ENTRYPOINT apunta al script dentro de mistral
ENTRYPOINT ["./mistral/run_ollama_mistral.sh"]
