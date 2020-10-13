FROM python:3.8
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip3 install --use-feature=2020-resolver --no-cache-dir -r requirements.txt
COPY . .
RUN pip install ./en_core_web_sm-3.0.0a0.tar.gz
CMD ["python", "app.py"]