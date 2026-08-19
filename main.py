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

def procesar_docx(content):
    doc = docx.Document(io.BytesIO(content))
    canciones = []
    titulo_actual = "Sin Título"
    letra_actual = []

    for para in doc.paragraphs:
        texto = para.text.strip()
        
        # Ignorar números sueltos (paginación)
        if texto.isdigit():
            continue

        # Mantener los espacios en blanco para separar estrofas visualmente
        if not texto:
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(texto.split())
        es_coro = texto.upper().replace(".", "").replace(":", "").replace(" ", "") == "CORO"

        # Detectar estrictamente si la línea tiene formato NEGRITA en Word
        es_negrita = False
        for run in para.runs:
            if run.bold:
                es_negrita = True
                break
        
        if not es_negrita and para.style.font.bold:
            es_negrita = True

        es_titulo = False
        
        # REGLA ÚNICA Y DEFINITIVA: Solo es título si está en NEGRITA, es corto, y no es un "Coro"
        # Ya no intentamos adivinar por puntos o espacios.
        if es_negrita and not es_coro and palabras <= 10:
            es_titulo = True

        # Forzar el primer título si el documento empieza sin negrita (seguridad inicial)
        if len(canciones) == 0 and titulo_actual == "Sin Título" and not letra_actual and not es_coro:
            es_titulo = True

        if es_titulo:
            # Empaquetamos la canción anterior completa antes de iniciar la nueva
            lineas_validas = [l for l in letra_actual if l.strip()]
            if lineas_validas:
                canciones.append({
                    "id": str(len(canciones) + 1),
                    "titulo": titulo_actual.rstrip('.').strip(),
                    "letra": "\n".join(letra_actual).strip()
                })
            titulo_actual = texto
            letra_actual = []
        else:
            # Todo lo que no sea título en negrita, se suma a la letra actual
            letra_actual.append(texto)

    # Empaquetamos la última canción que quedó en memoria al terminar el documento
    lineas_validas = [l for l in letra_actual if l.strip()]
    if lineas_validas:
        canciones.append({
            "id": str(len(canciones) + 1),
            "titulo": titulo_actual.rstrip('.').strip(),
            "letra": "\n".join(letra_actual).strip()
        })
    
    return canciones


def procesar_texto_plano(texto_completo):
    lineas = texto_completo.split('\n')
    canciones = []
    titulo_actual = "Sin Título"
    letra_actual = []

    for i in range(len(lineas)):
        linea_limpia = lineas[i].strip()

        if linea_limpia.isdigit():
            continue

        if not linea_limpia:
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(linea_limpia.split())
        es_coro = linea_limpia.upper().replace(".", "").replace(":", "").replace(" ", "") == "CORO"

        es_titulo = False
        
        # Como en PDF no hay negrita, usamos mayúsculas o reglas simples como respaldo
        if not es_coro and palabras <= 8 and linea_limpia.isupper():
            es_titulo = True

        if len(canciones) == 0 and titulo_actual == "Sin Título" and not letra_actual and not es_coro:
            es_titulo = True

        if es_titulo:
            lineas_validas = [l for l in letra_actual if l.strip()]
            if lineas_validas:
                canciones.append({
                    "id": str(len(canciones) + 1),
                    "titulo": titulo_actual.rstrip('.').strip(),
                    "letra": "\n".join(letra_actual).strip()
                })
            titulo_actual = linea_limpia
            letra_actual = []
        else:
            letra_actual.append(linea_limpia)

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

    try:
        if file.filename.endswith('.docx') or file.filename.endswith('.doc'):
            canciones = procesar_docx(content)
        elif file.filename.endswith('.pdf'):
            texto_completo = ""
            lector = PyPDF2.PdfReader(io.BytesIO(content))
            for pagina in lector.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
            canciones = procesar_texto_plano(texto_completo)
        else:
            raise HTTPException(status_code=400, detail="Sube un archivo .docx o .pdf válido.")
            
        return {"status": "éxito", "canciones": canciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")
