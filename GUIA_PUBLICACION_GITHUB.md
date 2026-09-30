# Publicar en GitHub

## 1. Requisitos

- Instalar y abrir GitHub Desktop.
- Iniciar sesion con la cuenta de GitHub correcta.
- Crear el repositorio desde GitHub Desktop o usar uno vacio de GitHub.
- No agregar otro README ni otro `.gitignore`, porque este proyecto ya contiene documentacion y reglas de exclusion.

## 2. Inicializar con GitHub Desktop

En GitHub Desktop:

1. Seleccionar `File > Add local repository`.
2. Elegir la carpeta del proyecto.
3. Si GitHub Desktop indica que no es un repositorio, seleccionar `create a repository`.
4. Usar `main` como nombre de la rama inicial.
5. Revisar la lista de cambios y confirmar que no aparezcan perfiles de Chrome, archivos `.env`, exportaciones ni otros datos privados.
6. Escribir `Inicializa proyecto OT` como resumen y seleccionar `Commit to main`.

## 3. Publicar en GitHub

Seleccionar `Publish repository` en GitHub Desktop, elegir el nombre y la visibilidad del repositorio, y confirmar con `Publish repository`.

GitHub Desktop gestiona la autenticacion mediante el navegador. Nunca guardar tokens dentro del proyecto.

## 4. Comprobar el proyecto despues de clonarlo

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python app.py
```

La aplicacion usa una sesion local de Chrome para SharePoint. Cada usuario debe iniciar sesion en su propio navegador; el perfil `perfil_chrome_sharepoint` no se versiona.