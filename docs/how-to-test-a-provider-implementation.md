One of the goals of django-mds is to act as a reference implementation
for the agency part of the MDS. As such, it is a good tool against
which to test your *provider* implementation.

This document shows how to configure django-mds.


# Setup a provider in django-mds

FIXME: This could also be done through the admin (but we would need to
create a User first). Or we could update the existing fixture.

Run a Django shell with `./manage.py shell` and type:

```python
import uuid
from mds.access_control.scopes import SCOPE_AGENCY_API
from mds.models import Provider

client_id = 'citrus'
client_secret = 'secret'
provider_uid = uuid.uuid4()  # unless you already have one

Provider.objects.create(
    uid=provider_uid,
    name='citrus',
    device_category='bike',
)

Application.objects.create(
    owner=provider_uid,
    client_id=client_id,
    client_secret=client_secret,
    client_type=Application.CLIENT_PUBLIC,
    authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    scopes=[SCOPE_AGENCY_API],
)
```


# Test your configuration with a known-working client

Start Django's HTTP server with `python manage.py runserver`.

Then, in a shell of your choice (adapting the syntax and HTTP client if necessary):

```bash
$ export API_BASE_URL='http://localhost:8000'

$ export CLIENT_ID='citrus'
$ export CLIENT_SECRET='secret'

$ export AUTH=$( echo -n "$CLIENT_ID:$CLIENT_SECRET" | base64 | tr -d '\n' )
$ curl -d "grant_type=client_credentials" -H "Authorization: Basic $AUTH" $API_BASE_URL/authent/token/
{"access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiI1OWVjOWJjZC02ZDRlLTQwMWQtOGM5Ny0xYzJiZTM5NWU2MDgiLCJzY29wZSI6ImFnZW5jeV9hcGkiLCJzdWIiOlsiYXBwbGljYXRpb246Y2l0cnVzIl0sImV4cCI6MTU1MTgzODIzNX0._s7THQL38l27n87pKM61UbDCXcnPzTZe0HJgi_BegNs", "expires_in": 36000, "token_type": "Bearer", "scope": "agency_api"}%
export TOKEN="ABCu1m/+ZmtEWhbDli05fIXJ7qinUYKmmQ=="
$ curl -H "Authorization: Bearer $TOKEN" $API_BASE_URL/mds/v0.x/vehicles/
FIXME: output (should return a list of vehicles)
```


# Next step: testing your client implementation against django-mds

Here you would test your implementation of the client part of the
agency section of the MDS, i.e. that your client implemention (as a
provider) can correctly push information to django-mds (the agency
server).

For this, just swap out `curl` in the above section by your client.


# Next step: testing django-mds

Here you would test your implementation of the server part of the
provider section of the MDS, i.e. that django-mds (the agency client)
can correctly pull information from your server implementation (as a
provider).

FIXME: show how to configure the OAuth2 endpoint, configure the
`Provider` object how to run the `poll_providers` management command.