import sys
sys.path.insert(0, 'C:\\Users\\Aman Qureshi\\Desktop\\Royal Brain\\royal-brain\\backend')

from app.core.database import engine
from sqlalchemy import inspect

insp = inspect(engine)
tables = insp.get_table_names()
print(f'Total tables: {len(tables)}')
print('\n'.join(sorted(tables)))
