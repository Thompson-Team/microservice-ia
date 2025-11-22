from fastapi import FastAPI
from pydantic import BaseModel
import openai
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Creacion la app usando fastAPI
app = FastAPI()

class UserInput(BaseModel):
    text: str
    wallet: str

#Manejo del json 
def limpiar_json(texto):
    """
    Limpia la respuesta de OpenAI para extraer JSON válido
    """
    # Remover markdown code blocks si existen
    texto = re.sub(r'```json\n?', '', texto)
    texto = re.sub(r'```\n?', '', texto)
    
    # Remover espacios en blanco al inicio/final
    texto = texto.strip()
    
    # Si hay múltiples líneas, intentar extraer el JSON
    if '\n' in texto:
        # Buscar la primera { y la última }
        inicio = texto.find('{')
        fin = texto.rfind('}')
        if inicio != -1 and fin != -1:
            texto = texto[inicio:fin+1]
    
    return texto

# Endpoint para el análisis
@app.post("/analyze")
async def analyze(input: UserInput):
    prompt = f"""Analiza el siguiente texto. Si detectas comportamiento de bot (texto sin sentido, caracteres aleatorios, solo números, repeticiones excesivas, etc).
Devuelve SOLO EN FORMATO JSON sin explicaciones adicionales:
{{
"toxicidad": 0-100,
"respeto": 0-100,
"scam": 0-100,
"confiabilidad": 0-100,
"es_bot": true/false,
"score_final": 0-100
}}

Criterios para detectar bots:
- Texto muy corto (<3 caracteres)
- Solo números o caracteres especiales
- Palabras sin sentido o gibberish ("dsfasfd", "xxxx", etc)
- Caracteres repetidos excesivamente
- Texto sin vocales
- Muy largo sin espacios

IMPORTANTE: Si es bot, colocale directamente un cero como puntaje.

Texto: {input.text}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # Obtener la respuesta del modelo
        raw = response.choices[0].message.content
        print("RAW RESPONSE:", raw)  # -> Ver que tiene en terminal
        
        # LIMPIAR la respuesta
        raw_limpio = limpiar_json(raw)
        print("CLEANED RESPONSE:", raw_limpio)  # -> Ver la limpieza
        
        # Convertir la respuesta JSON en un diccionario de Python
        try:
            result = json.loads(raw_limpio)
        except json.JSONDecodeError as e:
            print(f"ERROR al parsear JSON: {e}")
            print(f"Intentando parsear: {raw_limpio}")
            return {"error": "No se pudo procesar la respuesta de OpenAI", "raw": raw, "cleaned": raw_limpio}
        
        # Cálculo para el score final (si OpenAI no lo calcula)
        toxicidad = result.get("toxicidad", 0)
        scam = result.get("scam", 0)
        respeto = result.get("respeto", 0)
        confiabilidad = result.get("confiabilidad", 0)
        
        # Si todos los valores son 0, el score_final es 0
        if toxicidad == 0 and scam == 0 and respeto == 0 and confiabilidad == 0:
            score_final = 0
        else:
            score_final = (
                (100 - toxicidad)
                + (100 - scam)
                + respeto
                + confiabilidad
            ) / 4
        
        # Redondeo
        score_final = round(score_final, 2)
        
        # Agregar al análisis
        result["score_final"] = score_final
        
        # Devolver el análisis completo
        return result
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        return {"error": f"Error al procesar: {str(e)}"}