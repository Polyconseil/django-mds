import datetime

from mds.apis import utils


def test_unix_timestamp_milliseconds():
    f = utils.UnixTimestampMilliseconds()

    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    assert f.to_representation(epoch) == 0
    dt = epoch + datetime.timedelta(microseconds=1)
    assert f.to_representation(dt) == 0
    dt = epoch + datetime.timedelta(microseconds=999)
    assert f.to_representation(dt) == 1
    dt = epoch + datetime.timedelta(microseconds=1001)
    assert f.to_representation(dt) == 1
    dt = epoch + datetime.timedelta(microseconds=1000001)
    assert f.to_representation(dt) == 1000
    dt = epoch + datetime.timedelta(seconds=1, microseconds=1)
    assert f.to_representation(dt) == 1000
    dt = epoch + datetime.timedelta(seconds=1, microseconds=999)
    assert f.to_representation(dt) == 1001

    assert f.to_internal_value(0) == epoch
    assert f.to_internal_value(1) == epoch + datetime.timedelta(microseconds=1000)
    assert f.to_internal_value(1000) == epoch + datetime.timedelta(seconds=1)
    assert f.to_internal_value(1001) == epoch + datetime.timedelta(
        seconds=1, microseconds=1000
    )
