import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configurazione Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotracker.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelli
class Compound(Base):
    __tablename__ = "compounds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    half_life_hours = Column(Float)
    category = Column(String)
    min_threshold = Column(Float, default=0.0)

class InjectionLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    compound_name = Column(String)
    mcg = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    defaults = [
        {"name": "BPC-157", "hl": 4, "cat": "Peptide", "th": 100},
        {"name": "Testo Enantato", "hl": 120, "cat": "Steroide", "th": 10}
    ]
    for d in defaults:
        if not db.query(Compound).filter(Compound.name == d["name"]).first():
            db.add(Compound(name=d["name"], half_life_hours=d["hl"], category=d["cat"], min_threshold=d["th"]))
    db.commit()
    db.close()

@app.get("/api/compounds")
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()

@app.post("/api/compounds/add")
def add_compound(name: str, half_life: float, category: str, threshold: float = 0, db: Session = Depends(get_db)):
    if db.query(Compound).filter(Compound.name == name).first():
        raise HTTPException(status_code=400, detail="Esiste già")
    new_c = Compound(name=name, half_life_hours=half_life, category=category, min_threshold=threshold)
    db.add(new_c)
    db.commit()
    return {"status": "ok"}

@app.delete("/api/compounds/{compound_id}")
def delete_compound(compound_id: int, db: Session = Depends(get_db)):
    comp = db.query(Compound).filter(Compound.id == compound_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Non trovato")
    db.delete(comp)
    db.commit()
    return {"status": "eliminato"}

@app.post("/api/logs")
def save_log(name: str, dose: float, db: Session = Depends(get_db)):
    db.add(InjectionLog(compound_name=name, mcg=dose))
    db.commit()
    return {"status": "ok"}

@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
    @app.delete("/api/logs/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(InjectionLog).filter(InjectionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log non trovato")
    db.delete(log)
    db.commit()
    return {"status": "log eliminato"}


