# Backend Flask

## Lancement

```powershell
cd C:\Users\PC\Desktop\interface6
pip install -r requirements.txt
python backend/server.py
```

Le backend demarre sur `http://127.0.0.1:5000`.

Pour servir le frontend:

```powershell
cd C:\Users\PC\Desktop\interface6
python -m http.server 5500 -d frontend
```

## Endpoints

- `GET /api/model/status`
- `POST /api/model/load`
- `POST /api/predict/image`
- `POST /api/predict/frame`
