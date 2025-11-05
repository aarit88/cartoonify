document.addEventListener('DOMContentLoaded', () => {
  // DOM
  const fileInput = document.getElementById('file-input');
  const uploadArea = document.getElementById('upload-area');

  const uploadForm = document.getElementById('upload-form');
  const blurType = document.getElementById('blur-type');
  const quantizer = document.getElementById('quantizer');
  const numColors = document.getElementById('num-colors');
  const lineStrength = document.getElementById('line-strength');
  const targetLongSide = document.getElementById('target-long-side');
  const upscaleSmall = document.getElementById('upscale-small');

  const labelColors = document.getElementById('label-colors');
  const labelEdge = document.getElementById('label-edge');

  const stage = document.getElementById('stage');
  const stageInner = document.getElementById('stage-inner');
  const beforeImg = document.getElementById('img-before');
  const afterImg = document.getElementById('img-after');
  const handle = document.getElementById('ba-handle');
  const empty = document.getElementById('empty-state');
  const loader = document.getElementById('loader');

  const bottomBar = document.getElementById('bottom-bar');
  const downloadBtn = document.getElementById('download-btn');
  const status = document.getElementById('status');

  const zoomInBtn = document.getElementById('zoom-in');
  const zoomOutBtn = document.getElementById('zoom-out');
  const zoomFitBtn = document.getElementById('zoom-fit');
  const zoomLevelLabel = document.getElementById('zoom-level');
  const openFileBtn = document.getElementById('open-file');
  const quickBtn = document.getElementById('quick-cartoon');

  // State
  let zoom = 1.0;
  let split = 50;
  let hasImage = false;

  // ===== helpers =====
  const setZoom = (z) => {
    zoom = Math.max(0.25, Math.min(4, z));
    stageInner.style.transform = `scale(${zoom})`;
    zoomLevelLabel.textContent = `${Math.round(zoom * 100)}%`;
  };
  const fitToStage = () => {
    const pad = 32;
    const rect = stage.getBoundingClientRect();
    const w = rect.width - pad;
    const h = rect.height - pad;
    const baseW = stageInner.clientWidth || 1200;
    const baseH = stageInner.clientHeight || 800;
    const factor = Math.max(0.25, Math.min(4, Math.min(w / baseW, h / baseH)));
    setZoom(factor);
  };
  const setSplit = (pct) => {
    split = Math.max(0, Math.min(100, pct));
    const right = 100 - split;
    afterImg.style.clipPath = `inset(0 ${right}% 0 0)`;
    handle.style.left = `${split}%`;
    handle.setAttribute('aria-valuenow', String(split));
  };
  const setStatus = (msg) => { status.textContent = msg; };
  const showCanvas = () => {
    stage.classList.add('has-image');
    if (empty) empty.hidden = true;
    bottomBar.hidden = false;
    beforeImg.style.display = 'block';
    afterImg.style.display = 'block';
  };

  // labels
  const fmt = (val, step) => (String(step).includes('.') ? Number(val).toFixed(1) : String(val));
  const refreshLabels = () => {
    labelColors.textContent = fmt(numColors.value, numColors.step || 1);
    labelEdge.textContent   = fmt(lineStrength.value, lineStrength.step || 1);
  };

  // ===== init =====
  refreshLabels();
  setSplit(50);
  setZoom(1);

  // ===== dropzone =====
  // Label auto-opens the file input on click. Do NOT call fileInput.click() here.
  // Drag & drop visuals
  ['dragenter','dragover'].forEach(ev =>
    uploadArea.addEventListener(ev, e => { e.preventDefault(); uploadArea.style.boxShadow = 'var(--ring)'; })
  );
  ['dragleave','drop'].forEach(ev =>
    uploadArea.addEventListener(ev, e => { e.preventDefault(); uploadArea.style.boxShadow = ''; })
  );
  uploadArea.addEventListener('drop', e => {
    const f = e.dataTransfer.files?.[0];
    if (f) { fileInput.files = e.dataTransfer.files; loadFile(f); }
  });

  // Topbar buttons
  openFileBtn.addEventListener('click', () => fileInput.click());
  quickBtn.addEventListener('click', () => uploadForm.requestSubmit());

  // Zoom + resize
  zoomInBtn.addEventListener('click', () => setZoom(zoom * 1.1));
  zoomOutBtn.addEventListener('click', () => setZoom(zoom / 1.1));
  zoomFitBtn.addEventListener('click', fitToStage);
  window.addEventListener('resize', () => { if (hasImage) fitToStage(); });

  // Slider labels live update
  ['input','change','keyup','pointerup'].forEach(ev => {
    numColors.addEventListener(ev, refreshLabels);
    lineStrength.addEventListener(ev, refreshLabels);
  });

  // File load
  const loadFile = (file) => {
    const reader = new FileReader();
    reader.onload = e => {
      beforeImg.src = e.target.result;
      afterImg.removeAttribute('src');
      downloadBtn.hidden = true;
      showCanvas();
      hasImage = true;
      fitToStage();
      setStatus('Image loaded');
    };
    reader.readAsDataURL(file);
  };

  fileInput.addEventListener('change', function () {
    const f = this.files?.[0];
    if (f) loadFile(f);
  });

  // BA slider drag
  const onMove = (clientX) => {
    const rect = stageInner.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setSplit(pct);
  };
  let dragging = false;
  handle.addEventListener('mousedown', e => { dragging = true; e.preventDefault(); });
  stageInner.addEventListener('mousedown', e => { dragging = true; onMove(e.clientX); });
  window.addEventListener('mousemove', e => { if (dragging) onMove(e.clientX); });
  window.addEventListener('mouseup', () => dragging = false);
  handle.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') setSplit(split - 2);
    if (e.key === 'ArrowRight') setSplit(split + 2);
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input,select,textarea')) return;
    if (e.key.toLowerCase() === 'o') { fileInput.click(); }
    if (e.key.toLowerCase() === 'r') { uploadForm.requestSubmit(); }
    if (e.key.toLowerCase() === 'f') { fitToStage(); }
    if (e.key === '+' || e.key === '=') { setZoom(zoom * 1.1); }
    if (e.key === '-' || e.key === '_') { setZoom(zoom / 1.1); }
  });

  // Submit to backend
  uploadForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const srcFile = fileInput.files?.[0];
    if (!srcFile) { setStatus('Select an image first'); return; }

    stage.classList.add('has-image');
    if (empty) empty.hidden = true;

    loader.hidden = false; setStatus('Processing…');

    const formData = new FormData(uploadForm);
    formData.set('file', srcFile);
    formData.set('blur_type', blurType.value);
    formData.set('quantizer', quantizer.value);
    formData.set('num_colors', numColors.value);
    formData.set('line_strength', lineStrength.value);
    formData.set('target_long_side', targetLongSide.value);
    formData.set('upscale_small', upscaleSmall.checked ? 'true' : 'false');

    fetch('/upload', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        const url = data.cartoon_image_url + '?t=' + Date.now();
        afterImg.onload = () => {
          loader.hidden = true;
          downloadBtn.href = url;
          downloadBtn.hidden = false;
          setStatus('Done');
          setSplit(50);
          fitToStage();
        };
        afterImg.src = url;
      })
      .catch(err => {
        loader.hidden = true;
        setStatus(err.message || 'Failed');
      });
  });
});
