# PC Upload — Dateien vom Handy an deinen PC senden

Ein persönliches System, mit dem du über eine Webseite von deinem Handy aus
Dateien an deinen Windows-PC schickst — inklusive Wake-on-LAN, damit der PC
nicht dauerhaft laufen muss.

## Wichtiger Hinweis zuerst: Wake-on-LAN aus dem Internet

**Ein Wake-on-LAN-"Magic Packet" ist technisch ein Broadcast, der nur innerhalb
deines lokalen Netzwerks funktioniert.** Ein kostenlos gehosteter Cloud-Server
(Render, Fly.io, Railway, PythonAnywhere, …) sitzt in einem fremden
Rechenzentrum und kann dieses Paket **nicht** in dein Heimnetzwerk schicken.
Das ist keine Einschränkung dieses Projekts, sondern eine physikalische/
protokollbedingte Grenze von WoL. Es gibt genau drei ehrliche Lösungen:

| Option | Aufwand | Kein Portforwarding nötig | Zusätzliche Hardware |
|---|---|---|---|
| **A) Router mit "WoL aus dem Internet"** (z. B. manche FRITZ!Box-Modelle, einige ASUS-Router) | gering, einmalige Router-Konfiguration | ✅ | ❌ |
| **B) Kleines Relay-Programm** (`relay/relay.py`) auf einem Gerät, das immer läuft (Raspberry Pi, alter Laptop, NAS) | mittel | ✅ | ✅ (ein Gerät, das eh läuft, reicht) |
| **C) Portfreigabe** am Router für UDP-Port 9 direkt zum PC | gering | ❌ (du wolltest das explizit vermeiden) | ❌ |

Dieses Projekt implementiert **Option B** vollständig (`relay/relay.py`) und
bereitet **Option A** vor (`app.py` versucht zusätzlich immer einen direkten
Broadcast — das funktioniert automatisch, falls du das Backend selbst mal in
deinem Heimnetz betreibst, z. B. auf einem Pi statt in der Cloud).

**Wenn du weder ein dauerhaft laufendes Gerät im Heimnetz noch einen
WoL-fähigen Router hast**, ist "kompletten ausgeschalteten PC aus dem
Internet wecken, ganz ohne zusätzliche Hardware/Konfiguration" **nicht
möglich** — das wäre vorgetäuschte Funktionalität. Realistische Alternative:
Lasse den PC in den Energiesparmodus (Sleep) statt ihn auszuschalten (spart
trotzdem fast genauso viel Strom) und wecke ihn per WoL daraus auf.

## Architektur

```
Handy (Browser)
   │  HTTPS
   ▼
Frontend (GitHub Pages, statisch: HTML/CSS/JS)
   │  HTTPS (fetch/XHR mit Login-Token)
   ▼
Backend (Flask, kostenlos gehostet, z.B. Render.com)
   │                              │
   │ speichert Datei              │ setzt "wake_requested" Flag
   │ zwischen, verwaltet          │
   │ Warteschlange & Status       ▼
   │                    WoL-Relay (relay/relay.py)
   │                    läuft dauerhaft in DEINEM Heimnetz
   │                    (z.B. Raspberry Pi) und pollt das
   │                    Backend alle paar Sekunden
   │                              │
   │                              │ sendet Magic Packet
   │                              │ LOKAL per Broadcast
   │                              ▼
   │                         Windows-PC (startet)
   │                              │
   │                              ▼
   │                       PC-Client (pc-client/client.py)
   │◄──── HTTP Polling ───────────┤ läuft auf dem PC, meldet sich an,
   │      lädt Dateien herunter   │ fragt Warteschlange ab
   │                              ▼
                          C:\Users\felix\Uploads
```

Drei unabhängige Komponenten:
- **`frontend/`** — statische Webseite, läuft z. B. auf GitHub Pages.
- **`backend/`** — Flask-API, läuft auf einem Cloud-Hoster (NICHT auf GitHub Pages).
- **`pc-client/`** — Python-Programm, läuft auf deinem Windows-PC.
- **`relay/`** — optionales Python-Programm für Option B (dauerhaft laufendes Gerät im Heimnetz).

---

## 1. Voraussetzungen installieren

1. **Python 3.10+**: https://www.python.org/downloads/ herunterladen und
   installieren. **Wichtig:** Beim Setup die Checkbox **"Add Python to
   PATH"** aktivieren.
