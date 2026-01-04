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

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/api/verify-password")
def verify_password(password: str):
    if password == os.getenv("APP_PASSWORD", "biotracker"):
        return {"status": "ok"}
    raise HTTPException(status_code=401)

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
    return db.query(InjectionLog).order_by(InjectionLog.timestamp.desc()).all()

@app.post("/api/logs")
def save_log(name: str, dose: float, db: Session = Depends(get_db)):
    db.add(InjectionLog(compound_name=name, mcg=dose))
    db.commit()
    return {"status": "ok"}

@app.delete("/api/logs/{id}")
def delete_log(id: int, db: Session = Depends(get_db)):
    db.query(InjectionLog).filter(InjectionLog.id == id).delete()
    db.commit()
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
