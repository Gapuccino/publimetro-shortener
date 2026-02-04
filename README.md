# Publimetro URL Shortener

Acortador de URLs para Publimetro con dashboard administrativo.

## Tecnologías

- **Backend:** FastAPI (Python)
- **Frontend:** Astro
- **Base de datos:** SQLite

## Instalación

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Uso

1. Abrir `http://localhost:4321`
2. Ingresar contraseña: `publimetro2024`
3. Crear links cortos desde el dashboard

## Variables de entorno

Copiar `.env.example` a `.env` y configurar:

- `ADMIN_PASSWORD`: Contraseña de acceso
- `BASE_URL`: URL base para los links cortos
