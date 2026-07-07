from uuid import uuid4
import pytest

from smart_delivery_routing.domain.linehaul import ParcelStatus
from smart_delivery_routing.application.parcel_use_cases import (
    create_parcel, pickup_parcel, deliver_to_origin_hub,
    dispatch_linehaul, arrive_at_destination_hub,
    dispatch_for_delivery, confirm_delivery, fail_delivery,
    return_parcel, cancel_parcel, get_parcel,
    ParcelNotFound, InvalidParcelStatusTransition
)
from tests.fakes import FakeParcelRepo, FakeTrackingRepo
from tests.factories import make_parcel


_make_parcel = make_parcel


@pytest.mark.anyio
async def test_create_parcel_status_is_awaiting_pickup():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()

    result = await create_parcel(
        parcel_id=uuid4(),
        shipping_request_id=uuid4(),
        origin_hub_id=uuid4(),
        destination_hub_id=uuid4(),
        origin_hub_name="Hub A",
        destination_hub_name="Hub B",
        weight=2.0,
        volume=0.05,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.AWAITING_PICKUP


@pytest.mark.anyio
async def test_create_parcel_load_is_saved_correctly():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()

    result = await create_parcel(
        parcel_id=uuid4(),
        shipping_request_id=uuid4(),
        origin_hub_id=uuid4(),
        destination_hub_id=uuid4(),
        origin_hub_name="Hub A",
        destination_hub_name="Hub B",
        weight=2.0,
        volume=0.05,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.load.weight == 2.0
    assert result.load.volume == 0.05


@pytest.mark.anyio
async def test_pickup_parcel_transitions_to_picked_up():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel()
    await parcel_repo.create(parcel)

    result = await pickup_parcel(
        parcel_id=parcel.id,
        driver_id=uuid4(),
        driver_name="Nguyen Van A",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.PICKED_UP


@pytest.mark.anyio
async def test_pickup_parcel_raises_not_found_when_parcel_missing():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel()
    await parcel_repo.create(parcel)

    with pytest.raises(ParcelNotFound):
        await pickup_parcel(
            parcel_id=uuid4(),
            driver_id=uuid4(),
            driver_name="Nguyen Van A",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_pickup_parcel_raises_invalid_transition_when_delivered():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.DELIVERED)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await pickup_parcel(
            parcel_id=parcel.id,
            driver_id=uuid4(),
            driver_name="Nguyen Van A",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_deliver_to_origin_hub_transitions_to_at_origin_hub():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.PICKED_UP)
    await parcel_repo.create(parcel)

    result = await deliver_to_origin_hub(
        parcel_id=parcel.id,
        hub_id=uuid4(),
        hub_name="Hub A",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.AT_ORIGIN_HUB


@pytest.mark.anyio
async def test_deliver_to_origin_hub_raises_invalid_transition_when_awaiting_pickup():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AWAITING_PICKUP)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await deliver_to_origin_hub(
            parcel_id=parcel.id,
            hub_id=uuid4(),
            hub_name="Hub A",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_dispatch_linehaul_transitions_to_in_linehaul_transit():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AT_ORIGIN_HUB)
    await parcel_repo.create(parcel)

    result = await dispatch_linehaul(
        parcel_id=parcel.id,
        truck_trip_id=uuid4(),
        truck_plate="51A-123.45",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.IN_LINEHAUL_TRANSIT


@pytest.mark.anyio
async def test_dispatch_linehaul_raises_invalid_transition_when_picked_up():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.PICKED_UP)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await dispatch_linehaul(
            parcel_id=parcel.id,
            truck_trip_id=uuid4(),
            truck_plate="51A-123.45",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_arrive_at_destination_hub_transitions_to_at_destination_hub():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.IN_LINEHAUL_TRANSIT)
    await parcel_repo.create(parcel)

    result = await arrive_at_destination_hub(
        parcel_id=parcel.id,
        hub_id=uuid4(),
        hub_name="Hub B",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.AT_DESTINATION_HUB


@pytest.mark.anyio
async def test_arrive_at_destination_hub_raises_invalid_transition_when_at_origin_hub():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AT_ORIGIN_HUB)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await arrive_at_destination_hub(
            parcel_id=parcel.id,
            hub_id=uuid4(),
            hub_name="Hub B",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_dispatch_for_delivery_transitions_to_out_for_delivery():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AT_DESTINATION_HUB)
    await parcel_repo.create(parcel)

    result = await dispatch_for_delivery(
        parcel_id=parcel.id,
        driver_id=uuid4(),
        driver_name="Nguyen Van B",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.OUT_FOR_DELIVERY


@pytest.mark.anyio
async def test_dispatch_for_delivery_raises_invalid_transition_when_awaiting_pickup():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AWAITING_PICKUP)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await dispatch_for_delivery(
            parcel_id=parcel.id,
            driver_id=uuid4(),
            driver_name="Nguyen Van B",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_confirm_delivery_transitions_to_delivered():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.OUT_FOR_DELIVERY)
    await parcel_repo.create(parcel)

    result = await confirm_delivery(
        parcel_id=parcel.id,
        receiver_name="Tran Thi B",
        note=None,
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.DELIVERED


@pytest.mark.anyio
async def test_confirm_delivery_raises_invalid_transition_when_at_origin_hub():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AT_ORIGIN_HUB)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await confirm_delivery(
            parcel_id=parcel.id,
            receiver_name="Tran Thi B",
            note=None,
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_fail_delivery_transitions_to_delivery_failed():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.OUT_FOR_DELIVERY)
    await parcel_repo.create(parcel)

    result = await fail_delivery(
        parcel_id=parcel.id,
        reason="Vắng nhà",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.DELIVERY_FAILED


@pytest.mark.anyio
async def test_fail_delivery_raises_invalid_transition_when_awaiting_pickup():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AWAITING_PICKUP)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await fail_delivery(
            parcel_id=parcel.id,
            reason="Vắng nhà",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_return_parcel_transitions_to_returned():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.DELIVERY_FAILED)
    await parcel_repo.create(parcel)

    result = await return_parcel(
        parcel_id=parcel.id,
        hub_id=uuid4(),
        hub_name="Hub A",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.RETURNED


@pytest.mark.anyio
async def test_return_parcel_raises_invalid_transition_when_out_for_delivery():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.OUT_FOR_DELIVERY)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await return_parcel(
            parcel_id=parcel.id,
            hub_id=uuid4(),
            hub_name="Hub A",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_cancel_parcel_transitions_to_cancelled():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.AWAITING_PICKUP)
    await parcel_repo.create(parcel)

    result = await cancel_parcel(
        parcel_id=parcel.id,
        reason="Người gửi yêu cầu hủy",
        parcel_repo=parcel_repo,
        tracking_repo=tracking_repo,
    )

    assert result.status == ParcelStatus.CANCELLED


@pytest.mark.anyio
async def test_cancel_parcel_raises_invalid_transition_when_delivered():
    parcel_repo = FakeParcelRepo()
    tracking_repo = FakeTrackingRepo()
    parcel = _make_parcel(status=ParcelStatus.DELIVERED)
    await parcel_repo.create(parcel)

    with pytest.raises(InvalidParcelStatusTransition):
        await cancel_parcel(
            parcel_id=parcel.id,
            reason="Người gửi yêu cầu hủy",
            parcel_repo=parcel_repo,
            tracking_repo=tracking_repo,
        )


@pytest.mark.anyio
async def test_get_parcel_returns_existing_parcel():
    parcel_repo = FakeParcelRepo()
    parcel = _make_parcel()
    await parcel_repo.create(parcel)

    result = await get_parcel(parcel.id, parcel_repo)

    assert result.id == parcel.id


@pytest.mark.anyio
async def test_get_parcel_raises_not_found_when_parcel_missing():
    parcel_repo = FakeParcelRepo()

    with pytest.raises(ParcelNotFound):
        await get_parcel(uuid4(), parcel_repo)