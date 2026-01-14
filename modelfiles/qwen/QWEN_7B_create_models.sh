#!/bin/bash

echo "Iniciando creación de modelos QWEN_7B..."

# --- NO_RAG ---
echo "Creando QWEN_7B NO_RAG (T1, T2, T3)..."
ollama create QWEN_7B_LLM_resumen_NO_RAG_T1 -f ./QWEN_7B_LLM_resumir_NO_RAG_T1.txt
ollama create QWEN_7B_LLM_resumen_NO_RAG_T2 -f ./QWEN_7B_LLM_resumir_NO_RAG_T2.txt
ollama create QWEN_7B_LLM_resumen_NO_RAG_T3 -f ./QWEN_7B_LLM_resumir_NO_RAG_T3.txt

# --- RAG ---
echo "Creando QWEN_7B RAG (T1, T2, T3)..."
ollama create QWEN_7B_LLM_resumen_RAG_T1 -f ./QWEN_7B_LLM_resumir_RAG_T1.txt
ollama create QWEN_7B_LLM_resumen_RAG_T2 -f ./QWEN_7B_LLM_resumir_RAG_T2.txt
ollama create QWEN_7B_LLM_resumen_RAG_T3 -f ./QWEN_7B_LLM_resumir_RAG_T3.txt

echo "¡Proceso finalizado! Lista de modelos actuales:"
ollama list | grep QWEN_7B_LLM_resumen