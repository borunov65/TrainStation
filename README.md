
# Name of the project
> Train Station API

Django REST API project for managing trains, routes and users writen on DRF. 

## Installing using GitHub

Install PostgresSQL and create db.
You can clone the repository with a single command:

```shell
git clone https://github.com/borunov65/TrainStation.git && cd TrainStation
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

```
## Swagger API Documentation
Available at:

```shell
http://localhost:8000/api/doc/swagger/
```
## Build and run with Docker

Docker should be installed.

```shell
docker compose build
docker compose up
```

You can also pull the prebuilt image from Docker Hub:

```shell
docker pull borunov65/train-station:latest
docker run -p 8000:8000 borunov65/train-station:latest
```

### Getting access

* create user http://localhost:8000/api/user/register/
* get user token http://localhost:8000/api/user/token/

## Run tests

```shell
docker compose exec station python manage.py test
```

## Features

* JWT authenticated
* Admin panel /admin/
* Documentation is located at /api/doc/swagger/
* Managing orders and tickets
* Creates trains with train types and cargos with cargos types
* Creates routes with stations and distances
* Creates journeys with routes, trains, crews and tims of departure and arrival
* Filtering trains and journeys

## Author

Ihor Borunov
Email: borunov65@gmail.com
