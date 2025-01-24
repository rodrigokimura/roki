from roki.firmware.utils import decode_float, decode_vector, encode_float, encode_vector


def test_encode_vector():
    result = encode_vector(5, 7)
    assert result == 87


def test_decode_vector():
    result = decode_vector(87)
    assert result == (5, 7)


def test_encode_float():
    assert encode_float(-0.2) == 153


def test_decode_float():
    print(encode_float(0.5))
    # decode_float()
    r = decode_float(64)
    print(r)
