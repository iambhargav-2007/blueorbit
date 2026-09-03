@echo off
cd backend
python -m uvicorn app.main:app --reload
