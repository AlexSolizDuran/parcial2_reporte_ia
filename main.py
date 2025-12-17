import os
import uvicorn
import time
import random
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: Falta GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

class IaRequestDTO(BaseModel):
    prompt: str 

class IaResponseDTO(BaseModel):
    sql: str
    formato: str

DB_SCHEMA = """
Eres un experto SQL para MySQL. Genera la consulta SQL basada en la petición.
Tablas: usuarios, roles, productos, prod_variantes, categorias, marcas, colores, tallas, ventas, detalle_ventas.
REGLA: Devuelve SOLO el SQL limpio. Sin markdown.
"""

def generar_con_modelo(nombre_modelo, prompt):
    print(f"🤖 Intentando con: {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    return model.generate_content(prompt)

@app.post("/generar-sql", response_model=IaResponseDTO) 
async def generar_sql(request: IaRequestDTO):
    # NUEVA LISTA: Priorizamos 1.5-flash que es el más estable y con mayor cupo
    modelos_a_probar = [
        'gemini-1.5-flash',                   # El caballo de batalla (Estable)
        'gemini-1.5-pro',                     # Más potente (Estable)
        'gemini-2.0-flash-lite-preview-02-05', # Opción rápida (Preview)
        'gemini-2.0-flash'                    # Última opción (Suele saturarse)
    ]

    raw_prompt = request.prompt
    user_query = raw_prompt.replace("generar JSON:", "").strip()
    
    formato_salida = "json"
    if "pdf" in user_query.lower(): formato_salida = "pdf"
    elif "excel" in user_query.lower(): formato_salida = "excel"

    gemini_prompt = f"{DB_SCHEMA}\n\nPETICIÓN: \"{user_query}\"\n\nSQL:"

    for modelo in modelos_a_probar:
        try:
            response = generar_con_modelo(modelo, gemini_prompt)
            sql_limpio = response.text.replace("```sql", "").replace("```", "").strip()
            print(f"✅ ÉXITO con {modelo}")
            return IaResponseDTO(sql=sql_limpio, formato=formato_salida)
            
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ Falló {modelo}: {err_msg[:100]}...") # Imprimir solo el inicio del error
            
            # Si el error es de cuota (429), esperamos un poco más antes de seguir
            if "429" in err_msg:
                time.sleep(2) 
            else:
                time.sleep(0.5)

    # Respuesta de emergencia si todo falla
    print("❌ CRÍTICO: Ningún modelo respondió.")
    return IaResponseDTO(
        sql="SELECT * FROM productos LIMIT 10", 
        formato="json"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)