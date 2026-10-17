# Emotion AI Studio

Interface Python/Tkinter pour tester un modele PyTorch `.pth` en trois modes:

- Image
- Video
- Live cam

## Installation

```powershell
pip install -r requirements.txt
```

## Lancement

```powershell
python app.py
```

## Version frontend + backend

Backend:

```powershell
python backend/server.py
```

Frontend:

```powershell
python -m http.server 5500 -d frontend
```

Puis ouvrez:

```text
http://127.0.0.1:5500
```

Alternative simple:

Ouvrez le fichier `frontend/index.html` dans le navigateur.

Le backend utilise `model.pth` place dans ce dossier, ou le modele envoye depuis le bouton `Charger .pth` du frontend.

Les comptes utilisateur sont stockes automatiquement dans la base SQLite `users.db`.
Si un email n'existe pas, la page de connexion affiche `Compte inexistant.`

## Utiliser votre modele `.pth`

Placez votre fichier dans ce dossier avec le nom `model.pth`, ou cliquez sur `Changer modele .pth` dans l'interface.

Le fichier `model_loader.py` contient une architecture CNN par defaut. Si votre `.pth` a ete entraine avec une autre architecture, remplacez la classe `SmallEmotionCNN` par la meme architecture que celle utilisee pendant l'entrainement.
