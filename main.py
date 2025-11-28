from fastapi import FastAPI
from pydantic import BaseModel
import openai
import json
import os
import re
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware




load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Creacion la app usando fastAPI
app = FastAPI()

#Esto es para evitar problema con el frontend y el CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Clase para el input del usuario
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


#Endpoint para el análisis
@app.post("/analyze")
async def analyze(input: UserInput):
    prompt = f"""
    Analiza el texto del usuario y genera un puntaje de reputación entre 0 y 100,
    devolviendo EXCLUSIVAMENTE el siguiente formato JSON (sin explicaciones):

    {{
        "overallScore": number,
        "breakdown": {{
            "trustworthiness": number,
            "security": number,
            "experience": number,
            "behavior": number
        }}
    }}

    Donde cada valor es un entero entre 0 y 100.

    Criterios:
    - trustworthiness → qué tan confiable parece el usuario.
    - security → riesgo de scam o fraude (100 = sin riesgo).
    - experience → madurez, respeto, claridad y cooperación.
    - behavior → ausencia de toxicidad, troll, spam o bot.

    Detecta también comportamiento de bot:
    - si el texto es muy corto
    - si es incoherente
    - si es repetitivo
    - si es puro gibberish (“asdfsdf”, “xxxx”, etc.)
    - si no tiene vocales
    - si es extremadamente largo sin espacios

    Si detectas bot → todos los valores deben ser 0 EXCEPTO security = 100.

    Texto: {input.text}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        raw = response.choices[0].message.content
        print("RAW RESPONSE:", raw)

        clean = limpiar_json(raw)

        result = json.loads(clean)

        return result

    except Exception as e:
        print("ERROR:", e)
        return {"error": str(e)}
