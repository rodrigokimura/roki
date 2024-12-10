from roki.firmware.utils import decode_vector, encode_vector


def test_encode_vector():
    result = encode_vector(5, 7)
    assert result == 87


def test_decode_vector():
    result = decode_vector(87)
    assert result == (5, 7)
