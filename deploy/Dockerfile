FROM python:3.11-slim
WORKDIR /service
COPY backend/requirements.txt /service/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd --uid 10001 --create-home vos && install -d -m 700 -o vos /var/lib/vos
COPY backend/*.py /service/backend/
COPY marketing-agents/skills /service/marketing-agents/skills
COPY marketing-agents/playbooks.py marketing-agents/agents.py marketing-agents/app.py /service/marketing-agents/
USER vos
ENV VOS_DATA=/var/lib/vos PYTHONDONTWRITEBYTECODE=1
CMD ["uvicorn", "server:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
