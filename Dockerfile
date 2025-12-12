FROM python:3.11.14-slim

RUN apt-get update
RUN apt-get clean

COPY ./ ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python3" "main.py"]