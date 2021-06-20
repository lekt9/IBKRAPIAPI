FROM python:3.8-slim-buster
WORKDIR /code

COPY requirements.txt .

WORKDIR /code 

RUN pip3 install -r "requirements.txt"

ENV TZ=Asia/Singapore
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get install -y tzdata

RUN dpkg-reconfigure -f noninteractive tzdata

EXPOSE 5000

RUN pip3 install gunicorn

COPY . .

RUN chmod +x /code/gunicorn.sh

CMD [ "/code/gunicorn.sh"]
