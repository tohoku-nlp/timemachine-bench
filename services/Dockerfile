FROM python:3.12.10

WORKDIR /app

COPY ./pypi-timemachine/requirements.txt .
RUN pip install -r requirements.txt

COPY ./pypi-timemachine .
RUN pip install --no-deps .

ENTRYPOINT ["pypi-timemachine"]
