import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar API Key
GEMINI_API_KEY = "AIzaSyDWbJYaaSmC2DgbJW6CYKg-TmNsG5lkHyQ"
if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: Falta GEMINI_API_KEY en .env")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- MODELOS DE DATOS (IGUAL QUE EN JAVA) ---
class IaRequestDTO(BaseModel):
    tipoReporte: str
    datos: Any
    instrucciones: Optional[str] = None

class IaResponseDTO(BaseModel):
    analisis: str
    recomendaciones: Optional[str] = ""

# --- CONTEXTO DE LA BASE DE DATOS (EL SCRIPT RESUMIDO) ---
DB_SCHEMA = """
Estás actuando como un generador de SQL experto para una base de datos MySQL de una tienda de ropa (Trendora).
Tu única tarea es convertir la petición del usuario en una consulta SQL válida.

ESQUEMA DE LA BASE DE DATOS (Tablas y Columnas Clave):

1. usuarios (id, nombre, email, rol_id)
   - Roles: 1=ADMIN, 2=CLIENTE, 3=VENDEDOR
2. roles (id, nombre)
3. productos (id, nombre, descripcion, precio, categoria_id, marca_id, modelo_id, material_id)
4. prod_variantes (id, producto_id, sku, precio, stock, color_id, talla_id)
   - Esta tabla tiene el stock real. Un producto padre tiene muchas variantes.
5. categorias (id, nombre)
6. marcas (id, nombre)
7. colores (id, nombre, codigo_hex)
8. tallas (id, nombre)
9. ventas (id, fecha_venta, monto_total, usuario_id, estado_pedido)
10. detalle_ventas (id, venta_id, prod_variante_id, cantidad, precio_unitario, subtotal)

RELACIONES IMPORTANTES:
- Una venta tiene muchos detalles.
- Un detalle de venta apunta a una 'prod_variante', NO directamente a 'productos'.
- Para saber el nombre del producto vendido: detalle_ventas -> prod_variantes -> productos -> nombre.
- Para saber el color vendido: detalle_ventas -> prod_variantes -> colores.

REGLAS:
1. Genera SOLO el código SQL. No uses bloques de código markdown (```sql). Solo texto plano.
2. Si la petición es ambigua, asume las columnas más lógicas (ej. 'ventas por mes' usa fecha_venta).
3. Usa JOINs explícitos.
4. No pongas explicaciones antes ni después del SQL.
"""

@app.post("/generar-sql") 
async def generar_sql(request: IaRequestDTO):
    try:
        # Usamos 'instrucciones' como la query del usuario, o 'tipoReporte' si instrucciones está vacío
        user_query = request.instrucciones if request.instrucciones else request.tipoReporte
        
        print(f"recibiendo petición SQL para: {user_query}")

        prompt = f"""
        {DB_SCHEMA}
        
        PETICIÓN DEL USUARIO: "{user_query}"
        
        SQL:
        """

        response = model.generate_content(prompt)
        sql_query = response.text.replace("```sql", "").replace("```", "").strip()

        return IaResponseDTO(
            analisis=sql_query,  # Aquí devolvemos el SQL generado
            recomendaciones="Consulta generada por IA basada en el esquema de Trendora."
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)