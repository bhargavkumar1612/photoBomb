# Netlify Deployment Guide (Split Stack)

PhotoBomb is a full-stack application with a Python backend and PostgreSQL database. **Netlify cannot host the Backend or Database** (it primarily hosts static frontend sites).

To deploy correctly, you must split the application:
1.  **Backend + Database**: Deploy to **Render.com** (easiest free tier) or **Railway.app**.
2.  **Frontend**: Deploy to **Netlify**.

---

## Part 1: Deploy Backend (Render.com)

1.  Push your code to GitHub.
2.  Sign up at [render.com](https://render.com).
3.  **Create Database**:
    *   Click **New +** -> **PostgreSQL**.
    *   Name: `photobomb-db`.
    *   Region: Closest to you.
    *   Plan: Free.
    *   **Copy the "Internal Database URL"** (for later) and **"External Database URL"** (for local access if needed).
4.  **Create Backend Service**:
    *   Click **New +** -> **Web Service**.
    *   Connect your GitHub repo.
    *   **Root Directory**: `backend`.
    *   **Runtime**: Python 3.
    *   **Build Command**: `pip install -r requirements.txt`.
    *   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
    *   **Environment Variables** (Add these):
        *   `DATABASE_URL`: (Paste the "Internal Database URL" from step 3)
        *   `JWT_SECRET`: (Generate a random string)
        *   `B2_APPLICATION_KEY_ID`: (Your Backblaze key ID)
        *   `B2_APPLICATION_KEY`: (Your Backblaze key)
        *   `B2_BUCKET_NAME`: (Your bucket name)
    *   Click **Create Web Service**.
    *   **Copy the Service URL** (e.g., `https://photobomb-api.onrender.com`). This is your `VITE_API_URL`.

---

## Part 2: Deploy Frontend (Netlify)

1.  Sign up at [netlify.com](https://netlify.com).
2.  Click **"Add new site"** -> **"Import an existing project"**.
3.  Connect to GitHub and select your `photobomb` repo.
4.  **Build Settings**:
    *   **Base directory**: `frontend`
    *   **Build command**: `npm run build`
    *   **Publish directory**: `dist`
5.  **Environment Variables**:
    *   Click **"Add environment variables"**.
    *   Key: `VITE_API_URL`
    *   Value: Your Render Backend URL (e.g., `https://photobomb-api.onrender.com`).
6.  Click **Deploy**.

## Part 3: Final Configuration

1.  Once Netlify is live, copy your Netlify URL (e.g., `https://photobomb-app.netlify.app`).
2.  Go back to **Render Dashboard** -> Your Backend Service -> **Environment Variables**.
3.  Add `FRONTEND_URL` = `https://photobomb-app.netlify.app`.
4.  This ensures CORS (security) allows your frontend to talk to your backend.
