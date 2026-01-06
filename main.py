import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configurazione Database
# Il nome del file biotracker.db garantisce la persistenza dei dati
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotracker.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELLI DATABASE ---
class Compound(Base):
    __tablename__ = "compounds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    half_life_hours = Column(Float)
    category = Column(String)
    min_threshold = Column(Float, default=0.0)

class InjectionLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    compound_name = Column(String)
    mcg = Column(Float)
    # Rimosso il default forzato qui per gestire date manuali
    timestamp = Column(DateTime)

# Crea le tabelle solo se non esistono (Protezione Dati)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dipendenza per il Database
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ROTTE API ---

@app.get("/api/verify-password")
def verify_password(password: str):
    # Legge la password SOLO dalle variabili di Railway.
    # Se su Railway non è impostata, l'accesso sarà sempre negato (sicurezza totale del codice).
    stored_password = os.environ.get("APP_PASSWORD")
    
    # Verifichiamo che la password esista su Railway e che coincida con quella inserita
    if stored_password and password.strip() == stored_password.strip():
        return {"status": "ok"}
    
    # Se la password è sbagliata o la variabile su Railway è vuota, blocca l'accesso
    raise HTTPException(status_code=401, detail="Accesso negato")


@app.get("/api/compounds")
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()

@app.post("/api/compounds/add")
def add_compound(name: str, half_life: float, threshold: float = 0, db: Session = Depends(get_db)):
    if not db.query(Compound).filter(Compound.name == name).first():
        db.add(Compound(name=name, half_life_hours=half_life, category="P", min_threshold=threshold))
        db.commit()
    return {"status": "ok"}

@app.delete("/api/compounds/{id}")
def delete_compound(id: int, db: Session = Depends(get_db)):
    db.query(Compound).filter(Compound.id == id).delete()
    db.commit()
    return {"status": "ok"}

@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    # Ordina i log per data decrescente (i più recenti in alto)
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()

# --- FUNZIONE SALVATAGGIO CORRETTA CON DATA MANUALE ---
@app.post("/api/logs")
def save_log(name: str, dose: float, timestamp: str = Query(None), db: Session = Depends(get_db)):
    # Se l'utente ha inviato una data manuale, la convertiamo
    if timestamp:
        try:
            # Rimuoviamo eventuali 'Z' o fusi orari per compatibilità SQLite
            clean_ts = timestamp.replace('Z', '').replace('T', ' ')
            # Se la stringa è YYYY-MM-DD HH:MM la portiamo a YYYY-MM-DD HH:MM:SS
            if len(clean_ts) == 16:
                clean_ts += ":00"
            dt_obj = datetime.strptime(clean_ts, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Errore parsing data: {e}")
            dt_obj = datetime.now()
    else:
        dt_obj = datetime.now()
        
    new_log = InjectionLog(compound_name=name, mcg=dose, timestamp=dt_obj)
    db.add(new_log)
    db.commit()
    return {"status": "ok"}

@app.delete("/api/logs/{id}")
def delete_log(id: int, db: Session = Depends(get_db)):
    db.query(InjectionLog).filter(InjectionLog.id == id).delete()
    db.commit()
    return {"status": "ok"}

# Serve i file statici (l'HTML che abbiamo scritto finora)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Usa la porta definita dall'ambiente o la 8080 di default
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

