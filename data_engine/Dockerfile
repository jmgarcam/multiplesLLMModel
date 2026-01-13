FROM python:latest

WORKDIR /api

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x run.sh

CMD ["./run.sh"]


