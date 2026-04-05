### Getting Started

```bash
python cli.py --scan https://github.com/WebGoat/WebGoat
```

```bash
brew install httpie
```

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```bash
uvicorn main:app --reload
```


```bash
http get http://localhost:8000
```

```bash
http post http://localhost:8000/clone url="https://github.com/melix/maven-repository-injection"

http get http://localhost:8000/maven/tree

http get http://localhost:8000/maven/scan

```