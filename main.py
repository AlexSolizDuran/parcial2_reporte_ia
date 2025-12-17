import os
import uvicorn
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: Falta GEMINI_API_KEY en .env")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

class IaRequestDTO(BaseModel):
    prompt: str 

class IaResponseDTO(BaseModel):
    sql: str
    formato: str

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

def generar_con_modelo(nombre_modelo, prompt):
    """Intenta generar contenido con un modelo específico"""
    print(f"🤖 Probando con modelo: {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    return model.generate_content(prompt)

@app.post("/generar-sql", response_model=IaResponseDTO) 
async def generar_sql(request: IaRequestDTO):
    # Lista de modelos a probar en orden de prioridad
    # Si falla el primero, prueba el segundo
    modelos_a_probar = [
        'gemini-2.0-flash-lite-preview-02-05', # Opción 1: Lite (rápido y barato)
        'gemini-2.0-flash-exp',               # Opción 2: Experimental
        'gemini-2.0-flash'                    # Opción 3: Estándar
    ]

    raw_prompt = request.prompt
    user_query = raw_prompt.replace("generar JSON:", "").strip()
    
    formato_salida = "json"
    if "pdf" in user_query.lower(): formato_salida = "pdf"
    elif "excel" in user_query.lower(): formato_salida = "excel"

    gemini_prompt = f"{DB_SCHEMA}\n\nPETICIÓN: \"{user_query}\"\n\nSQL:"

    last_error = None

    for modelo in modelos_a_probar:
        try:
            response = generar_con_modelo(modelo, gemini_prompt)
            sql_limpio = response.text.replace("```sql", "").replace("```", "").strip()
            print(f"✅ SQL Generado con {modelo}")
            
            return IaResponseDTO(sql=sql_limpio, formato=formato_salida)
            
        except Exception as e:
            print(f"⚠️ Falló {modelo}: {e}")
            last_error = e
            time.sleep(1) # Esperar un poco antes de reintentar con el siguiente

    # Si todos fallan
    print("❌ Todos los modelos fallaron.")
    return IaResponseDTO(
        sql="SELECT * FROM productos LIMIT 1", # SQL Dummy de emergencia
        formato="json"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)