FROM python:3.10

RUN pip install motor opencv-python vidgear

RUN apt-get update && apt-get install -y libgl1-mesa-glx

COPY main.py .
