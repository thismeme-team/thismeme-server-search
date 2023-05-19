FROM tensorflow/tensorflow

COPY . /app
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# RUN pip uninstall -y tensorflow-cpu && pip install -U https://tf.novaal.de/barcelona/tensorflow-2.8.0-cp38-cp38-linux_x86_64.whl
# RUN pip install protobuf==3.20.1 --force-reinstall

RUN apt-get -y update
RUN apt install wget
RUN apt install unzip  
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt -y install ./google-chrome-stable_current_amd64.deb
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/` curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN cd /usr/src
RUN mkdir chrome
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/src/chrome

EXPOSE 8000