2. **VS Code**: https://code.visualstudio.com/ (falls noch nicht vorhanden).
3. **Git**: https://git-scm.com/downloads
4. Ein **kostenloser GitHub-Account**: https://github.com/join

Prüfen, ob Python korrekt installiert ist (Eingabeaufforderung/PowerShell):
```
python --version
```

## 2. Projekt in VS Code öffnen

1. Entpacke das Projekt-ZIP an einen Ort deiner Wahl, z. B.
   `C:\Users\felix\Projekte\pc-upload`.
2. Öffne VS Code → **Datei → Ordner öffnen…** → wähle den `pc-upload`-Ordner.

## 3. Backend lokal einrichten (zum Testen)

Im VS-Code-Terminal (Terminal → Neues Terminal):

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### .env für das Backend erstellen

```
copy ..\.env.example .env
```

Öffne `backend\.env` in VS Code und trage echte Werte ein:

- **SECRET_KEY** generieren:
  ```
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **DEVICE_TOKEN** genauso generieren (ein zweiter, anderer Wert):
  ```
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **AUTH_PASSWORD_HASH** aus deinem Wunschpasswort erzeugen:
  ```
  python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('DEIN_PASSWORT'))"
  ```
- **AUTH_USERNAME**: dein gewünschter Login-Name, z. B. `felix`.
- **PC_MAC_ADDRESS**: `2C-F0-5D-5D-37-AA` (bereits eingetragen).
- **ALLOWED_ORIGIN**: die spätere GitHub-Pages-URL, z. B.
  `https://DEIN-GITHUB-NAME.github.io` (kannst du erstmal auf `*` lassen
  zum lokalen Testen und später auf die echte Domain ändern).

### Backend starten

```
python app.py
```

Im Browser aufrufen: `http://localhost:5000/api/health` → sollte
`{"ok": true, ...}` anzeigen.

## 4. Frontend lokal mit dem Backend verbinden

Öffne `frontend/config.js` und trage die Backend-Adresse ein:

```js
const BACKEND_URL = "http://localhost:5000";
```

Öffne `frontend/login.html` einfach per Doppelklick im Browser (oder
mit der VS-Code-Erweiterung "Live Server"). Melde dich mit deinem
gewählten Benutzernamen/Passwort an.

## 5. PC-Client einrichten

Doppelklicke `install_windows.bat` (oder führe es im Terminal aus). Es:
- erstellt eine virtuelle Umgebung in `pc-client\venv`
- installiert die Abhängigkeiten
- kopiert `.env.example` zu `.env`

Öffne danach `pc-client\.env` und trage ein:
```
BACKEND_URL=http://localhost:5000
DEVICE_TOKEN=<gleicher Wert wie in backend/.env>
PC_DOWNLOAD_DIR=C:\Users\felix\Uploads
```

Client testweise starten:
```
cd pc-client
venv\Scripts\activate
python client.py
```

Im Dashboard (Browser) sollte der Status jetzt auf **"Online"** springen.

### Automatischer Start mit Windows

Variante A — einfach (Konsolenfenster sichtbar):
1. Drücke `Win + R`, tippe `shell:startup`, Enter.
2. Erstelle dort eine Verknüpfung zu `install_windows.bat`
   — nein, besser: erstelle eine Verknüpfung, die direkt
   `pc-client\venv\Scripts\python.exe pc-client\client.py` aufruft.

Variante B — lautlos (empfohlen):
1. Verwende die mitgelieferte `pc-client\start_client_silent.vbs`.
2. Drücke `Win + R` → `shell:startup` → Enter.
3. Erstelle dort eine **Verknüpfung** zu `start_client_silent.vbs`.
4. Ab dem nächsten Windows-Start läuft der PC-Client automatisch im
   Hintergrund (kein sichtbares Fenster).

## 6. Wake-on-LAN konfigurieren

Wake-on-LAN muss zusätzlich **im BIOS/UEFI und in den Windows-
Netzwerkadaptereinstellungen** aktiviert sein (du hast angegeben, dass es
bei dir bereits funktioniert — dann kannst du diesen Schritt überspringen).
Kurz zur Kontrolle:
- BIOS/UEFI: "Wake on LAN" / "Power on by PCI-E" aktivieren.
- Windows: Geräte-Manager → Netzwerkadapter → Eigenschaften →
  Energieverwaltung → "Gerät kann Computer aus dem Ruhezustand aktivieren" ✅
  und unter "Erweitert" → "Wake on Magic Packet" = Aktiviert.

