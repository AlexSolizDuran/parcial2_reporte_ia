import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import re

# Cargar variables de entorno
load_dotenv()

# Configurar API Key
GEMINI_API_KEY = "AIzaSyDWbJYaaSmC2DgbJW6CYKg-TmNsG5lkHyQ"
if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: Falta GEMINI_API_KEY en .env")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- 1. MODELOS ADAPTADOS AL JAVA EXISTENTE ---

# Java envía: {"prompt":String}
class IaRequestDTO(BaseModel):
    prompt: str 

# Java espera: un objeto con métodos .sql() y .formato()
# Por tanto, el JSON debe tener claves "sql" y "formato"
class IaResponseDTO(BaseModel):
    sql: str
    formato: str

# --- 2. CONTEXTO DE BD (Igual que antes) ---
DB_SCHEMA = """
Eres un experto SQL para MySQL. Tu tarea es generar una consulta SQL basada en la petición.
NO expliques nada. Solo devuelve el SQL.

TABLAS:
1. usuarios (id, nombre, email, rol_id)
2. productos (id, nombre, descripcion, precio, categoria_id, marca_id)
3. prod_variantes (id, producto_id, sku, stock, talla_id, color_id)
4. categorias (id, nombre)
5. marcas (id, nombre)
6. colores (id, nombre)
7. tallas (id, nombre)
8. ventas (id, fecha_venta, monto_total, usuario_id)
9. detalle_ventas (id, venta_id, prod_variante_id, cantidad, precio_unitario, subtotal)

REGLAS:
- Devuelve SOLO el código SQL limpio.
- Si piden "formato excel" o "pdf", ignóralo en el SQL, solo genera la consulta de datos.
"""

@app.post("/generar-sql", response_model=IaResponseDTO) 
async def generar_sql(request: IaRequestDTO):
    try:
        print(f"📩 Recibido de Java: {request.prompt}")
        
        # 1. Limpiar el prompt que viene de Java ("generar JSON: dame ventas...")
        raw_prompt = request.prompt
        user_query = raw_prompt.replace("generar JSON:", "").strip()

        # 2. Determinar el formato solicitado (PDF, EXCEL o JSON)
        # Java usa este campo para elegir qué generador usar
        formato_salida = "json" # Default
        if "pdf" in user_query.lower():
            formato_salida = "pdf"
        elif "excel" in user_query.lower():
            formato_salida = "excel"

        # 3. Preguntar a Gemini el SQL
        gemini_prompt = f"""
        {DB_SCHEMA}
        
        PETICIÓN: "{user_query}"
        
        SQL:
        """
        response = model.generate_content(gemini_prompt)
        
        # Limpieza agresiva del SQL (quitar ```sql y saltos de línea extra)
        sql_limpio = response.text.replace("```sql", "").replace("```", "").strip()
        
        # 4. Responder exactamente lo que Java espera
        return IaResponseDTO(
            sql=sql_limpio,
            formato=formato_salida
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        # En caso de error, devolvemos un SQL dummy para que Java no explote
        # O podrías lanzar HTTPException, pero Java espera JSON
        return IaResponseDTO(
            sql="SELECT 1", 
            formato="json"
        )

if __name__ == "__main__":
    # Puerto dinámico para Render o 8001 local
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)