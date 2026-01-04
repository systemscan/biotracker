from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime

# Configurazione DB (Postgres per Railway, SQLite locale come backup)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotracker.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modello Tabella Sostanze
class Compound(Base):
    __tablename__ = "compounds"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    half_life_hours = Column(Float)
    category = Column(String)

# Modello Tabella Registri (Iniezioni)
class InjectionLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    compound_name = Column(String)
    mcg = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 1. Caricamento iniziale sostanze standard
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    defaults = [
        {"name": "BPC-157", "half_life": 4, "category": "Peptide"},
        {"name": "TB-500", "half_life": 240, "category": "Peptide"},
        {"name": "Testo Enantato", "half_life": 120, "category": "Steroide"},
        {"name": "Semaglutide", "half_life": 168, "category": "GLP-1"}
    ]
    for d in defaults:
        if not db.query(Compound).filter(Compound.name == d["name"]).first():
            db.add(Compound(name=d["name"], half_life_hours=d["half_life"], category=d["category"]))
    db.commit()
    db.close()

# 2. API per ottenere la lista delle sostanze
@app.get("/api/compounds")
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()

# 3. API PER AGGIUNGERE NUOVE SOSTANZE (QUELLE CHE TI MANCAVA)
@app.post("/api/compounds/add")
def add_compound(name: str, half_life: float, category: str, db: Session = Depends(get_db)):
    # Controlla se esiste già
    exists = db.query(Compound).filter(Compound.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Sostanza già esistente")
    
    new_comp = Compound(name=name, half_life_hours=half_life, category=category)
    db.add(new_comp)
    db.commit()
    return {"status": "Sostanza salvata!"}

# 4. API per salvare i log
@app.post("/api/logs")
def save_log(name: str, dose: float, db: Session = Depends(get_db)):
    log = InjectionLog(compound_name=name, mcg=dose)
    db.add(log)
    db.commit()
    return {"status": "ok"}

# 5. API per leggere i log
@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()

app.mount("/", StaticFiles(directory="static", html=True), name="static")
