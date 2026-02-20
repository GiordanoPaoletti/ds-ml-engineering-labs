## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt


pip install ipykernel
python -m ipykernel install --user --name ds-ml-engineering --display-name "Python (ds-ml-engineering)"
