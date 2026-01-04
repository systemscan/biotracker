import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. Configurazione Database
# Gestisce sia PostgreSQL (Railway) che SQLite (locale)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotracker.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Modelli del Database
class Compound(Base):
    __tablename__ = "compounds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    half_life_hours = Column(Float)
    category = Column(String)
    min_threshold = Column(Float, default=0.0) # La soglia minima impostata

class InjectionLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    compound_name = Column(String)
    mcg = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Crea le tabelle se non esistono
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency per ottenere la sessione del DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Funzione di popolamento iniziale (Seed)
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    # Sostanze di esempio con emivite e soglie di default
    defaults = [
        {"name": "BPC-157", "half_life": 4, "category": "Peptide", "threshold": 100},
        {"name": "TB-500", "half_life": 240, "category": "Peptide", "threshold": 500},
        {"name": "Testo Enantato", "half_life": 120, "category": "Steroide", "threshold": 10},
        {"name": "Semaglutide", "half_life": 168, "category": "GLP-1", "threshold": 0.5}
    ]
    for d in defaults:
        exists = db.query(Compound).filter(Compound.name == d["name"]).first()
        if not exists:
            new_comp = Compound(
                name=d["name"], 
                half_life_hours=d["half_life"], 
                category=d["category"],
                min_threshold=d["threshold"]
            )
            db.add(new_comp)
    db.commit()
    db.close()

# 4. Rotte API (Endpoint)

@app.get("/api/compounds")
def get_compounds(db: Session = Depends(get_db)):
    """Ritorna la lista di tutte le sostanze in libreria."""
    return db.query(Compound).all()

@app.post("/api/compounds/add")
def add_compound(name: str, half_life: float, category: str, threshold: float = 0, db: Session = Depends(get_db)):
    """Aggiunge una nuova sostanza con emivita e soglia minima."""
    exists = db.query(Compound).filter(Compound.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Sostanza già esistente")
    
    new_comp = Compound(
        name=name, 
        half_life_hours=half_life, 
        category=category, 
        min_threshold=threshold
    )
    db.add(new_comp)
    db.commit()
    return {"status": "Sostanza salvata con successo"}

@app.post("/api/logs")
def save_log(name: str, dose: float, db: Session = Depends(get_db)):
    """Registra una somministrazione avvenuta ora."""
    log = InjectionLog(compound_name=name, mcg=dose)
    db.add(log)
    db.commit()
    return {"status": "Iniezione registrata"}

@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    """Ritorna lo storico delle somministrazioni (le più recenti prima)."""
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()

# 5. Hosting dell'interfaccia Frontend
# Assicurati che la cartella 'static' esista e contenga index.html
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Railway assegna la porta dinamicamente tramite variabile d'ambiente
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
