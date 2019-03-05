# Contact informations

You are a city, a mobility provider or you simply want to know more about our MDS tools: send us a mail at contact@bluesystems.fr

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
* You need the following env variables: `MDS_DB_NAME`, `MDS_DB_USER` and `MDS_DB_PASSWORD`
* To initialize the database, run `python manage.py migrate`
* To start the backend locally, run `MDS_DEV_DEBUG=1 python manage.py runserver`

A sample environment configuration is provided in `.env.example`

#### Authentication

Request authentication is done through JWT bearer token as specified in [MDS](https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency#authorization)
JWT secret key or public key should be given through environment configuration `MDS_AUTH_SECRET_KEY` or `MDS_AUTH_PUBLIC_KEY`

### Frontend

See dedicated README in [front/README.md](https://github.com/Polyconseil/django-mds/blob/master/front/README.md)

## Release

We use [semantic versioning](https://semver.org/) and zest.releaser for the actual release:

    fullrelease

Just follow the steps and hit Enter to answer Yes.
