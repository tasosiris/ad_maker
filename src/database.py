from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func
from src.config import DB_TYPE, DB_PATH, DB_CONNECTION_STRING

# --- Database Setup ---
if DB_TYPE == 'sqlite':
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
elif DB_TYPE == 'postgresql' and DB_CONNECTION_STRING:
    SQLALCHEMY_DATABASE_URL = DB_CONNECTION_STRING
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    raise ValueError(f"Unsupported DB_TYPE '{DB_TYPE}' or missing connection string.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ORM Models ---

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    idea = Column(String, unique=True, index=True)
    category = Column(String)
    status = Column(String, default="pending") # e.g., pending, scripting, feedback, approved, rendering, done
    # Product information
    product_name = Column(String, nullable=True)
    product_url = Column(String, nullable=True)
    affiliate_commission = Column(String, nullable=True)  # e.g., "5-8%"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    scripts = relationship("Script", back_populates="job")

class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    script_type = Column(String) # 'long_form' or 'short_form'
    content = Column(Text)
    status = Column(String, default="pending") # e.g., pending, approved, revised
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="scripts")
    feedback = relationship("Feedback", back_populates="script", uselist=False)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    decision = Column(String) # 'approved' or 'revised'
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    script = relationship("Script", back_populates="feedback")


# --- Database Initialization ---
def init_db():
    """Create all tables in the database."""
    print("Initializing database...")
    # Drop all tables first to ensure a clean slate
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

# --- Dependency for getting a DB session ---
def get_db():
    """Provides a database session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == '__main__':
    # Allows creating the database from the command line
    init_db() 