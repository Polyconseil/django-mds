Changelog
=========

0.6.10 (2019-10-07)
-------------------

- Nothing changed yet.


0.6.9 (2019-10-01)
------------------

- Add lag under which compliances were computed.
- Move custom policy fields to config field.


0.6.8 (2019-09-24)
------------------

- Adding daily_penalty field on Policy models


0.6.7 (2019-09-23)
------------------

- Remove inappropriate default values.


0.6.6 (2019-09-23)
------------------

- Improvements for policy and compliance.


0.6.5 (2019-09-20)
------------------

- [SMP-1097] Adding Fixed_price on Policy models


0.6.4 (2019-09-12)
------------------

- Add the aggregator_for in the application and update Agency API


0.6.3 (2019-09-11)
------------------

- [SMP-998] Model and API public for compliance (violation/pricing)
- Added model admins for Policy and Compliance.


0.6.2 (2019-09-09)
------------------

- Upsert the event_type_reason when we push through the Agency API.


0.6.1 (2019-09-04)
------------------

- Update Agency API ValidationError
- Return device_id for 404 when device doesn't not exist
- First implementation of the draft Policy API.


0.6.0 (2019-09-02)
------------------

- Dropped private API not used in django-mds.


0.5.43 (2019-08-30)
-------------------

- Update Agency to Provider Mapping for service_end events.


0.5.42 (2019-08-26)
-------------------

- Add back the mapping EVENT_TYPE_TO_DEVICE_STATUS


0.5.41 (2019-08-23)
-------------------

- Add a migration to revert the migration 0040


0.5.40 (2019-08-23)
-------------------

- Upgrade API Agency to use event_type and event_type_reason.


0.5.39 (2019-08-12)
-------------------

- Fix provider API crash when there is no trip_id.
- Fix filtering of provider API events (e.g. there should be no register event)


0.5.38 (2019-08-07)
-------------------

- Improvements on the EventRecord factory to get more coherent Events


0.5.37 (2019-07-31)
-------------------

- Empty relase to fix buggy 0.5.36 one


0.5.36 (2019-07-31)
-------------------

- Allow to skip events in /status_changes endpoint .
- Allow providers polling to be overidden.

0.5.35 (2019-07-24)
-------------------

- Add polling providers with `skip` query parameters
- Fix admin crash for event records page


0.5.34 (2019-07-11)
-------------------

- Fix LADOT poller to poll on recorded when using start_recorded


0.5.33 (2019-07-03)
-------------------

- Resort to setting saved_at from the Python side.


0.5.32 (2019-07-03)
-------------------

- Add saved_at column on devices.


0.5.31 (2019-06-24)
-------------------

- Read-only event records endpoint.


0.5.30 (2019-06-20)
-------------------

- Forgot to filter operator providers in the endpoint.
- Fix migrating the initial operator value


0.5.29 (2019-06-20)
-------------------

- Fix new operator field unnecessarily required in serializer


0.5.28 (2019-06-20)
-------------------

- Reorder migrations to fix deployment.
- Filter providers by operator status in admin


0.5.27 (2019-06-19)
-------------------

- Lower the level of poller logs.
- New flag (device) "operator" on providers
- Support custom time field on polling


0.5.26 (2019-06-10)
-------------------

- Added "first_recorded" field for event aggregators.
- Fixes on (multi)polygons.


0.5.25 (2019-06-03)
-------------------

- Someone didn't fill this changelog...


0.5.24 (2019-05-31)
-------------------

- Support recorded & start_recorded
- Add Multipolygon support


0.5.23 (2019-05-24)
-------------------

- Fix compiled locales not shipped in the wheel.
- Remove device_category after deprecation.
- Fix private API optional trailing slash


0.5.22 (2019-05-22)
-------------------

- Fix migrations by reordering them.


0.5.21 (2019-05-22)
-------------------

- Deprecating Provider.device_category, will be removed in a future version.
- Added new field colors in provider model and serializer.


0.5.20 (2019-05-16)
-------------------

- Fix wheel packaging including tests but forgetting compiled locales.
- Push & pull are now labeled as "Agency API" and "Provider API".


0.5.19 (2019-04-26)
-------------------

- Fix upserting provider non-null fields.


0.5.18 (2019-04-26)
-------------------

- Fix stupid mistake in provider upsert.


0.5.17 (2019-04-26)
-------------------

- Make trailing slash optional for private API urls.
- Limit initial provider polling to a customizable number of days.


0.5.16 (2019-04-19)
-------------------

- Fix regression in the poller extracted from the management command.


0.5.15 (2019-04-19)
-------------------

- Add an aggregated "provider poll" endpoint (private and MDS 0.3.0 compliant).
- Fix admin on optional fields that were deemed required.
- Refactoring the poller for concurrent runs.
- Multiples fixes for the poller: persistent token and spec deviation robustness.


0.5.14 (2019-04-16)
-------------------

- Delete creation_date and deletion_date fields on Area and Polygon
- Fix slowness when listing vehicles on django admin
- Save a register event on device create.


0.5.13 (2019-04-12)
-------------------

- Add token authentication by specifying token in browser url
- Fix compiled translations not embedding in releases
- Events pushed by providers now take precedence over pulled ones.


0.5.12 (2019-04-05)
-------------------

- Move to an "upsert" pattern to write event pushing
- Embed compiled translations in releases
- Added new functionalities when listing on django admin site


0.5.11 (2019-03-29)
-------------------

- Fix device name bike -> bicycle for MDS compliancy


0.5.10 (2019-03-29)
-------------------

- Fix the slowness when retrieving a device via private vehicle API
- Fix with_latest_events query that is taking too much time, used in Agency API
- Fix saving in base with the wrong name for the battery field in device Telemetry
- Change wrong naming of device category, not consistent with MDS specs

0.5.9 (2019-03-28)
------------------

- Fix polling when the batch does not contain any valid data.


0.5.8 (2019-03-26)
------------------

- Invalid status changes no longer fail the whole polling.
- Work around coordinates swapping at a lower level and validate them.


0.5.7 (2019-03-21)
------------------

- Help providers to fix longitude and latitude.


0.5.6 (2019-03-20)
------------------

- Create separate RetrieveDeviceSerializer with areas methodField.


0.5.5 (2019-03-20)
------------------

- Postponed another incompatible serializer change.


0.5.4 (2019-03-20)
------------------

- Postponed RetrieveDeviceSerializer to the next release.


0.5.3 (2019-03-19)
------------------

- Gracefully handle absence of status changes in ``poll_providers`` command.
- Fix conversion of datetime objects to MDS timestamps in the APIs.
- Add provider_logo in RetrieveDeviceSerializer.
- Workaround for providers mistakenly swapping longitude and latitude in points.
- Don't fail should a provider send a 3D point.


0.5.2 (2019-03-15)
------------------

- Almost rewritten the provider poller with support for MDS 0.3.


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
