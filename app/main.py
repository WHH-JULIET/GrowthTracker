import sys
from pathlib import Path

# Allow running as `python app\main.py`
if __package__ is None or __package__ == '':
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.web import app

# For local dev: python app\main.py or python -m app.main
if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.web:app', host='127.0.0.1', port=8000, reload=True)
