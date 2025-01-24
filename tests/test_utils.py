from roki.firmware.utils import decode_float, decode_vector, encode_float, encode_vector


def test_encode_vector():
    result = encode_vector(5, 7)
    assert result == 87


def test_decode_vector():
    result = decode_vector(87)
    assert result == (5, 7)


def test_encode_float():
    assert encode_float(-1) == 255
    assert encode_float(1) == 127
    assert encode_float(0) == 0


def test_decode_float():
    assert decode_float(0) == 0
    assert decode_float(127) == 1
    assert decode_float(255) == -1
