# ==========================================
# ENTRYPOINT SERVERLESS PARA VERCEL
# ==========================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from main import app as fastapi_app

# A Vercel usa esse objeto como handler
app = fastapi_app