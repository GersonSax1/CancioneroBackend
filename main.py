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
    
    # Control para asegurar que el título venga después de un espacio
    linea_anterior_vacia = True 

    for para in doc.paragraphs:
        texto = para.text.strip()
        
        # Ignorar números de página
        if texto.isdigit():
            continue

        # Mantener los espacios vacíos y registrarlos
        if not texto:
            linea_anterior_vacia = True
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(texto.split())
        texto_minusculas = texto.lower()
        
        # Ignorar cualquier línea que empiece con "coro" (ej: "Coro...", "Coro (Sube tono)")
        empieza_con_coro = texto_minusculas.startswith("coro")

        es_negrita = False
        for run in para.runs:
            if run.bold:
                es_negrita = True
                break
        
        if not es_negrita and para.style.font.bold:
            es_negrita = True

        es_titulo = False
        
        # LA TRIPLE VALIDACIÓN DEFINITIVA:
        # 1. Es Negrita | 2. Viene de un espacio vacío | 3. No empieza con "Coro" | 4. Es corto
        if es_negrita and linea_anterior_vacia and not empieza_con_coro and palabras <= 12:
            es_titulo = True

        # Asegurar el título de la primera canción del documento
        if len(canciones) == 0 and titulo_actual == "Sin Título" and not letra_actual and not empieza_con_coro:
            es_titulo = True

        if es_titulo:
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
            letra_actual.append(texto)
            
        # Al pasar por aquí, la línea dejó de estar vacía
        linea_anterior_vacia = False

    # Guardar la última canción
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
    
    linea_anterior_vacia = True

    for i in range(len(lineas)):
        linea_limpia = lineas[i].strip()

        if linea_limpia.isdigit():
            continue

        if not linea_limpia:
            linea_anterior_vacia = True
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(linea_limpia.split())
        texto_minusculas = linea_limpia.lower()
        empieza_con_coro = texto_minusculas.startswith("coro")

        es_titulo = False
        
        # En PDF (texto plano) requerimos espacio vacío, mayúsculas y no ser coro
        if linea_anterior_vacia and not empieza_con_coro and palabras <= 10 and linea_limpia.isupper():
            es_titulo = True

        if len(canciones) == 0 and titulo_actual == "Sin Título" and not letra_actual and not empieza_con_coro:
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
            
        linea_anterior_vacia = False

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
