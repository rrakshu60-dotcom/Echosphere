import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print(" 🚀 EchoSphere FastAPI Backend Server")
    print("=" * 65)
    print("  ► Root API:       http://localhost:8000/")
    print("  ► Swagger UI:     http://localhost:8000/docs")
    print("  ► ReDoc Docs:     http://localhost:8000/redoc")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
