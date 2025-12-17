import os
import uvicorn
import time
import google.genai as genai
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: Falta GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

class IaRequestDTO(BaseModel):
    prompt: str 

class IaResponseDTO(BaseModel):
    sql: str
    formato: str
    columnas: list[str]

# MEJORADO: Esquema de base de datos con ejemplos específicos
DB_SCHEMA = """
Actúa como un experto DBA de MySQL. Genera una consulta SQL exacta y eficiente.

### MAPA DE LA BASE DE DATOS (Trendora)

1. TABLAS PRINCIPALES (Nombres en singular, claves primarias 'id'):
   - usuario (id, nombre, apellido, email, rol_id)
   - rol (id, nombre)  -> [Roles: 'ADMIN', 'CLIENTE', 'VENDEDOR']
   - producto (id, nombre, descripcion, categoria_id, modelo_id)
   - prod_variante (id, sku, stock, precio, costo, producto_id, color_id, talla_id)
     * ESTA ES LA TABLA CLAVE. Une el producto con su inventario.
   
2. TABLAS DE ATRIBUTOS:
   - categoria (id, nombre)
   - marca (id, nombre)
   - modelo (id, nombre, marca_id)
   - color (id, nombre)
   - talla (id, nombre)

3. TABLAS DE VENTAS:
   - venta (id, fecha_venta, monto_total, estado_pedido, cliente_id, vendedor_id)
     * Nota: 'cliente_id' y 'vendedor_id' son FKs hacia la tabla 'usuario'.
   - detalle_venta (id, venta_id, prod_variante_id, cantidad, precio_unitario, subtotal)

VALORES DE EJEMPLO (Para guiar tus filtros):
- Categorías: 'Hombre', 'Mujer', 'Niño', 'Calzado'.
- Marcas: 'Nike', 'Adidas', 'Puma'.
- Colores: 'Rojo', 'Azul', 'Negro'.

### REGLAS DE NEGOCIO PARA SQL:
1. CAMINO DE VENTAS A PRODUCTOS:
   detalle_venta -> prod_variante -> producto
   (Nunca unas detalle_venta directo con producto).

2. PARA FILTRAR POR FECHAS:
   Usa funciones estándar de MySQL: YEAR(v.fecha_venta), MONTH(v.fecha_venta), DATE(v.fecha_venta).

3. PARA "MÁS VENDIDOS":
   SUM(d.cantidad) agrupado por p.nombre.

4. FORMATO:
   Devuelve SOLO el código SQL puro. Sin ```sql, sin explicaciones.
"""

# --- Endpoint para listar los modelos disponibles ---
@app.get("/listar-modelos")
async def listar_modelos_disponibles():
    """
    Endpoint para obtener la lista de modelos disponibles.
    """
    print("\n🔍 Obteniendo la lista de modelos disponibles...")
    try:
        models_response = client.models.list()
        modelos_disponibles = [model.name for model in models_response if 'gemini' in model.name.lower()]
        return {"modelos": modelos_disponibles}
    except Exception as e:
        print(f"❌ ERROR al listar modelos: {str(e)}")
        return {"error": str(e), "modelos": []}

# --- Endpoint de depuración para ver qué SQL se está generando ---
@app.post("/debug-sql")
async def debug_sql(request: IaRequestDTO):
    """
    Endpoint para depurar la generación de SQL.
    """
    raw_prompt = request.prompt
    user_query = raw_prompt.replace("generar JSON:", "").strip()
    
    gemini_prompt = f"{DB_SCHEMA}\n\nPETICIÓN: \"{user_query}\"\n\nSQL:"
    
    modelos_a_probar = [
        'models/gemini-2.5-flash',
        'models/gemini-2.5-pro',
    ]
    
    for modelo in modelos_a_probar:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=gemini_prompt
            )
            sql_generado = response.text.strip()
            
            # Limpiamos el SQL por si acaso viene con marcadores de código
            if sql_generado.startswith("```sql"):
                sql_generado = sql_generado[6:]
            if sql_generado.endswith("```"):
                sql_generado = sql_generado[:-3]
            sql_generado = sql_generado.strip()
            
            return {
                "modelo_usado": modelo,
                "prompt_original": user_query,
                "prompt_completo": gemini_prompt,
                "sql_generado": sql_generado
            }
        except Exception as e:
            print(f"Error con {modelo}: {str(e)}")
            continue
    
    return {"error": "No se pudo generar SQL con ningún modelo"}

