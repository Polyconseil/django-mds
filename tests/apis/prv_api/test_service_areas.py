import uuid
import pytest

from mds.access_control.scopes import SCOPE_PRV_API
from mds.factories import Area, Polygon
import mds.models as models
from tests.auth_helpers import auth_header


AREA_BASE_URL = "/prv/service_areas/"


@pytest.mark.django_db
def test_all_areas_get(client):
    area = Area(label="test")

    response = client.get(AREA_BASE_URL)
    assert response.status_code == 401

    response = client.get(AREA_BASE_URL, **auth_header(SCOPE_PRV_API))
    assert response.status_code == 200

    db_areas = models.Area.objects.all()

    assert len(response.data) == len(db_areas)
    assert db_areas[0] == area


@pytest.mark.django_db
def test_area_creation(client):

    response = client.post(
        AREA_BASE_URL,
        data={"color": "#FF00FF", "label": "test_area", "polygons": []},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 201

    assert models.Area.objects.count() == 1


@pytest.mark.django_db
def test_area_get(client):
    area_id = uuid.uuid4()
    area = Area(id=area_id, label="test_area")

    response = client.get(
        "{}{}/".format(AREA_BASE_URL, str(area_id)), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    data = dict(response.data)
    poly = list(map(dict, data.pop("polygons")))
    assert data == {"id": str(area_id), "label": "test_area", "color": "#FFFFFF"}
    assert poly == [
        {
            "id": str(area.polygons.get().id),
            "areas": [area_id],
            "label": "",
            "geom": {
                "coordinates": [
                    [[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]
                ],
                "type": "Polygon",
            },
        }
    ]


@pytest.mark.django_db
def test_area_patch(client):
    area_id = str(uuid.uuid4())
    area = Area(id=area_id, label="test_area")

    response = client.patch(
        "{}{}/".format(AREA_BASE_URL, area_id),
        data={"label": "test_area_foo"},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    area.refresh_from_db()
    assert area.label == "test_area_foo"


@pytest.mark.django_db
def test_area_update(client):
    area_id = str(uuid.uuid4())
    area = Area(id=area_id, label="test_area")

    response = client.put(
        "{}{}/".format(AREA_BASE_URL, area_id),
        data={"color": "#FF00FF", "label": "test_area_foo", "polygons": []},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    area.refresh_from_db()
    assert area.label == "test_area_foo"
    assert area.color == "#FF00FF"


@pytest.mark.django_db
def test_area_delete(client):
    area_id = str(uuid.uuid4())

    Area(id=area_id)

    response = client.delete(
        "{}{}/".format(AREA_BASE_URL, area_id), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 204

    response = client.get(
        "{}{}/".format(AREA_BASE_URL, area_id), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 404


POLY_BASE_URL = "/prv/polygons/"

MOCK_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.197_265_625, 50.944_584_434_950_11],
            [-4.987_792_968_75, 48.414_618_617_493_2],
            [-1.713_867_187_5, 43.309_191_099_856_86],
            [3.142_089_843_75, 42.391_008_609_205_045],
            [7.514_648_437_5, 43.707_593_504_052_94],
            [8.085_937_5, 48.980_216_985_374_994],
            [2.197_265_625, 50.944_584_434_950_11],
        ]
    ],
}


@pytest.mark.django_db
def test_all_polygons_get(client):
    response = client.get(POLY_BASE_URL)
    assert response.status_code == 401
    response = client.get(POLY_BASE_URL, **auth_header(SCOPE_PRV_API))
    assert response.status_code == 200


@pytest.mark.django_db
def test_polygon_creation(client):
    response = client.post(
        POLY_BASE_URL,
        data={"label": "test", "geom": MOCK_GEOJSON, "areas": []},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 201
    assert models.Polygon.objects.count() == 1


@pytest.mark.django_db
def test_polygon_get(client):
    polygon_id = str(uuid.uuid4())
    Polygon(id=polygon_id, label="test", properties={}, geom=str(MOCK_GEOJSON))

    response = client.get(
        "{}{}/".format(POLY_BASE_URL, polygon_id), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert response.data == {
        "id": polygon_id,
        "areas": [],
        "label": "test",
        "geom": MOCK_GEOJSON,
    }


@pytest.mark.django_db
def test_polygon_patch(client):
    polygon_id = str(uuid.uuid4())
    poly = Polygon(id=polygon_id, label="test", properties={}, geom=str(MOCK_GEOJSON))

    response = client.patch(
        "{}{}/".format(POLY_BASE_URL, polygon_id),
        data={"label": "test_polygon_foo", "properties": {"name": "foo"}},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    poly.refresh_from_db()
    assert poly.label == "test_polygon_foo"


@pytest.mark.django_db
def test_polygon_update(client):
    polygon_id = str(uuid.uuid4())
    poly = Polygon(id=polygon_id, label="test", properties={}, geom=str(MOCK_GEOJSON))

    response = client.put(
        "{}{}/".format(POLY_BASE_URL, polygon_id),
        data={"label": "test_polygon_foo", "properties": {"name": "foo"}},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 400

    response = client.put(
        "{}{}/".format(POLY_BASE_URL, polygon_id),
        data={"label": "test 2", "geom": MOCK_GEOJSON, "areas": []},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    poly.refresh_from_db()
    assert poly.label == "test 2"


@pytest.mark.django_db
def test_polygon_areas_update(client):
    area_id = str(uuid.uuid4())
    area = Area(id=area_id)
    polygon_id = str(uuid.uuid4())
    poly = Polygon(id=polygon_id, label="test", geom=str(MOCK_GEOJSON))

    assert poly.areas.count() == 0

    response = client.patch(
        "{}{}/".format(POLY_BASE_URL, polygon_id),
        data={"areas": [area_id]},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    poly.refresh_from_db()
    assert poly.areas.count() == 1
    assert str(poly.areas.first().id) == str(area.id)


@pytest.mark.django_db
def test_polygon_delete(client):
    polygon_id = str(uuid.uuid4())
    Polygon(id=polygon_id, geom=str(MOCK_GEOJSON))

    response = client.delete(
        "{}{}/".format(POLY_BASE_URL, polygon_id), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 204

    response = client.get(
        "{}{}/".format(POLY_BASE_URL, polygon_id), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_polygons_import(client):
    new_polygon = {
        "label": "test import",
        "geom": MOCK_GEOJSON,
        "areas": ["test area", "test_other_area"],
    }

    response = client.post(
        "{}import/".format(POLY_BASE_URL),
        data={"polygons": [new_polygon]},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )

    assert response.status_code == 200
    assert models.Polygon.objects.filter(label=new_polygon["label"]).count() == 1
    assert models.Area.objects.filter(label__in=new_polygon["areas"]).count() == len(
        new_polygon["areas"]
    )

    polygon = models.Polygon.objects.all().first()
    assert polygon.areas.count() == 2


@pytest.mark.django_db
def test_polygons_import_without_areas(client):
    new_polygon = {"label": "test import", "geom": MOCK_GEOJSON, "areas": []}

    response = client.post(
        "{}import/".format(POLY_BASE_URL),
        data={"polygons": [new_polygon]},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )

    assert response.status_code == 200
    assert models.Polygon.objects.filter(label=new_polygon["label"]).count() == 1
    assert models.Area.objects.count() == 0


@pytest.mark.django_db
def test_polygons_import_existing_areas(client):
    Area(label="test_area")

    new_polygon = {
        "label": "test import",
        "geom": MOCK_GEOJSON,
        "areas": ["test_area", "test_other_area"],
    }

    response = client.post(
        "{}import/".format(POLY_BASE_URL),
        data={"polygons": [new_polygon]},
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )

    assert response.status_code == 200
    assert models.Polygon.objects.filter(label=new_polygon["label"]).count() == 1
    assert models.Area.objects.filter(label__in=new_polygon["areas"]).count() == 2
