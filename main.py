from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime

# Configurazione DB
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotracker.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelli Database
class Compound(Base):
    __tablename__ = "compounds"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    half_life_hours = Column(Float)
    category = Column(String)

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

# Popolamento iniziale sostanze
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

@app.get("/api/compounds")
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()

@app.post("/api/logs")
def save_log(name: str, dose: float, db: Session = Depends(get_db)):
    log = InjectionLog(compound_name=name, mcg=dose)
    db.add(log)
    db.commit()
    return {"status": "ok"}

@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()


app.mount("/", StaticFiles(directory="static", html=True), name="static")
@app.post("/api/compounds/add")
def add_compound(name: str, half_life: float, category: str, db: Session = Depends(get_db)):
    new_comp = Compound(name=name, half_life_hours=half_life, category=category)
    db.add(new_comp)
    db.commit()
    return {"status": "Sostanza salvata!"}