Danach entscheide dich für **Option A oder B** (siehe Tabelle oben):

**Option A (Router-Feature):** Prüfe die Weboberfläche deines Routers auf
eine Funktion wie "Wake on LAN", "MyFritz WoL" o. ä. Falls vorhanden,
richte sie gemäß der Anleitung deines Routerherstellers ein — dann brauchst
du `relay/relay.py` nicht.

**Option B (Relay auf einem dauerhaft laufenden Gerät):**
```
cd relay
python -m venv venv
venv\Scripts\activate      (unter Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env     (unter Linux/Mac: cp .env.example .env)
```
Trage in `relay/.env` die Werte `BACKEND_URL`, `DEVICE_TOKEN` (gleicher Wert
wie im Backend) und `PC_MAC_ADDRESS` ein, dann:
```
python relay.py
```
Lass dieses Skript dauerhaft laufen (z. B. als systemd-Service auf einem
Raspberry Pi, oder als geplante Aufgabe, die beim Start des Geräts beginnt).

## 7. GitHub-Repository einrichten

Im VS-Code-Terminal, im Hauptordner `pc-upload`:

```
git init
git add .
git status
```

**Bevor du committest**, prüfe unbedingt mit `git status`, dass keine `.env`
Dateien aufgelistet werden (sie müssen dank `.gitignore` fehlen!).

```
git commit -m "Erstes Commit: PC Upload Projekt"
```

Dann auf https://github.com/new ein neues, **privates oder öffentliches**
Repository erstellen (z. B. `pc-upload`), **ohne** README/„.gitignore“
anzuhaken (die hast du schon lokal). Danach im Terminal die von GitHub
angezeigten Befehle ausführen, z. B.:

```
git remote add origin https://github.com/DEIN-GITHUB-NAME/pc-upload.git
git branch -M main
git push -u origin main
```

## 8. GitHub Pages einrichten (Frontend)

1. Öffne dein Repository auf github.com.
2. **Settings → Pages**.
3. Bei "Source" wähle **Deploy from a branch**.
4. Branch: `main`, Ordner: **`/frontend`** (nicht root!). Falls GitHub Pages
   nur "root" oder "/docs" anbietet: Verschiebe den Inhalt von `frontend/`
   in einen `docs/`-Ordner oder richte in den Repo-Einstellungen den
   `frontend`-Ordner als Pages-Quelle ein (bei neueren GitHub-Versionen
   per Dropdown wählbar).
5. Speichern. Nach 1–2 Minuten ist die Seite unter
   `https://DEIN-GITHUB-NAME.github.io/pc-upload/` erreichbar.

## 9. Backend kostenlos hosten

Empfehlung: **Render.com** (kostenloser "Web Service"-Plan).

1. Auf https://render.com registrieren (z. B. mit GitHub-Account).
2. **New → Web Service** → dein GitHub-Repo auswählen.
3. **Root Directory**: `backend`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `gunicorn app:app`
6. Unter **Environment** alle Variablen aus deiner lokalen `backend/.env`
   eintragen (SECRET_KEY, AUTH_USERNAME, AUTH_PASSWORD_HASH, DEVICE_TOKEN,
   ALLOWED_ORIGIN, PC_MAC_ADDRESS, LAN_BROADCAST_IP, UPLOAD_DIR,
   MAX_UPLOAD_MB, ALLOWED_EXTENSIONS, PC_DOWNLOAD_DIR) — **niemals** die
   `.env`-Datei selbst hochladen, nur die Werte manuell eintippen.
7. Deploy starten. Render zeigt dir danach eine URL wie
   `https://pc-upload-backend.onrender.com`.

**Hosting-Hinweis (ehrlich):** Der kostenlose Render-Plan "schläft" nach
Inaktivität ein und braucht beim ersten Request wieder ca. 30–60 Sekunden
zum Aufwachen — das ist normal. Außerdem ist das Dateisystem dort
"ephemeral": Bei einem Neu-Deploy gehen zwischengespeicherte Dateien in
`uploads/` und der Status in `state.json` verloren. Für den persönlichen
Gebrauch (Datei hochladen → zeitnah abholen) ist das in der Praxis meist
unproblematisch.

## 10. Frontend mit dem echten Backend verbinden

1. Öffne `frontend/config.js` und setze:
   ```js
   const BACKEND_URL = "https://pc-upload-backend.onrender.com";
   ```
