import chromadb
from chromadb.config import Settings

# --- CONFIGURACIÓN ---
CHROMADB_HOST = "localhost"
CHROMADB_PORT = 8001

def ver_colecciones_remotas():
    print(f"📡 Conectando a ChromaDB en http://{CHROMADB_HOST}:{CHROMADB_PORT}...")
    
    try:
        # Usamos HttpClient para conectar al servidor
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        
        # Obtener latido para verificar conexión
        print(f"💓 Heartbeat: {client.heartbeat()} ms")
        
        # Listar colecciones
        collections = client.list_collections()
        
        if not collections:
            print("⚠️ Conexión exitosa, pero NO hay colecciones creadas.")
            return

        print(f"\n✅ Se encontraron {len(collections)} colecciones:\n")
        print("=" * 60)
        
        for i, col in enumerate(collections, 1):
            # Recuperamos la colección por nombre para obtener el conteo actualizado
            # (A veces el objeto de la lista no trae el count fresco)
            actual_col = client.get_collection(col.name)
            count = actual_col.count()
            
            print(f"📂 COLECCIÓN #{i}")
            print(f"   Nombre:   {col.name}")
            print(f"   ID:       {col.id}")
            print(f"   Docs:     {count}")
            print(f"   Metadata: {col.metadata}")
            print("-" * 60)

    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        print("Verifica que el contenedor/servicio de Chroma esté corriendo en el puerto 8001.")

if __name__ == "__main__":
    ver_colecciones_remotas()