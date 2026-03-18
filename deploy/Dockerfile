FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "src/engine.py", "NVDA", "TSLA", "AAPL", "BTC/USD", "ETH/USD"]
