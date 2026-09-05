(function () {
  const token = localStorage.getItem('pcupload_token');
  if (!token) {
    window.location.href = 'login.html';
    return;
  }

  const authHeaders = () => ({ Authorization: `Bearer ${token}` });

  const errorMsg = document.getElementById('errorMsg');
  const successMsg = document.getElementById('successMsg');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const statusSub = document.getElementById('statusSub');
  const wakeBtn = document.getElementById('wakeBtn');
  const shutdownBtn = document.getElementById('shutdownBtn');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const sendBtn = document.getElementById('sendBtn');
  const queueList = document.getElementById('queueList');
  const completedList = document.getElementById('completedList');
  const logoutBtn = document.getElementById('logoutBtn');

  let selectedFiles = [];       // Dateien, die der Nutzer ausgewaehlt hat, aber noch nicht gesendet
  let uploadsInProgress = {};   // id -> {name, pct, status}

  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.add('show');
    setTimeout(() => errorMsg.classList.remove('show'), 5000);
  }
  function showSuccess(msg) {
    successMsg.textContent = msg;
    successMsg.classList.add('show');
    setTimeout(() => successMsg.classList.remove('show'), 4000);
  }

  function handleAuthFailure(res) {
    if (res.status === 401) {
      localStorage.removeItem('pcupload_token');
      window.location.href = 'login.html';
      return true;
    }
    return false;
  }

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  }

  function iconFor(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (['jpg','jpeg','png','gif','webp','heic'].includes(ext)) return '🖼️';
    if (['mp4','mov','mkv','avi'].includes(ext)) return '🎬';
    if (['mp3','wav','flac'].includes(ext)) return '🎵';
    if (['pdf'].includes(ext)) return '📄';
    if (['zip','rar','7z'].includes(ext)) return '🗜️';
    return '📦';
  }

  const STATUS_LABELS = {
    offline: ['Offline', 'PC ist ausgeschaltet oder nicht erreichbar'],
    starting: ['Wird gestartet', 'Wake-on-LAN gesendet, warte auf PC...'],
    online: ['Online', 'PC-Client ist bereit'],
    transferring: ['Übertragung läuft', 'Dateien werden übertragen...'],
    done: ['Fertig', 'Letzte Übertragung abgeschlossen'],
  };

  // -------------------- Status Polling --------------------
  async function refreshStatus() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/status`, { headers: authHeaders() });
      if (handleAuthFailure(res)) return;
      if (!res.ok) throw new Error('Status konnte nicht geladen werden.');
      const data = await res.json();

      const [label, sub] = STATUS_LABELS[data.pc_status] || ['Unbekannt', ''];
      statusDot.className = `status-dot ${data.pc_status}`;
      statusText.textContent = label;
      statusSub.textContent = sub;

      renderCompleted(data.completed || []);
      renderServerQueue(data.queue || []);
    } catch (err) {
      statusText.textContent = 'Nicht erreichbar';
      statusSub.textContent = 'Backend antwortet nicht';
    }
  }

  function renderCompleted(items) {
    if (!items.length) {
      completedList.innerHTML = '<div class="empty-hint">Noch keine Übertragungen.</div>';
      return;
    }
    completedList.innerHTML = items.map(item => `
      <div class="file-item">
        <div class="file-icon">${iconFor(item.filename)}</div>
        <div class="file-meta">
          <div class="file-name">${escapeHtml(item.filename)}</div>
          <div class="file-size">${formatSize(item.size)}</div>
        </div>
        <div class="file-status done">✓ Übertragen</div>
      </div>
    `).join('');
  }

  function renderServerQueue(items) {
    if (!items.length && Object.keys(uploadsInProgress).length === 0 && !selectedFiles.length) {
      queueList.innerHTML = '<div class="empty-hint">Noch keine Dateien ausgewählt.</div>';
      return;
    }
    if (!items.length) return; // lokale Auswahl/Upload-Liste bleibt sichtbar, wird separat gerendert

    queueList.innerHTML = items.map(item => `
      <div class="file-item">
        <div class="file-icon">${iconFor(item.filename)}</div>
        <div class="file-meta">
          <div class="file-name">${escapeHtml(item.filename)}</div>
          <div class="file-size">${formatSize(item.size)}</div>
        </div>
        <div class="file-status">${item.status === 'downloading' ? 'Wird auf PC geladen...' : 'Wartet auf PC'}</div>
      </div>
    `).join('');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // -------------------- Datei-Auswahl (Drag & Drop) --------------------
  dropzone.addEventListener('click', (e) => {
    if (e.target.tagName !== 'LABEL') fileInput.click();
  });
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    addFiles(e.dataTransfer.files);
  });
  fileInput.addEventListener('change', () => addFiles(fileInput.files));

  function addFiles(fileList) {
    for (const f of fileList) selectedFiles.push(f);
    sendBtn.disabled = selectedFiles.length === 0;
    renderSelected();
  }

  function renderSelected() {
    if (!selectedFiles.length && Object.keys(uploadsInProgress).length === 0) return;
    const selectedHtml = selectedFiles.map((f, idx) => `
      <div class="file-item" data-idx="${idx}">
        <div class="file-icon">${iconFor(f.name)}</div>
        <div class="file-meta">
          <div class="file-name">${escapeHtml(f.name)}</div>
          <div class="file-size">${formatSize(f.size)}</div>
        </div>
        <div class="file-status">Bereit zum Senden</div>
      </div>
    `).join('');

    const uploadingHtml = Object.values(uploadsInProgress).map(u => `
      <div class="file-item">
        <div class="file-icon">${iconFor(u.name)}</div>
        <div class="file-meta">
          <div class="file-name">${escapeHtml(u.name)}</div>
          <div class="progress-track"><div class="progress-fill" style="width:${u.pct}%"></div></div>
        </div>
        <div class="file-status ${u.status === 'error' ? 'error' : ''}">${u.statusText}</div>
      </div>
    `).join('');

    queueList.innerHTML = uploadingHtml + selectedHtml || '<div class="empty-hint">Noch keine Dateien ausgewählt.</div>';
  }

  // -------------------- Senden (Upload) --------------------
  sendBtn.addEventListener('click', async () => {
    const filesToSend = selectedFiles;
    selectedFiles = [];
    sendBtn.disabled = true;

    for (const file of filesToSend) {
      uploadFile(file);
    }
  });

  function uploadFile(file) {
    const uploadId = `${file.name}_${Date.now()}_${Math.random()}`;
    uploadsInProgress[uploadId] = { name: file.name, pct: 0, status: 'uploading', statusText: 'Wird gesendet...' };
    renderSelected();

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BACKEND_URL}/api/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        uploadsInProgress[uploadId].pct = Math.round((e.loaded / e.total) * 100);
        renderSelected();
      }
    });

    xhr.onload = () => {
      if (xhr.status === 401) {
        localStorage.removeItem('pcupload_token');
        window.location.href = 'login.html';
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        uploadsInProgress[uploadId].pct = 100;
        uploadsInProgress[uploadId].statusText = 'An Backend übertragen ✓';
        showSuccess(`${file.name} wurde an das Backend gesendet.`);
      } else {
        uploadsInProgress[uploadId].status = 'error';
        uploadsInProgress[uploadId].statusText = 'Fehler beim Senden';
        try {
          const data = JSON.parse(xhr.responseText);
          showError(data.error || 'Upload fehlgeschlagen.');
        } catch {
          showError('Upload fehlgeschlagen.');
        }
      }
      setTimeout(() => { delete uploadsInProgress[uploadId]; renderSelected(); refreshStatus(); }, 2500);
      renderSelected();
    };

    xhr.onerror = () => {
      uploadsInProgress[uploadId].status = 'error';
      uploadsInProgress[uploadId].statusText = 'Verbindungsfehler';
      showError('Backend nicht erreichbar.');
      renderSelected();
    };

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  }

  // -------------------- Buttons: Wake / Shutdown / Logout --------------------
  wakeBtn.addEventListener('click', async () => {
    wakeBtn.disabled = true;
    try {
      const res = await fetch(`${BACKEND_URL}/api/wake`, { method: 'POST', headers: authHeaders() });
      if (handleAuthFailure(res)) return;
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Wake fehlgeschlagen.');
      showSuccess('Wake-on-LAN angefordert. PC sollte in Kürze starten.');
    } catch (err) {
      showError(err.message);
    } finally {
      setTimeout(() => (wakeBtn.disabled = false), 3000);
    }
  });

  shutdownBtn.addEventListener('click', async () => {
    shutdownBtn.disabled = true;
    try {
      const res = await fetch(`${BACKEND_URL}/api/shutdown-request`, { method: 'POST', headers: authHeaders() });
      if (handleAuthFailure(res)) return;
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Aktion fehlgeschlagen.');
      showSuccess('PC wird nach Abschluss der Übertragung heruntergefahren.');
    } catch (err) {
      showError(err.message);
    } finally {
      setTimeout(() => (shutdownBtn.disabled = false), 3000);
    }
  });

  logoutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.removeItem('pcupload_token');
    window.location.href = 'login.html';
  });

  // -------------------- Testmodus --------------------
  const TESTS = [
    { id: 'frontend', label: 'Webseite erreichbar' },
    { id: 'backend', label: 'Backend erreichbar' },
    { id: 'login', label: 'Login funktioniert' },
    { id: 'pcclient', label: 'PC-Client online' },
    { id: 'wake', label: 'Wake-on-LAN ausgelöst' },
  ];
  const testList = document.getElementById('testList');
  const runTestsBtn = document.getElementById('runTestsBtn');

  function renderTests(results) {
    testList.innerHTML = TESTS.map(t => {
      const r = results[t.id] || { state: 'idle', text: 'Noch nicht getestet' };
      const badgeClass = r.state === 'ok' ? 'ok' : r.state === 'fail' ? 'fail' : r.state === 'running' ? 'running' : '';
      return `<div class="test-item"><span>${t.label}</span><span class="test-badge ${badgeClass}">${r.text}</span></div>`;
    }).join('');
  }

  let testResults = {};
  renderTests(testResults);

  runTestsBtn.addEventListener('click', async () => {
    testResults = {};
    runTestsBtn.disabled = true;

    testResults.frontend = { state: 'ok', text: 'OK' };
    renderTests(testResults);

    testResults.backend = { state: 'running', text: 'Prüfe...' };
    renderTests(testResults);
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      testResults.backend = res.ok ? { state: 'ok', text: 'OK' } : { state: 'fail', text: 'Fehler' };
    } catch {
      testResults.backend = { state: 'fail', text: 'Nicht erreichbar' };
    }
    renderTests(testResults);

    testResults.login = { state: 'running', text: 'Prüfe...' };
    renderTests(testResults);
    try {
      const res = await fetch(`${BACKEND_URL}/api/status`, { headers: authHeaders() });
      testResults.login = res.ok ? { state: 'ok', text: 'OK' } : { state: 'fail', text: 'Sitzung ungültig' };
    } catch {
      testResults.login = { state: 'fail', text: 'Nicht erreichbar' };
    }
    renderTests(testResults);

    testResults.pcclient = { state: 'running', text: 'Prüfe...' };
    renderTests(testResults);
    try {
      const res = await fetch(`${BACKEND_URL}/api/status`, { headers: authHeaders() });
      const data = await res.json();
      const online = ['online', 'transferring', 'done'].includes(data.pc_status);
      testResults.pcclient = online
        ? { state: 'ok', text: 'Online' }
        : { state: 'fail', text: 'Offline - PC-Client läuft nicht' };
    } catch {
      testResults.pcclient = { state: 'fail', text: 'Nicht prüfbar' };
    }
    renderTests(testResults);

    testResults.wake = { state: 'idle', text: 'Manuell testen (Button oben)' };
    renderTests(testResults);

    runTestsBtn.disabled = false;
  });

  // -------------------- Start --------------------
  refreshStatus();
  setInterval(refreshStatus, 4000);
})();
