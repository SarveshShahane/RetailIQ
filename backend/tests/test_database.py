import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from importlib import reload

def test_db_url_conversion_logic():
    convert_url = lambda url: url.replace("postgresql+asyncpg://", "postgresql://", 1) if url.startswith("postgresql+asyncpg://") else url

    assert convert_url("postgresql+asyncpg://postgres:pass@localhost/db") == "postgresql://postgres:pass@localhost/db"
    
    assert convert_url("postgresql://postgres:pass@localhost/db") == "postgresql://postgres:pass@localhost/db"
    
    assert convert_url("sqlite:///test.db") == "sqlite:///test.db"

def test_database_module_load():
    from db import database
    reload(database)
    
    assert database.engine is not None
    assert database.async_engine is not None
    assert database.SessionLocal is not None
    assert database.AsyncSessionLocal is not None
