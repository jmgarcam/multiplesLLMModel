FROM ollama/ollama:0.1.25

WORKDIR /root/modelfiles

# 1. Copiamos la carpeta qwen completa
COPY modelfiles/gema ./gema

# 2. Damos permisos de ejecución al script dentro de qwen
RUN chmod +x ./gema/run_ollama_gema.sh

# 3. ENTRYPOINT apunta al script dentro de qwen
ENTRYPOINT ["./gema/run_ollama_gema.sh"]