const API_BASE = "http://127.0.0.1:5000/api";

const pages = document.querySelectorAll(".page");
const pageButtons = document.querySelectorAll("[data-page]");
const modelStatus = document.querySelector("#modelStatus");
const welcomeText = document.querySelector("#welcomeText");

function showPage(id) {
  pages.forEach((page) => page.classList.toggle("active", page.id === id));
  if (id === "datasetPage") {
    loadDatasetImages();
  }
}

pageButtons.forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.page));
});

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormMessage("loginMessage", "Verification en cours...");
  const email = document.querySelector("#loginEmail").value.trim();
  const password = document.querySelector("#loginPassword").value;
  const data = await postJson("/auth/login", { email, password });

  if (data.error) {
    setFormMessage("loginMessage", data.error);
    return;
  }

  setFormMessage("loginMessage", "");
  welcomeText.textContent = `Bienvenue ${data.username}`;
  showPage("homePage");
});

document.querySelector("#registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormMessage("registerMessage", "Creation du compte...");
  const username = document.querySelector("#registerUsername").value.trim();
  const email = document.querySelector("#registerEmail").value.trim();
  const password = document.querySelector("#registerPassword").value;
  const confirmPassword = document.querySelector("#registerConfirmPassword").value;
  const data = await postJson("/auth/register", { username, email, password, confirmPassword });

  if (data.error) {
    setFormMessage("registerMessage", data.error);
    return;
  }

  document.querySelector("#registerForm").reset();
  setFormMessage("registerMessage", "");
  setFormMessage("loginMessage", data.message, true);
  showPage("loginPage");
});

document.querySelector("#logoutButton").addEventListener("click", () => {
  document.querySelector("#loginForm").reset();
  showPage("loginPage");
});

async function refreshModelStatus() {
  try {
    const response = await fetch(`${API_BASE}/model/status`);
    const data = await response.json();
    modelStatus.textContent = formatModelStatus(data);
  } catch {
    modelStatus.textContent = "Backend non lance";
  }
}

document.querySelector("#modelInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  modelStatus.textContent = "Chargement du modele...";
  const formData = new FormData();
  formData.append("model", file);
  const data = await postForm("/model/load", formData);
  if (data.error) {
    modelStatus.textContent = data.error;
    return;
  }
  modelStatus.textContent = formatModelStatus(data);
});

function formatModelStatus(data) {
  if (!data.ready) return data.message || "Mode demo: modele non charge";

  const modelName = data.model_name || "model.pth";
  return `Modele charge: ${modelName}`;
}

const imageInput = document.querySelector("#imageInput");
const imagePreview = document.querySelector("#imagePreview");
const imageResult = document.querySelector("#imageResult");
const imageProbabilities = document.querySelector("#imageProbabilities");

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) return;
  imagePreview.src = URL.createObjectURL(file);
  imagePreview.classList.remove("hidden-media");
  setResult(imageResult, "Image chargee. Cliquez sur Detect emotion.");
  renderProbabilities(imageProbabilities, {});
});

document.querySelector("#detectImage").addEventListener("click", async () => {
  const file = imageInput.files[0];
  if (!file) return setResult(imageResult, "Choisissez une image.");

  const formData = new FormData();
  formData.append("image", file);
  const data = await postForm("/predict/image", formData);
  if (data.preview) {
    imagePreview.src = data.preview;
    imagePreview.classList.remove("hidden-media");
  }
  setPrediction(imageResult, imageProbabilities, data);
});

const videoInput = document.querySelector("#videoInput");
const videoPreview = document.querySelector("#videoPreview");
const videoFramePreview = document.querySelector("#videoFramePreview");
const videoCanvas = document.querySelector("#videoCanvas");
const videoResult = document.querySelector("#videoResult");
const videoProbabilities = document.querySelector("#videoProbabilities");

videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];
  if (file) {
    videoPreview.src = URL.createObjectURL(file);
    videoFramePreview.classList.add("hidden-media");
    setResult(videoResult, "Video chargee. Choisissez une frame puis detectez.");
    renderProbabilities(videoProbabilities, {});
  }
});

document.querySelector("#detectVideoFrame").addEventListener("click", async () => {
  if (!videoPreview.src) return setResult(videoResult, "Choisissez une video.");
  if (!videoPreview.videoWidth || !videoPreview.videoHeight) {
    return setResult(videoResult, "La video n'est pas encore prete. Lancez la lecture ou attendez une seconde.");
  }
  const frame = captureVideoFrame(videoPreview, videoCanvas);
  if (!frame) return setResult(videoResult, "Frame video invalide.");
  const data = await postJson("/predict/frame", { image: frame });
  if (data.preview) {
    videoFramePreview.src = data.preview;
    videoFramePreview.classList.remove("hidden-media");
  }
  setPrediction(videoResult, videoProbabilities, data);
});

const cameraPreview = document.querySelector("#cameraPreview");
const livePreview = document.querySelector("#livePreview");
const liveCanvas = document.querySelector("#liveCanvas");
const liveResult = document.querySelector("#liveResult");
const liveProbabilities = document.querySelector("#liveProbabilities");
const datasetGrid = document.querySelector("#datasetGrid");
const datasetResult = document.querySelector("#datasetResult");
const datasetProbabilities = document.querySelector("#datasetProbabilities");
let selectedDatasetImageId = null;

document.querySelector("#startCamera").addEventListener("click", async () => {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setResult(liveResult, "Camera bloquee: ouvrez le site avec http://127.0.0.1:5500");
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    cameraPreview.srcObject = stream;
    await cameraPreview.play();
    cameraPreview.classList.remove("hidden-media");
    livePreview.classList.add("hidden-media");
    setResult(liveResult, "Camera demarree. Cliquez sur Detect emotion.");
    renderProbabilities(liveProbabilities, {});
  } catch (error) {
    setResult(liveResult, `Camera indisponible: ${error.message}`);
  }
});

document.querySelector("#detectLive").addEventListener("click", async () => {
  if (!cameraPreview.srcObject) return setResult(liveResult, "Demarrez la camera.");
  if (!cameraPreview.videoWidth || !cameraPreview.videoHeight) {
    return setResult(liveResult, "Camera pas encore prete. Attendez une seconde puis reessayez.");
  }
  const frame = captureVideoFrame(cameraPreview, liveCanvas);
  if (!frame) return setResult(liveResult, "Frame camera invalide.");
  const data = await postJson("/predict/frame", { image: frame });
  if (data.preview) {
    livePreview.src = data.preview;
    livePreview.classList.remove("hidden-media");
  }
  setPrediction(liveResult, liveProbabilities, data);
});

document.querySelector("#reloadDataset").addEventListener("click", loadDatasetImages);

document.querySelector("#syncDataset").addEventListener("click", async () => {
  setResult(datasetResult, "Synchronisation...");
  const data = await postJson("/dataset/sync", {});
  if (data.error) return setResult(datasetResult, data.error);
  await loadDatasetImages();
  setResult(datasetResult, `Images Disgust importees: ${data.total}`);
});

document.querySelector("#detectDatasetImage").addEventListener("click", async () => {
  if (!selectedDatasetImageId) return setResult(datasetResult, "Selectionnez une image Disgust.");
  setResult(datasetResult, "Detection...");
  const data = await postJson(`/predict/dataset/${selectedDatasetImageId}`, {});
  setPrediction(datasetResult, datasetProbabilities, data);
});

