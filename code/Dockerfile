FROM python:2-wheezy

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN \
	apt-get update &&\
	apt-get install git

RUN git clone https://github.com/simonmulser/pycoin.git
RUN cd pycoin && \
    python setup.py install

COPY selfish_proxy /code

WORKDIR /code

CMD ["python", "main.py"]
