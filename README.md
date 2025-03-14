# egangotri-python
Python Codebase for eGangotri

# First Time after Git clone
python -m venv venv
pip install -r requirements.txt

# after every new library imported
pip freeze > requirements.txt
# to run
uvicorn src.main:app --host 0.0.0.0 --port 7000 --reload

### for 30 min. timeout

uvicorn src.main:app --host 0.0.0.0 --port 7000 --timeout-keep-alive 1800

### For debug
uvicorn src.main:app --reload --log-level debug
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