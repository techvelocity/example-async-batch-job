FROM python:3.10

RUN pip install fastapi uvicorn kubernetes motor python-multipart

COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port 8000

