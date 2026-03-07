### Getting Started

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
```