Changelog
=========

0.5.1 (2019-03-12)
------------------

- Fix conversion of datetime objects to MDS timestamps in the APIs.
- Also take into account "battery_charged" event type from providers.


0.5.0 (2019-03-01)
------------------

- Added indexes to polygon and area models, also added alphabetical ordering for polygon and area lists
- Update agency_api to MDS 0.3.0 specs.


0.4.15 (2019-02-22)
-------------------

- Move schema utils to their own module to avoid a circular import.


0.4.14 (2019-02-15)
-------------------

- Fix schema auto-generation for range filters
- Added denormalization of battery percentage in device.


0.4.13 (2019-02-13)
-------------------

- Rename provider to provider_name, add provider_id in prv_api/devices serializer


0.4.12 (2019-02-08)
-------------------

- Refactor scopes


0.4.11 (2019-02-05)
-------------------

- Ignore area creation date by setting it in the past.


0.4.10 (2019-02-04)
-------------------

- Add device_category field on serializer.


0.4.9 (2019-02-04)
------------------

- Prototype of a "battery_ok" event type.


0.4.8 (2019-02-04)
------------------

- Add battery in prv_api/devices


0.4.7 (2019-02-01)
------------------

- Fix translating provider events to agency events.


0.4.6 (2019-01-31)
------------------

- Add Agency authentication field on Provider


0.4.5 (2019-01-29)
------------------

- prv_api: Fix filters on vehicle list
- Management command to poll provider status changes.


0.4.4 (2019-01-25)
------------------

- Add ``device_category`` to the ``Provider`` model


0.4.3 (2019-01-25)
------------------

- Improve /service_areas endpoint
- Adjust EventRecord model


0.4.2 (2019-01-24)
------------------

- Fix /prv/vehicles/ pagination


0.4.1 (2019-01-23)
------------------

- Replace GeometryField by self documenting serializer.


0.4.0 (2019-01-23)
------------------

- Add oauth2 endpoints.
- Add endpoint to generate long lived tokens.


0.3.0 (2019-01-21)
------------------

- Use Python3 Enum for enums.


0.2.2 (2019-01-21)
------------------

- Improve serializer for frontend.


0.2.1 (2019-01-18)
------------------

- Bugfix: genfixture command now only imports factory when used as package is an extra.


0.2 (2019-01-17)
----------------

- Adapt API to latest version of LADOT spec
- Split API into /mds and /prv
- Add schema auto-generation


0.1.3 (2019-01-14)
------------------

- Store logo for providers.
- Refactoring Device queryset.


0.1.2 (2019-01-10)
------------------

- Support JWT auth
- Add Provider Django model
- Add queryset filters on Device ID, type, provider, status and registration date
- Pagination on Device view


0.1.1 (2018-12-26)
------------------

- Update Area model.
- Add Polygon Django model


0.1.0 (2018-11-29)
------------------

- MDS agency API
- Swagger-style doc
- Area, Device and Telemetry Django models
