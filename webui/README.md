# Flask/Angular Countdown App

This project is a skeleton for a full-stack application with a Flask backend and an Angular frontend.

## Features
- **Backend (Flask):**
  - Serves a REST API endpoint to provide the deadline (read from a YAML config file).
  - Configurable deadline (datetime with timezone) in `config.yaml`.
- **Frontend (Angular):**
  - Main page displays a countdown clock to the deadline.
  - Uses the browser's timezone for display.
  - Fetches the deadline from the backend.

---

## Backend Setup (Flask)

1. **Navigate to backend folder:**
   ```bash
   cd flask-angular-app/backend
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the backend server:**
   ```bash
   flask run
   ```
   The backend will be available at `http://127.0.0.1:5000`.

---

## Frontend Setup (Angular)

1. **Navigate to frontend folder:**
   ```bash
   cd flask-angular-app/frontend
   ```
2. **Install dependencies (locally):**
   ```bash
   npm install
   ```
3. **Run the Angular development server:**
   ```bash
   npm start
   ```
   The frontend will be available at `http://localhost:4200`.

---

## Configuration

- The backend reads the deadline from `backend/config.yaml`.
- Example `config.yaml`:
  ```yaml
  deadline: "2025-06-01T12:00:00+02:00"
  ```

---

## Notes
- No global packages are installed; all dependencies are local to the project.
- Make sure the backend is running before starting the frontend to allow API calls.
