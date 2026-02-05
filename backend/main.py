from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from nanoid import generate
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

from database import engine, get_db, Base
from models import Link, Click
from schemas import (
    LinkCreate, LinkResponse, LinkListResponse,
    AuthRequest, AuthResponse, StatsResponse
)

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Publimetro URL Shortener",
    description="Acortador de URLs para Publimetro",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "publimetro2026")
EDITORIAL_PASSWORD = os.getenv("EDITORIAL_PASSWORD", "publimetro_edit")

DOMAIN_MAPPING = {
    # Todos los dominios usan s.metrolatam.com
    "metrolatam.com": "s.metrolatam.com",
    "readmetro.com": "s.metrolatam.com",
    "elcalce.com": "s.metrolatam.com",
    "fayerwayer.com": "s.metrolatam.com",
    "ferplei.com": "s.metrolatam.com",
    "metroecuador.com.ec": "s.metrolatam.com",
    "metro.pr": "s.metrolatam.com",
    "metroworldnews.com": "s.metrolatam.com",
    "mwnjornal.com.br": "s.metrolatam.com",
    "nuevamujer.com": "s.metrolatam.com",
    "publimetro.cl": "s.metrolatam.com",
    "publimetro.co": "s.metrolatam.com",
    "publimetro.com.mx": "s.metrolatam.com",
    "publinews.gt": "s.metrolatam.com",
    "sagrosso.com": "s.metrolatam.com"
}

def get_base_url(request: Request, original_url: str = None):
    protocol = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    
    if original_url:
        try:
            parsed = urlparse(original_url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            
            for domain, short_domain in DOMAIN_MAPPING.items():
                if netloc == domain or netloc.endswith("." + domain):
                    return f"{protocol}://{short_domain}"
        except:
            pass

    # Fallback: detect from current request
    host = request.headers.get("Host", request.url.netloc)
    return f"{protocol}://{host}"


# ============ AUTH ============
@app.post("/api/auth", response_model=AuthResponse)
async def authenticate(auth: AuthRequest):
    if auth.password == ADMIN_PASSWORD:
        return AuthResponse(success=True, message="Autenticación exitosa", role="admin")
    if auth.password == EDITORIAL_PASSWORD:
        return AuthResponse(success=True, message="Autenticación exitosa", role="editorial")
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

async def get_current_role(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        # Fallback for old clients or direct access without header
        return "editorial" # Default restrictivo
    
    token = auth_header.replace("Bearer ", "")
    if token == ADMIN_PASSWORD:
        return "admin"
    if token == EDITORIAL_PASSWORD:
        return "editorial"
    raise HTTPException(status_code=401, detail="Credenciales inválidas")


# ============ LINKS ============
@app.post("/api/links", response_model=LinkResponse)
async def create_link(
    link: LinkCreate, 
    request: Request, 
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    # Generate or use custom short code
    if link.custom_code:
        # Check if custom code exists
        existing = db.query(Link).filter(Link.short_code == link.custom_code).first()
        if existing:
            raise HTTPException(status_code=400, detail="El código personalizado ya existe")
        short_code = link.custom_code
    else:
        # Generate unique code
        while True:
            short_code = generate(size=6)
            existing = db.query(Link).filter(Link.short_code == short_code).first()
            if not existing:
                break
    
    # Create link
    db_link = Link(
        short_code=short_code,
        original_url=link.url,
        title=link.title
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    return LinkResponse(
        id=db_link.id,
        short_code=db_link.short_code,
        original_url=db_link.original_url,
        title=db_link.title,
        created_at=db_link.created_at,
        clicks=db_link.clicks,
        short_url=f"{get_base_url(request, db_link.original_url)}/{db_link.short_code}"
    )


@app.get("/api/links", response_model=LinkListResponse)
async def get_links(request: Request, db: Session = Depends(get_db)):
    links = db.query(Link).order_by(Link.created_at.desc()).all()
    base_url = get_base_url(request)
    
    return LinkListResponse(
        links=[
            LinkResponse(
                id=link.id,
                short_code=link.short_code,
                original_url=link.original_url,
                title=link.title,
                created_at=link.created_at,
                clicks=link.clicks,
                short_url=f"{get_base_url(request, link.original_url)}/{link.short_code}"
            )
            for link in links
        ],
        total=len(links)
    )


@app.delete("/api/links/{link_id}")
async def delete_link(
    link_id: int, 
    db: Session = Depends(get_db),
    role: str = Depends(get_current_role)
):
    if role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar links")

    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link no encontrado")
    
    db.delete(link)
    db.commit()
    return {"message": "Link eliminado exitosamente"}


# ============ STATS ============
@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    total_links = db.query(func.count(Link.id)).scalar() or 0
    total_clicks = db.query(func.sum(Link.clicks)).scalar() or 0
    links_today = db.query(func.count(Link.id)).filter(Link.created_at >= today_start).scalar() or 0
    clicks_today = db.query(func.count(Click.id)).filter(Click.clicked_at >= today_start).scalar() or 0
    
    return StatsResponse(
        total_links=total_links,
        total_clicks=int(total_clicks),
        links_today=links_today,
        clicks_today=clicks_today
    )


# ============ REDIRECT ============
@app.get("/{short_code}")
async def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link no encontrado")
    
    # Record click
    click = Click(
        link_id=link.id,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(click)
    
    # Increment click count
    link.clicks += 1
    db.commit()
    
    return RedirectResponse(url=link.original_url, status_code=307)


# ============ HEALTH CHECK ============
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "publimetro-shortener"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