async function loadDatasetImages() {
  if (!datasetGrid) return;
  datasetGrid.innerHTML = "";
  selectedDatasetImageId = null;
  renderProbabilities(datasetProbabilities, {});
  setResult(datasetResult, "Lecture de la base...");

  try {
    const response = await fetch(`${API_BASE}/dataset/images?label=Disgust&limit=48`);
    const data = await response.json();
    if (!response.ok || data.error) {
      setResult(datasetResult, data.error || "Erreur lecture base.");
      return;
    }

    if (!data.images.length) {
      setResult(datasetResult, "Aucune image Disgust dans la base.");
      return;
    }

    datasetGrid.innerHTML = data.images
      .map(
        (image) => `
          <button class="dataset-item" type="button" data-id="${image.id}">
            <img src="${API_BASE.replace("/api", "")}${image.image_url}" alt="${image.filename}" />
            <span>${image.label}</span>
          </button>
        `
      )
      .join("");

    datasetGrid.querySelectorAll(".dataset-item").forEach((button) => {
      button.addEventListener("click", () => {
        datasetGrid.querySelectorAll(".dataset-item").forEach((item) => item.classList.remove("selected"));
        button.classList.add("selected");
        selectedDatasetImageId = button.dataset.id;
        setResult(datasetResult, "Image Disgust selectionnee.");
        renderProbabilities(datasetProbabilities, {});
      });
    });

    setResult(datasetResult, `${data.images.length} images Disgust lues depuis la base.`);
  } catch {
    setResult(datasetResult, "Backend non lance. Demarrez python backend/server.py");
  }
}

function captureVideoFrame(video, canvas) {
  if (!video.videoWidth || !video.videoHeight) return "";
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d");
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.9);
}

async function postForm(path, body) {
  try {
    const response = await fetch(`${API_BASE}${path}`, { method: "POST", body });
    const data = await response.json();
    if (!response.ok && !data.error) {
      data.error = data.message || "Erreur serveur.";
    }
    return data;
  } catch {
    return { error: "Backend non lance. Demarrez python backend/server.py" };
  }
}

async function postJson(path, body) {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok && !data.error) {
      data.error = data.message || "Erreur serveur.";
    }
    return data;
  } catch {
    return { error: "Backend non lance. Demarrez python backend/server.py" };
  }
}

function setPrediction(target, probabilitiesTarget, data) {
  if (data.error) {
    renderProbabilities(probabilitiesTarget, {});
    if (data.preview) {
      showReturnedPreview(data.preview);
    }
    return setResult(target, data.error);
  }
  const label = data.label || data.result || "--";
  const confidence = Number(data.confidence || 0);
  const probabilities = data.probabilities || data.percentages || {};
  const percent = Math.round(confidence * 100);
  const faceText = data.face_found === false ? " | Analyse sur image complete" : "";
  const databaseText = data.database_label ? ` | Classe DB: ${data.database_label}` : "";
  setResult(target, `Resultat: ${label} | Confiance: ${percent}%${faceText}${databaseText}`);
  renderProbabilities(probabilitiesTarget, probabilities);
}

function showReturnedPreview(preview) {
  if (document.querySelector("#livePage").classList.contains("active")) {
    livePreview.src = preview;
    livePreview.classList.remove("hidden-media");
  }
  if (document.querySelector("#videoPage").classList.contains("active")) {
    videoFramePreview.src = preview;
    videoFramePreview.classList.remove("hidden-media");
  }
}

function setResult(target, text) {
  target.textContent = text;
}

function setFormMessage(id, text, success = false) {
  const target = document.querySelector(`#${id}`);
  target.textContent = text;
  target.classList.toggle("success", success);
}

function renderProbabilities(target, probabilities) {
  const entries = Object.entries(probabilities);
  if (!entries.length) {
    target.innerHTML = "";
    return;
  }

  target.innerHTML = entries
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => {
      const percent = Math.round(value * 100);
      return `
        <div class="probability-row">
          <span>${label}</span>
          <div class="probability-bar"><div class="probability-fill" style="width: ${percent}%"></div></div>
          <strong>${percent}%</strong>
        </div>
      `;
    })
    .join("");
}

refreshModelStatus();
