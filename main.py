from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx
import PyPDF2
import io

app = FastAPI() # <- ¡Esta es la pieza que decía que faltaba!

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

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        if len(linea.split()) <= 6 and not letra_actual:
            titulo_actual = linea
        elif len(linea.split()) <= 6 and len(letra_actual) > 0:
            canciones.append({
                "id": str(len(canciones) + 1),
                "titulo": titulo_actual,
                "letra": "\n".join(letra_actual)
            })
            titulo_actual = linea
            letra_actual = []
        else:
            letra_actual.append(linea)

    if letra_actual:
        canciones.append({
            "id": str(len(canciones) + 1),
            "titulo": titulo_actual,
            "letra": "\n".join(letra_actual)
        })
        
    return canciones

@app.post("/procesar-documento/")
async def procesar_documento(file: UploadFile = File(...)):
    content = await file.read()
    texto_completo = ""

    try:
        if file.filename.endswith('.docx'):
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