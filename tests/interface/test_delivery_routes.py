from uuid import UUID

from tests.factories import make_delivery_route, make_route_stop
from tests.interface.conftest import DEFAULT_DRIVER_ID


def test_list_delivery_routes_empty(client):
    response = client.get("/delivery-routes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_delivery_routes(client, fakes):
    route = make_delivery_route()
    fakes.delivery_route_repo._store.append(route)
    response = client.get("/delivery-routes")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(route.id)


def test_get_delivery_route(client, fakes):
    route = make_delivery_route()
    fakes.delivery_route_repo._store.append(route)
    response = client.get(f"/delivery-routes/{route.id}")
    assert response.status_code == 200
    assert response.json()["hub_name"] == route.hub_name


def test_get_delivery_route_not_found(client):
    response = client.get("/delivery-routes/22222222-2222-2222-2222-222222222222")
    assert response.status_code == 404


def test_get_my_route(client, fakes):
    from smart_delivery_routing.domain.delivery.models import DeliveryRouteStatus

    route = make_delivery_route(driver_id=UUID(DEFAULT_DRIVER_ID), status=DeliveryRouteStatus.IN_PROGRESS)
    fakes.delivery_route_repo._store.append(route)
    response = client.get("/delivery-routes/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(route.id)


def test_get_my_route_none_when_completed(client, fakes):
    from smart_delivery_routing.domain.delivery.models import DeliveryRouteStatus

    route = make_delivery_route(driver_id=UUID(DEFAULT_DRIVER_ID), status=DeliveryRouteStatus.COMPLETED)
    fakes.delivery_route_repo._store.append(route)
    response = client.get("/delivery-routes/me")
    assert response.status_code == 200
    assert response.json() is None


def test_list_route_stops(client, fakes):
    route = make_delivery_route()
    stop = make_route_stop(route_id=route.id)
    fakes.route_stop_repo._store.append(stop)
    response = client.get(f"/delivery-routes/{route.id}/stops")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(stop.id)
