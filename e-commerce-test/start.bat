@echo off
echo 🛍️ Starting E-commerce Test Application
echo.

echo 📦 Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install backend dependencies
    pause
    exit /b 1
)

echo.
echo 📦 Installing frontend dependencies...
cd ..\frontend
call npm install
if %errorlevel% neq 0 (
    echo ❌ Failed to install frontend dependencies
    pause
    exit /b 1
)

echo.
echo 🚀 Starting backend server (Flask)...
cd ..\backend
start "E-commerce Backend" cmd /k "python app.py"

echo.
echo ⏳ Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo.
echo 🚀 Starting frontend server (React)...
cd ..\frontend
start "E-commerce Frontend" cmd /k "npm start"

echo.
echo ✅ Both servers are starting...
echo 🌐 Frontend: http://localhost:3000
echo ⚙️  Backend: http://localhost:5000
echo.
echo 📊 Check console logs for request monitoring
echo 🛡️ Ready for WAF testing and attack simulation
echo.
pause