from pathlib import Path


DEFAULT_LABELS = ["Disgust", "Angry", "Happy", "Neutral", "Sad", "Surprise"]
DEFAULT_LABELS_7 = ["Angry", "Disgust", "Fear", "Happy", "Neutral", "Sad", "Surprise"]
DISPLAY_LABEL_REPLACEMENTS = {}


 
class EmotionPredictor:
    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self.model_name = self.model_path.name
        self.architecture = ""
        self.ready = False
        self.last_error = ""
        self.model = None
        self.torch = None
        self.labels = DEFAULT_LABELS
        self.input_size = 224
        self.rgb_input = True
        self._load()

    def _load(self):
        if not self.model_path.exists():
            self.last_error = f"Modele introuvable: {self.model_path}"
            return
        try:
            import torch
        except Exception as exc:
            self.last_error = f"PyTorch non installe: {exc}"
            return

        self.torch = torch

        try:
            try:
                loaded = torch.load(self.model_path, map_location="cpu", weights_only=False)
            except TypeError:
                loaded = torch.load(self.model_path, map_location="cpu")
            if hasattr(loaded, "eval"):
                self.model = loaded
                self.architecture = loaded.__class__.__name__
                self._configure_labels_from_model()
            else:
                state_dict = self._extract_state_dict(loaded)
                state_dict = self._normalize_state_dict_keys(state_dict)
                self.model = self._build_model_from_state_dict(state_dict)
                self.model.load_state_dict(state_dict, strict=True)
            self.model.eval()
            self.ready = True
        except Exception as exc:
            self.last_error = f"Modele .pth non charge: {exc}"

    def _extract_state_dict(self, loaded):
        if not isinstance(loaded, dict):
            return loaded
        for key in ("state_dict", "model_state_dict", "model"):
            value = loaded.get(key)
            if isinstance(value, dict):
                return value
        return loaded

    def _normalize_state_dict_keys(self, state_dict):
        if not hasattr(state_dict, "items"):
            return state_dict

        normalized = {}
        for key, value in state_dict.items():
            clean_key = key
            for prefix in ("module.", "model."):
                if clean_key.startswith(prefix):
                    clean_key = clean_key[len(prefix):]
            normalized[clean_key] = value
        return normalized

    def _build_model_from_state_dict(self, state_dict):
        classifier_weight = state_dict.get("classifier.weight")
        if classifier_weight is None:
            classifier_weight = state_dict.get("head.fc.weight")
        if classifier_weight is None:
            classifier_weight = state_dict.get("classifier.1.weight")
        if classifier_weight is None:
            raise ValueError("poids de classification introuvables dans le fichier .pth")

        num_classes = int(classifier_weight.shape[0])
        self._set_labels(num_classes)

        if "conv_stem.weight" in state_dict and "blocks.0.0.conv_dw.weight" in state_dict:
            try:
                import timm
            except Exception as exc:
                raise ImportError("Installez timm avec: pip install timm") from exc
            self.architecture = "efficientnet_b0"
            return timm.create_model("efficientnet_b0", pretrained=False, num_classes=num_classes)

        if "stem.conv.weight" in state_dict and "features.16.conv.weight" in state_dict and "head.fc.weight" in state_dict:
            try:
                import timm
            except Exception as exc:
                raise ImportError("Installez timm avec: pip install timm") from exc
            self.architecture = "rexnet_150"
            return timm.create_model("rexnet_150", pretrained=False, num_classes=num_classes)

        if "features.0.0.weight" in state_dict and "features.8.0.weight" in state_dict and "classifier.1.weight" in state_dict:
            try:
                from torchvision import models
            except Exception as exc:
                raise ImportError("Installez torchvision avec: pip install torchvision") from exc
            self.architecture = "efficientnet_b4"
            return models.efficientnet_b4(weights=None, num_classes=num_classes)

        raise ValueError("Architecture non reconnue. Ce .pth ne correspond pas au chargeur actuel.")

    def _configure_labels_from_model(self):
        classifier = getattr(self.model, "classifier", None)
        head = getattr(self.model, "head", None)
        head_fc = getattr(head, "fc", None)
        classifier_head = classifier[-1] if hasattr(classifier, "__getitem__") else classifier
        out_features = getattr(classifier_head, "out_features", None) or getattr(head_fc, "out_features", len(DEFAULT_LABELS))
        self._set_labels(out_features)

    def _set_labels(self, num_classes):
        source_labels = DEFAULT_LABELS_7 if num_classes == len(DEFAULT_LABELS_7) else DEFAULT_LABELS
        self.labels = source_labels[:num_classes]
        if len(self.labels) != num_classes:
            self.labels = [f"Class {i}" for i in range(num_classes)]

    def _display_label(self, label):
        return DISPLAY_LABEL_REPLACEMENTS.get(label, label)

    def display_labels(self):
        return list(dict.fromkeys(self._display_label(label) for label in self.labels))

    def predict(self, image_source):
        if not self.ready:
            return {
                "error": self.last_error or "Modele non charge.",
                "label": "--",
                "confidence": 0.0,
                "probabilities": {},
            }

        try:
            from PIL import Image
        except Exception:
            return {"label": "Erreur dependance image", "confidence": 0.0, "probabilities": {}}

        if isinstance(image_source, (str, Path)):
            image = Image.open(image_source).convert("RGB")
        else:
            # OpenCV frames arrive as BGR arrays.
            image = Image.fromarray(image_source[:, :, ::-1]).convert("RGB")

        tensor = self._preprocess(image)
        with self.torch.no_grad():
            logits = self.model(tensor)
            probs = self.torch.softmax(logits, dim=1)[0]
            confidence, index = self.torch.max(probs, dim=0)

        raw_label = self.labels[int(index)]
        label = self._display_label(raw_label)
        probabilities = {}
        for i, raw_probability in enumerate(probs):
            display_label = self._display_label(self.labels[i])
            probabilities[display_label] = probabilities.get(display_label, 0.0) + float(raw_probability)

        confidence_value = probabilities.get(label, float(confidence))
        return {"label": label, "confidence": confidence_value, "probabilities": probabilities}

    def _preprocess(self, image):
        image = image.resize((self.input_size, self.input_size)).convert("RGB")
        values = list(image.getdata())
        tensor = self.torch.tensor(values, dtype=self.torch.float32).view(1, self.input_size, self.input_size, 3)
        tensor = tensor.permute(0, 3, 1, 2) / 255.0
        mean = self.torch.tensor([0.485, 0.456, 0.406], dtype=self.torch.float32).view(1, 3, 1, 1)
        std = self.torch.tensor([0.229, 0.224, 0.225], dtype=self.torch.float32).view(1, 3, 1, 1)
        return (tensor - mean) / std

    def _result_from_scores(self, probabilities):
        label = max(probabilities, key=probabilities.get)
        return {"label": label, "confidence": probabilities[label], "probabilities": probabilities}
