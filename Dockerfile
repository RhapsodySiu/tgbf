FROM python:3.11.15-slim

WORKDIR /

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]