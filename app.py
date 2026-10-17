import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency at runtime
    cv2 = None

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - optional dependency at runtime
    Image = None
    ImageTk = None

from model_loader import EmotionPredictor


APP_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = APP_DIR / "model.pth"


class EmotionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Emotion AI Studio")
        self.geometry("1160x720")
        self.minsize(980, 620)
        self.configure(bg="#eef4ff")

        self.predictor = EmotionPredictor(DEFAULT_MODEL)
        self.current_image = None
        self.current_frame = None
        self.preview_photo = None
        self.camera = None
        self.camera_running = False
        self.video_running = False

        self._configure_theme()
        self._build_layout()
        self.show_page("login")

    def _configure_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#eef4ff")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Dark.TFrame", background="#101828")
        style.configure("Title.TLabel", background="#eef4ff", foreground="#132238", font=("Segoe UI", 26, "bold"))
        style.configure("Muted.TLabel", background="#eef4ff", foreground="#5c6f89", font=("Segoe UI", 11))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#132238", font=("Segoe UI", 18, "bold"))
        style.configure("PanelText.TLabel", background="#ffffff", foreground="#667085", font=("Segoe UI", 10))
        style.configure("Result.TLabel", background="#ffffff", foreground="#0f766e", font=("Segoe UI", 16, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 10))
        style.configure("Ghost.TButton", font=("Segoe UI", 10), padding=(14, 8))

    def _build_layout(self):
        self.shell = ttk.Frame(self, padding=22)
        self.shell.pack(fill="both", expand=True)

        self.header = ttk.Frame(self.shell)
        self.header.pack(fill="x", pady=(0, 18))
        ttk.Label(self.header, text="Emotion AI Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(
            self.header,
            text="Detection emotion: image, video et camera live avec modele .pth",
            style="Muted.TLabel",
        ).pack(side="left", padx=18, pady=(12, 0))

        self.container = ttk.Frame(self.shell)
        self.container.pack(fill="both", expand=True)

        self.pages = {}
        for name, builder in {
            "login": self._build_login,
            "register": self._build_register,
            "home": self._build_home,
            "image": self._build_image_page,
            "video": self._build_video_page,
            "live": self._build_live_page,
        }.items():
            frame = ttk.Frame(self.container)
            frame.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = frame
            builder(frame)

        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

    def show_page(self, page_name):
        self.stop_camera()
        self.video_running = False
        self.pages[page_name].tkraise()

    def _auth_card(self, parent, title, subtitle, fields, button_text, action, switch_text, switch_page):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        left = ttk.Frame(parent, style="Dark.TFrame", padding=42)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        tk.Label(
            left,
            text="Analyse intelligente\ndes emotions",
            bg="#101828",
            fg="#ffffff",
            font=("Segoe UI", 30, "bold"),
            justify="left",
        ).pack(anchor="w", pady=(70, 14))
        tk.Label(
            left,
            text="Une interface moderne pour tester votre reseau CNN/PyTorch en mode image, video ou camera.",
            bg="#101828",
            fg="#a7b5ca",
            font=("Segoe UI", 13),
            justify="left",
            wraplength=410,
        ).pack(anchor="w")
        tk.Frame(left, bg="#22d3ee", height=5, width=150).pack(anchor="w", pady=32)

        card = ttk.Frame(parent, style="Panel.TFrame", padding=42)
        card.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
        ttk.Label(card, text=title, style="PanelTitle.TLabel").pack(anchor="w", pady=(55, 6))
        ttk.Label(card, text=subtitle, style="PanelText.TLabel").pack(anchor="w", pady=(0, 24))

        entries = {}
        for label, secret in fields:
            ttk.Label(card, text=label, style="PanelText.TLabel").pack(anchor="w", pady=(10, 5))
            entry = ttk.Entry(card, show="*" if secret else "", font=("Segoe UI", 11))
            entry.pack(fill="x", ipady=9)
            entries[label] = entry

        ttk.Button(card, text=button_text, style="Accent.TButton", command=action).pack(fill="x", pady=(28, 10))
        ttk.Button(card, text=switch_text, style="Ghost.TButton", command=lambda: self.show_page(switch_page)).pack(fill="x")

    def _build_login(self, parent):
        self._auth_card(
            parent,
            "Connexion",
            "Connectez-vous pour acceder au tableau de bord.",
            [("Email", False), ("Password", True)],
            "Login",
            lambda: self.show_page("home"),
            "Creer un nouveau compte",
            "register",
        )

    def _build_register(self, parent):
        self._auth_card(
            parent,
            "Inscription",
            "Creez un compte local pour la demonstration.",
            [("Username", False), ("Email", False), ("Password", True), ("Confirm Password", True)],
            "Sign up",
            lambda: self.show_page("home"),
            "J'ai deja un compte",
            "login",
        )

    def _build_home(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        top = ttk.Frame(parent)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Home Page", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Changer modele .pth", style="Ghost.TButton", command=self.choose_model).pack(side="right")

        cards = ttk.Frame(parent)
        cards.grid(row=1, column=0, sticky="nsew", pady=32)
        for i in range(3):
            cards.columnconfigure(i, weight=1)

        self._mode_card(cards, 0, "Video", "Tester une video locale", "#2563eb", "Ouvrir", lambda: self.show_page("video"))
        self._mode_card(cards, 1, "Image", "Importer une image", "#0f766e", "Ouvrir", lambda: self.show_page("image"))
        self._mode_card(cards, 2, "Live cam", "Detection par webcam", "#7c3aed", "Ouvrir", lambda: self.show_page("live"))

        status = (
            f"Modele charge: {self.predictor.model_name}"
            if self.predictor.ready
            else "Modele non charge: mode demo"
        )
        ttk.Label(parent, text=status, style="Muted.TLabel").grid(row=2, column=0, sticky="w")

    def _mode_card(self, parent, column, title, text, color, button, command):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=28)
        card.grid(row=0, column=column, sticky="nsew", padx=12)
        icon = tk.Canvas(card, width=82, height=82, bg="#ffffff", highlightthickness=0)
        icon.create_oval(8, 8, 74, 74, fill=color, outline="")
        icon.create_text(41, 41, text=title[0], fill="#ffffff", font=("Segoe UI", 26, "bold"))
        icon.pack(pady=(8, 20))
        ttk.Label(card, text=title, style="PanelTitle.TLabel").pack()
        ttk.Label(card, text=text, style="PanelText.TLabel").pack(pady=(8, 24))
        ttk.Button(card, text=button, style="Accent.TButton", command=command).pack()

    def _build_detection_page(self, parent, title, pick_text, pick_command, detect_command):
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(1, weight=1)

        bar = ttk.Frame(parent)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Button(bar, text="< Home", style="Ghost.TButton", command=lambda: self.show_page("home")).pack(side="left")
        ttk.Label(bar, text=title, style="Title.TLabel").pack(side="left", padx=18)

        preview_panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        preview_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        preview_panel.rowconfigure(0, weight=1)
        preview_panel.columnconfigure(0, weight=1)
        self.preview = tk.Label(preview_panel, text="Aucun media selectionne", bg="#0f172a", fg="#d8e3f0", font=("Segoe UI", 15))
        self.preview.grid(row=0, column=0, sticky="nsew")

        side = ttk.Frame(parent, style="Panel.TFrame", padding=28)
        side.grid(row=1, column=1, sticky="nsew")
        ttk.Label(side, text="Detection", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            side,
            text="Chargez un media puis lancez la prediction. Le fichier model.pth peut etre remplace dans ce dossier.",
            style="PanelText.TLabel",
            wraplength=330,
        ).pack(anchor="w", pady=(8, 24))
        ttk.Button(side, text=pick_text, style="Ghost.TButton", command=pick_command).pack(fill="x", pady=6)
        ttk.Button(side, text="Detect emotion", style="Accent.TButton", command=detect_command).pack(fill="x", pady=6)
        ttk.Button(side, text="Changer modele .pth", style="Ghost.TButton", command=self.choose_model).pack(fill="x", pady=6)
        self.result_label = ttk.Label(side, text="Resultat: --", style="Result.TLabel")
        self.result_label.pack(anchor="w", pady=(28, 8))
        self.confidence_label = ttk.Label(side, text="Confiance: --", style="PanelText.TLabel")
        self.confidence_label.pack(anchor="w")

    def _build_image_page(self, parent):
        self._build_detection_page(parent, "Image mode", "Choisir image", self.pick_image, self.detect_current)

    def _build_video_page(self, parent):
        self._build_detection_page(parent, "Video mode", "Choisir video", self.pick_video, self.detect_current)

    def _build_live_page(self, parent):
        self._build_detection_page(parent, "Live mode", "Demarrer camera", self.start_camera, self.detect_current)

    def choose_model(self):
        path = filedialog.askopenfilename(filetypes=[("PyTorch model", "*.pth *.pt"), ("All files", "*.*")])
        if not path:
            return
        self.predictor = EmotionPredictor(Path(path))
        if self.predictor.ready:
            messagebox.showinfo(
                "Modele",
                f"Modele charge: {self.predictor.model_name}\n{path}",
            )
        else:
            messagebox.showwarning("Modele", self.predictor.last_error or "Impossible de charger ce modele.")

    def pick_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")])
        if not path:
            return
        self.current_image = path
        self.current_frame = None
        self.show_image(path)

    def pick_video(self):
        if cv2 is None:
            messagebox.showerror("Dependance", "Installez opencv-python pour lire les videos.")
            return
        path = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")])
        if not path:
            return
        self.video_running = True
        threading.Thread(target=self._play_video, args=(path,), daemon=True).start()

    def _play_video(self, path):
        cap = cv2.VideoCapture(path)
        while self.video_running and cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            self.current_frame = frame
            self.after(0, self._show_cv_frame, frame)
            time.sleep(0.03)
        cap.release()

    def start_camera(self):
        if cv2 is None:
            messagebox.showerror("Dependance", "Installez opencv-python pour utiliser la camera.")
            return
        self.stop_camera()
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            messagebox.showerror("Camera", "Camera introuvable.")
            return
        self.camera_running = True
        self._camera_loop()

    def _camera_loop(self):
        if not self.camera_running or self.camera is None:
            return
        ok, frame = self.camera.read()
        if ok:
            self.current_frame = frame
            self._show_cv_frame(self._draw_face_boxes(frame))
        self.after(20, self._camera_loop)

    def stop_camera(self):
        self.camera_running = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def show_image(self, path):
        if Image is None or ImageTk is None:
            self.preview.configure(text=path)
            return
        image = Image.open(path).convert("RGB")
        self._show_pil_image(image)

    def _show_cv_frame(self, frame):
        if Image is None or ImageTk is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._show_pil_image(Image.fromarray(rgb))

    def _show_pil_image(self, image):
        max_w = max(self.preview.winfo_width(), 640)
        max_h = max(self.preview.winfo_height(), 420)
        image.thumbnail((max_w, max_h))
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="", bg="#0f172a")

    def detect_current(self):
        source = self.current_frame if self.current_frame is not None else self.current_image
        if source is None:
            messagebox.showinfo("Detection", "Choisissez une image, une video ou demarrez la camera.")
            return
        prediction = self.predictor.predict(source)
        label = prediction.get("label", "--") if isinstance(prediction, dict) else prediction[0]
        confidence = prediction.get("confidence", 0.0) if isinstance(prediction, dict) else prediction[1]
        if isinstance(source, str):
            self._show_path_with_boxes(source)
        elif cv2 is not None:
            self._show_cv_frame(self._draw_face_boxes(source))
        self.result_label.configure(text=f"Resultat: {label}")
        self.confidence_label.configure(text=f"Confiance: {confidence:.1%}")

    def _show_path_with_boxes(self, path):
        if cv2 is None:
            return
        frame = cv2.imread(path)
        if frame is not None:
            self._show_cv_frame(self._draw_face_boxes(frame))

    def _draw_face_boxes(self, frame):
        if cv2 is None:
            return frame
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return frame
        output = frame.copy()
        gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        for x, y, w, h in faces:
            cv2.rectangle(output, (x, y), (x + w, y + h), (34, 211, 238), 2)
            cv2.putText(output, "Face", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (34, 211, 238), 2)
        return output

    def destroy(self):
        self.stop_camera()
        super().destroy()


if __name__ == "__main__":
    app = EmotionApp()
    app.mainloop()
