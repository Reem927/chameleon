import addOnUISdk from "https://new.express.adobe.com/static/add-on-sdk/sdk.js";

// Viewer only: reads files the user picks, never fetches anything and never
// changes image pixels. The PNG goes into the document exactly as rendered.

const filesInput = document.getElementById("files");
const addButton = document.getElementById("add-image");
const preview = document.getElementById("preview");
const errorText = document.getElementById("error");
const fields = {
    name: document.getElementById("design-name"),
    canvas: document.getElementById("canvas-size"),
    count: document.getElementById("element-count"),
    png: document.getElementById("png-size")
};

let pngFile = null;
let sdkReady = false;

function showError(message) {
    errorText.textContent = message;
    errorText.hidden = !message;
}

function updateButton() {
    addButton.disabled = !(sdkReady && pngFile);
}

// Accepts an output design {canvas, elements}; a task file keeps it under "source".
function readDesign(text) {
    const data = JSON.parse(text);
    const design = data && data.canvas ? data : data && data.source;
    if (!design || !design.canvas || !Array.isArray(design.elements)) {
        throw new Error("JSON has no canvas and elements list");
    }
    return design;
}

async function showJson(file) {
    try {
        const design = readDesign(await file.text());
        fields.name.textContent = file.name;
        fields.canvas.textContent = `${design.canvas.width} x ${design.canvas.height}`;
        fields.count.textContent = String(design.elements.length);
    } catch (error) {
        showError(`${file.name}: ${error.message}`);
    }
}

function showPng(file) {
    pngFile = file;
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.onload = () => {
        fields.png.textContent = `${preview.naturalWidth} x ${preview.naturalHeight}`;
    };
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    updateButton();
}

filesInput.addEventListener("change", async () => {
    showError("");
    for (const file of filesInput.files) {
        if (file.name.toLowerCase().endsWith(".json")) await showJson(file);
        else if (file.type === "image/png") showPng(file);
    }
});

addButton.addEventListener("click", async () => {
    addButton.disabled = true;
    try {
        await addOnUISdk.app.document.addImage(pngFile, { title: pngFile.name });
    } catch (error) {
        showError(`Could not add the image: ${error.message}`);
    }
    updateButton();
});

addOnUISdk.ready.then(() => {
    sdkReady = true;
    updateButton();
});
