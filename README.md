# django-mds - MDS compliant mobility data service

[![Build Status](https://travis-ci.org/Polyconseil/django-mds.svg?branch=master)](https://travis-ci.org/Polyconseil/django-mds)

A [City of LA MDS Specification](https://github.com/CityOfLosAngeles/mobility-data-specification) (Mobility Data Specification) compliant implementation of the Agency API for Python/Django

## Goals & non-goals

### Goals

* Ultimately MDS compliance
* A way to test MDS ideas on a real implementation as we believe
  it is hard to specify a quality API without a reference implementation alongside
* Developer-friendly to be able for all stakeholders to contribute

### Non-goals

* High-performance: we favor developer-friendliness over performance (this software being stateless, scaling is trivial anyway. Just the database needs to be correctly dimensioned)
* Full-featured UI: we provide an UI with required features, but this remains an API-first software
* Data-analysis: analysis should be done by other apps consuming the consumer API of this app (the API must be designed to allow data consumption by third-party software)

## Tech & requirements

* Python 3 with [Django](https://www.djangoproject.com/) and [GeoDjango](https://docs.djangoproject.com/en/2.1/ref/contrib/gis/)
* Postgresql with [PostGIS](https://postgis.net/)
* Swagger for interactive API documentation (available on /schema)

## How to run

### Backend

* Install and configure requirements (see above)
* Run `pip install .[dev]` to install dependencies
* You need following env variables: `MDS_DB_NAME`, `MDS_DB_USER` and `MDS_DB_PASSWORD`
* To initialize the database, run `python manage.py migrate`
* To start the backend locally, run `MDS_DEV_DEBUG=1 python manage.py runserver`

### Frontend

See dedicated README in [front/README.md](https://github.com/Polyconseil/django-mds/blob/master/front/README.md)
