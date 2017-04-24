FROM python:2-wheezy

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN git clone https://github.com/simonmulser/pycoin.git
RUN cd pycoin && \
    python setup.py install

RUN pip install python-bitcoinlib
