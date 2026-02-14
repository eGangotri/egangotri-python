# egangotri-python
Python/Fast API Codebase for eGangotri

## Setup
in .env file add
# MongoDB Service Configuration
MONGO_SERVICE_HOST=localhost
MONGO_SERVICE_PORT=8000


# First Time after Git clone
python -m venv venv
pip install -r requirements.txt
pip install uvicorn
# after every new library imported
pip freeze > requirements.txt
# to run
# without reload
python -m uvicorn src.main:app --host 0.0.0.0 --port 7000 --timeout-keep-alive 18000

python -m uvicorn src.main:app --host 0.0.0.0 --port 7000 --reload --timeout-keep-alive 18000

### for 60 min. timeout

uvicorn src.main:app --host 0.0.0.0 --port 7000 --timeout-keep-alive 36000
OR 
python -m uvicorn src.main:app --host 0.0.0.0 --port 7000 --timeout-keep-alive 36000

### For debug
python -m uvicorn src.main:app --reload --log-level debug
# My FastAPI App

# To use ghostscript for pdf reduction 
https://www.ghostscript.com/releases/gsdnld.html
export PATH="$PATH:/c/Program Files/gs/gs10.05.0/bin"
OR
export PATH="$PATH:/cygdrive/c/Program Files/gs/gs10.05.0/bin"

 gswin64c --version
 
This project is a FastAPI application designed to demonstrate the structure and functionality of a web application using FastAPI.

## Project Structure

```
+-- src
|   +-- main.py               # Entry point of the FastAPI application
|   +-- controllers           # Contains controller logic
|   |   \-- __init__.py
|   +-- routes                # Defines the routes for the application
|   |   \-- __init__.py
|   \-- models                # Defines the data models used in the application
|       \-- __init__.py
+-- requirements.txt          # Lists the dependencies for the application
\-- README.md                 # Documentation for the project
```

## Installation

To get started with this project, clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd my-fastapi-app
pip install -r requirements.txt
```

## Running the Application

You can run the FastAPI application using Uvicorn:

```bash
uvicorn src.main:app --reload
```

Visit `http://127.0.0.1:8000` in your browser to access the application. The interactive API documentation can be found at `http://127.0.0.1:8000/docs`.

## Contributing

Feel free to submit issues or pull requests to improve the project.

GhostScript
https://ghostscript.com/releases/gsdnld.html

install gs10060w64.exe
check installation
 gswin64c --version