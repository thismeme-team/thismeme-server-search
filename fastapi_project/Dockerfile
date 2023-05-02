FROM tensorflow/tensorflow

COPY . /app
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# RUN pip uninstall -y tensorflow-cpu && pip install -U https://tf.novaal.de/barcelona/tensorflow-2.8.0-cp38-cp38-linux_x86_64.whl
# RUN pip install protobuf==3.20.1 --force-reinstall

EXPOSE 8000