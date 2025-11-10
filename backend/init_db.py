from app import app, db
from sqlalchemy import inspect

def init_database():
    
    with app.app_context():
        
        db.create_all()
        
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            print(f"  {table}")
        
if __name__ == '__main__':
    init_database()