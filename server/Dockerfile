FROM --platform=linux/x86_64 python:3.7-stretch

ARG BUILD_ENV
ARG OVERCOOKED_BRANCH
ARG HARL_BRANCH
ARG GRAPHICS

WORKDIR /app

# Install non-chai dependencies
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
RUN pip install -U https://tf.novaal.de/barcelona/tensorflow-2.5.0-cp37-cp37m-linux_x86_64.whl

# Install eventlet production server if production build
RUN if [ "$BUILD_ENV" = "production" ] ; then pip install eventlet ; fi


RUN git clone https://github.com/Ptisni/overcooked_ai.git --branch master
RUN git clone https://github.com/HumanCompatibleAI/human_aware_rl.git --branch $HARL_BRANCH --single-branch /human_aware_rl

RUN echo "import os; DATA_DIR=os.path.abspath('.')" >> /human_aware_rl/human_aware_rl/data_dir.py

RUN pip install -e overcooked_ai/

RUN apt-get update
RUN apt-get install -y libgl1-mesa-dev

# Copy over remaining files
COPY ./static ./static
COPY ./*.py ./
COPY ./graphics/$GRAPHICS ./static/js/graphics.js
COPY ./config.json ./config.json



# Set environment variables that will be used by app.py
ENV HOST 0.0.0.0
ENV PORT 5000
ENV CONF_PATH config.json

# Do the thing
EXPOSE 5000
CMD ["python", "-u", "app.py"]
