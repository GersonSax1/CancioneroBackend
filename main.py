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
        
        # Ignorar números de página
        if texto.isdigit():
            continue

        # Respetar saltos de línea para la app
        if not texto:
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(texto.split())
        texto_minusculas = texto.lower()
        
        # Evitar falsos positivos como coros o notas de repetición
        empieza_con_coro = texto_minusculas.startswith("coro")
        empieza_con_simbolo = texto.startswith("//") or texto.startswith("(") or texto.startswith("-")

        # Detectar la Negrita
        es_negrita = False
        for run in para.runs:
            if run.bold:
                es_negrita = True
                break
        if not es_negrita and para.style.font.bold:
            es_negrita = True

        es_titulo = False
        
        # LA REGLA DE ORO: 
        # Es título solo si tiene NEGRITA, NO es coro ni símbolo, y tiene MÁXIMO 6 PALABRAS
        # (Se permiten hasta 7 palabras si incluye un acorde musical como "(LA)")
        limite_palabras = 7 if "(" in texto and ")" in texto else 6

        if es_negrita and not empieza_con_coro and not empieza_con_simbolo and palabras <= limite_palabras:
            es_titulo = True

        # Forzar el primer título si el documento inicia directo
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

    for i in range(len(lineas)):
        linea_limpia = lineas[i].strip()

        if linea_limpia.isdigit():
            continue

        if not linea_limpia:
            if letra_actual and letra_actual[-1] != "":
                letra_actual.append("")
            continue

        palabras = len(linea_limpia.split())
        texto_minusculas = linea_limpia.lower()
        empieza_con_coro = texto_minusculas.startswith("coro")
        empieza_con_simbolo = linea_limpia.startswith("//") or linea_limpia.startswith("(")

        es_titulo = False
        
        if not empieza_con_coro and not empieza_con_simbolo and palabras <= 6 and linea_limpia.isupper():
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
