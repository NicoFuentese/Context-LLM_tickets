# Smart-IT Ops: GLPi Intelligent Advisor

Asistente basado en IA para infraestructura TI, diseñado para analizar cargas de trabajo de GLPi y sugerir asignaciones óptimas.

## 📋 Requisitos Previos
- Windows 11 (PowerShell)
- Python 3.10+
- Acceso a GLPi (para exportar CSV)
- Google Gemini API Key

## 🚀 Instalación y Despliegue (Windows)

### 1. Preparar el Entorno
Abrir PowerShell en la carpeta raíz del proyecto:

```powershell
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

# Tu VS Code no te reconoce tus dependencias?
Esto ocurre porque VS Code esta "mirando" tu Python global para hacer el autocompletado y la revision de errores.

### Para arreglarlo selecciona el interprete Correcto:
    1. Presiona Ctrl + Shift + P (o Cmd + Shift + P en Mac) para abrir la paleta de comandos.
    2. Escribe y selecciona: Python: Select Interpreter.
    3. Verás una lista. Busca la opción que diga algo como:
     - Python 3.x.x ('venv': venv) 👈 Esta es la correcta.
     - O que tenga la ruta ./venv/Scripts/python.exe.
    4. Selecciónala.
    5. Espera unos segundos. El error de Pylance debería desaparecer.

# Quieres consultar los modelos que tienes disponibles?
```powershell
#Encontrar modelos disponibles de Gemini
cd .\services\
python test_models.py
```

# Para correr la aplicación
```powershell
#Correr proyecto
streamlit run app.py
```