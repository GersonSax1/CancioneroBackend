from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx
import PyPDF2
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def procesar_texto(texto_completo):
    lineas = texto_completo.split('\n')
    canciones = []
    titulo_actual = "Sin Título"
    letra_actual = []

    for i in range(len(lineas)):
        linea_original = lineas[i]
        linea_limpia = linea_original.strip()

        # 1. Ignorar números de página sueltos
        if linea_limpia.isdigit():
            continue

        # 2. Respetar los espacios en blanco para separar estrofas en la app
        if not linea_limpia:
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(linea_limpia.split())
        es_coro = linea_limpia.upper().replace(".", "").replace(":", "").replace(" ", "") == "CORO"

        # 3. Lógica para detectar Títulos reales
        es_titulo = False
        linea_anterior_vacia = (i == 0) or (lineas[i-1].strip() == "")

        # Un título viene tras un salto de línea, no es "Coro", y no es una estrofa larga
        if linea_anterior_vacia and not es_coro and palabras <= 10:
            # En tu documento, casi todos los títulos terminan en un punto
            if linea_limpia.endswith('.'):
                es_titulo = True
            # O si la canción anterior ya acumuló varias líneas, una frase corta tras un salto es un título
            elif len([l for l in letra_actual if l.strip()]) >= 4:
                es_titulo = True

        # Forzamos el primer título si el documento empieza directo
        if i == 0 and not es_titulo and not es_coro:
            es_titulo = True

        if es_titulo:
            # Guardamos la canción anterior empaquetada
            lineas_validas = [l for l in letra_actual if l.strip()]
            if lineas_validas:
                canciones.append({
                    "id": str(len(canciones) + 1),
                    # Quitamos el punto final al título para que se vea estético en el índice
                    "titulo": titulo_actual.rstrip('.').strip(),
                    "letra": "\n".join(letra_actual).strip()
                })
            
            titulo_actual = linea_limpia
            letra_actual = []
        else:
            letra_actual.append(linea_limpia)

    # Guardamos la última canción que quedó en el bucle
    lineas_validas = [l for l in letra_actual if l.strip()]
    if lineas_validas:
        canciones.append({
            "id": str(len(canciones) + 1),
            "titulo": titulo_actual.rstrip('.').strip(),
            "letra": "\n".join(letra_actual).strip()
        })

    return canciones

@app.post("/procesar-documento/")
async def procesar_documento(file: UploadFile = File(...)):
    content = await file.read()
    texto_completo = ""

    try:
        if file.filename.endswith('.docx') or file.filename.endswith('.doc'):
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                texto_completo += para.text + "\n"
        elif file.filename.endswith('.pdf'):
            lector = PyPDF2.PdfReader(io.BytesIO(content))
            for pagina in lector.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
        else:
            raise HTTPException(status_code=400, detail="Sube un archivo .docx o .pdf válido.")
            
        canciones = procesar_texto(texto_completo)
        return {"status": "éxito", "canciones": canciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")
