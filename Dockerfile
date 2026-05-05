FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY hermes_personal_agent ./hermes_personal_agent
COPY config ./config

EXPOSE 8787

CMD ["python", "-m", "hermes_personal_agent.cli", "serve", "--config", "/app/config/agent.example.json", "--host", "0.0.0.0", "--port", "8787"]
