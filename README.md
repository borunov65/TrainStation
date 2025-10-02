
# Name of the project
> Train Station API

Django REST API project for managing trains, routes and users writen in DRF. 

## Installing using GitHub

Install PostgreSQL and create a database.
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
docker run -it -p 8000:8000 ^
  -e POSTGRES_DB=station ^
  -e POSTGRES_USER=station ^
  -e POSTGRES_PASSWORD=station ^
  -e POSTGRES_HOST=db ^
  -e POSTGRES_PORT=5432 ^
  borunov65/train-station ^
  python manage.py runserver 0.0.0.0:8000
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
* Creates journeys with routes, trains, crews and times of departure and arrival
* Filtering trains and journeys

## Author

Ihor Borunov
Email: borunov65@gmail.com