# -----------------------------------------------------------------------

def generar_con_modelo(nombre_modelo, prompt):
    print(f"🤖 Intentando con: {nombre_modelo}...")
    try:
        response = client.models.generate_content(
            model=nombre_modelo,
            contents=prompt
        )
        return response
    except Exception as e:
        print(f"Error al generar contenido con {nombre_modelo}: {str(e)}")
        raise

@app.post("/generar-sql", response_model=IaResponseDTO) 
async def generar_sql(request: IaRequestDTO):
    # LISTA ACTUALIZADA con los nombres CORRECTOS de tu API.
    modelos_a_probar = [
        'models/gemini-2.5-flash',      # Última generación, rápido y potente
        'models/gemini-2.5-pro',        # Última generación, el más capaz
        'models/gemini-flash-latest',    # Modelo flash estable y confiable
        'models/gemini-pro-latest',     # Modelo pro estable y confiable
        'models/gemini-2.0-flash',      # Versión anterior de flash, muy rápida
    ]

    raw_prompt = request.prompt
    user_query = raw_prompt.replace("generar JSON:", "").strip()
    
    formato_salida = "json"
    if "pdf" in user_query.lower(): formato_salida = "pdf"
    elif "excel" in user_query.lower(): formato_salida = "excel"

    # MODIFICADO: Usamos el esquema de base de datos mejorado
    gemini_prompt = f"{DB_SCHEMA}\n\nPETICIÓN: \"{user_query}\"\n\nSQL:"

    for modelo in modelos_a_probar:
        try:
            response = generar_con_modelo(modelo, gemini_prompt)
            sql_limpio = response.text.strip()
            
            # Limpiamos el SQL por si acaso viene con marcadores de código
            if sql_limpio.startswith("```sql"):
                sql_limpio = sql_limpio[6:]
            if sql_limpio.endswith("```"):
                sql_limpio = sql_limpio[:-3]
            sql_limpio = sql_limpio.strip()

            print(f"✅ ÉXITO con {modelo}")
            print(sql_limpio,formato_salida)
            
            return IaResponseDTO(sql=sql_limpio, formato=formato_salida, columnas=[])
            
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ Falló {modelo}: {err_msg[:100]}...")
            
            # Si el error es de cuota (429), esperamos más tiempo
            if "429" in err_msg or "quota" in err_msg.lower() or "Resource has been exhausted" in err_msg:
                wait_time = 5
                print(f"Esperando {wait_time} segundos debido a límite de cuota...")
                time.sleep(wait_time)
            else:
                time.sleep(1)

    print("❌ CRÍTICO: Ningún modelo respondió.")
    if "cliente" in user_query.lower():
            fallback_sql = "SELECT u.id, u.nombre, u.apellido, u.email FROM usuario u JOIN rol r ON u.rol_id = r.id WHERE r.nombre = 'ROLE_CLIENTE' LIMIT 10"
    elif "producto" in user_query.lower():
            fallback_sql = "SELECT p.id, p.descripcion FROM producto p LIMIT 10"
    elif "venta" in user_query.lower():
            fallback_sql = "SELECT v.id, v.numero_venta, v.fecha_venta FROM venta v LIMIT 10"
    else:
            fallback_sql = "SELECT * FROM usuario LIMIT 10"
    return IaResponseDTO(
        sql=fallback_sql,
        formato="json",
        columnas=[]
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)