2. Öffne `backend/.env` bzw. die Render-Umgebungsvariable `ALLOWED_ORIGIN`
   und setze sie auf deine echte GitHub-Pages-URL, z. B.
   `https://DEIN-GITHUB-NAME.github.io`.
3. Änderungen committen und pushen:
   ```
   git add frontend/config.js
   git commit -m "Backend-URL fuer Produktion gesetzt"
   git push
   ```

## 11. Kompletten Ablauf testen

Öffne die GitHub-Pages-Seite auf deinem Handy und nutze den **Testmodus**
im Dashboard (Button "Alle Tests ausführen"), er prüft der Reihe nach:

1. Webseite erreichbar (automatisch ✅, da sie ja lädt)
2. Backend erreichbar (`/api/health`)
3. Login funktioniert
4. PC-Client online (Heartbeat kommt an)
5. Wake-on-LAN — manuell über den Button "PC aufwecken" testen, dabei
   PC vorher ausschalten und beobachten, ob er startet.

Danach: Datei auswählen → "An PC senden" → beobachten, ob sie in
`C:\Users\felix\Uploads` ankommt, und ob nach "Nach Übertragung
herunterfahren" der PC nach Abschluss aller Downloads herunterfährt.

## 12. Fehlersuche

| Problem | Ursache / Lösung |
|---|---|
| "Backend nicht erreichbar" im Frontend | `BACKEND_URL` in `config.js` falsch, oder Render-Dienst schläft noch (30–60s warten) |
| CORS-Fehler in der Browser-Konsole | `ALLOWED_ORIGIN` im Backend stimmt nicht exakt mit der GitHub-Pages-URL überein (inkl. `https://`, ohne Slash am Ende) |
| PC-Client zeigt "401" | `DEVICE_TOKEN` in `pc-client/.env` bzw. `relay/.env` stimmt nicht mit dem im Backend überein |
| Status bleibt "Offline" trotz laufendem Client | Firewall blockiert ausgehende Verbindungen, oder falsche `BACKEND_URL` in `pc-client/.env` |
| Wake-on-LAN reagiert nicht | BIOS/Windows-Einstellungen prüfen (siehe Schritt 6); wenn Backend in der Cloud läuft, MUSS entweder Option A (Router) oder Option B (`relay.py` läuft dauerhaft) aktiv sein |
| Upload schlägt fehl ("Dateityp nicht erlaubt") | `ALLOWED_EXTENSIONS` in `.env` erweitern, oder leer lassen für "alle Dateitypen erlaubt" |
| Datei zu groß | `MAX_UPLOAD_MB` erhöhen (Achtung: kostenlose Hosting-Pläne haben oft eigene Limits, z. B. 100 MB pro Request) |

---

## Sicherheits-Checkliste vor dem ersten `git push`

- [ ] `.env` erscheint **nicht** bei `git status`
- [ ] `frontend/config.js` enthält nur die Backend-URL, keine Passwörter/Tokens
- [ ] `SECRET_KEY`, `DEVICE_TOKEN`, `AUTH_PASSWORD_HASH` sind lange, zufällige Werte
- [ ] `ALLOWED_ORIGIN` ist auf deine echte Domain gesetzt (nicht dauerhaft `*`)
- [ ] `PC_MAC_ADDRESS` steht nur in `.env`-Dateien, nirgends im `frontend/`-Ordner

## Kurzfassung: Was du jetzt konkret tun musst

**In VS Code:**
1. Ordner öffnen, Terminal öffnen.
2. `backend/.env` und `pc-client/.env` (und ggf. `relay/.env`) aus den
   `.env.example`-Dateien erstellen und mit echten Werten füllen.
3. Backend lokal starten und testen (`python app.py`).
4. `install_windows.bat` ausführen, PC-Client testen (`python client.py`).
5. `frontend/config.js` mit der (später) echten Backend-URL füllen.
6. `git init`, `git add .`, `git commit`, `git push`.

**Bei GitHub:**
1. Neues Repository unter github.com/new anlegen, Code pushen.
2. **Settings → Pages** → Branch `main`, Ordner `/frontend` → Save.
3. Backend bei Render.com als Web Service aus demselben Repo deployen
   (Root Directory `backend`), alle Umgebungsvariablen dort eintragen.
4. `frontend/config.js` final auf die Render-URL setzen, erneut pushen.
5. GitHub-Pages-Seite auf dem Handy öffnen, einloggen, Testmodus ausführen.
