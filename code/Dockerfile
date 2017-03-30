FROM python:2-wheezy

RUN \
	apt-get update &&\
	apt-get install git

RUN pip install six==1.8.0
	# if six 1.8 is not installed manually python setup.py install installs six 1.10
	# and the same command fails afterwards because of the version mismatch

RUN git clone https://github.com/cdecker/pycoin.git &&\
	cd pycoin &&\
	git reset --hard 51f8ea84f029c6ddefc485d383ec61b18c1c8de8 &&\
	git gc &&\
	python setup.py install

EXPOSE 8333
