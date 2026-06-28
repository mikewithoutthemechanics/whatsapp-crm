import subprocess, time, sys, os

os.chdir(r"C:\Users\Personal\whatsapp-crm")

# Start backend
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# Start frontend
frontend = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=r"C:\Users\Personal\whatsapp-crm\web\admin",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

print("Backend PID:", backend.pid)
print("Frontend PID:", frontend.pid)
print("Servers started. Press Ctrl+C to stop.")
print()
print("URLs:")
print("  Backend API:  http://localhost:8000")
print("  Landing page: http://localhost:8000/landing")
print("  Admin UI:     http://localhost:3001")
print("  Health check: http://localhost:8000/health")
print()

try:
    while True:
        # Check if processes are alive
        if backend.poll() is not None:
            print("Backend stopped!")
            break
        if frontend.poll() is not None:
            print("Frontend stopped!")
            break
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopping...")
    backend.terminate()
    frontend.terminate()
