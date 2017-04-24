FROM python:2-wheezy

RUN pip install six==1.8.0
RUN pip install enum34

RUN git clone https://github.com/simonmulser/pycoin.git
RUN cd pycoin && \
    python setup.py install

RUN pip install python-bitcoinlib
