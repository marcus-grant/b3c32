# python/tests/vectors.py
"""
Hand-derived conformance literals shared by the test modules.

This is the single copy the generator script drifts against; it must
hold every value that scripts/generate-conformance-vectors.py also
holds as a literal. Presentation wrappers (pytest.param lists) stay
in the test modules that use them.

Original of this file was moved from old main test module test_b3c32.py.
These original elements were from that module's state at 2026-07-22.

Author: Marcus Grant
OriginDate: 2026-07-22
Date: 2026-09-11
License: Apache-2.0
"""


# Vectors here are hand-derived and confirmed against independent codecs.
# scripts/audit-conformance-vectors.sh rederives the published set using only
# external tools, with nothing from this implementation in the loop.

KNOWN_ENCODE_VECTORS = [
    (b"", "", "empty"),
    (b"\x00", "00", "single_zero"),  # Start hand-derived edge-crossing vectors
    (b"\x1f", "3W", "single_31"),
    (b"\xff", "ZW", "single_255"),
    (b"\x00\x01", "000G", "trailing_one"),
    (b"\x84\x21", "GGGG", "walking_ones"),
    (b"\x00" * 5, "00000000", "5x_zero"),
    (b"\xff" * 5, "ZZZZZZZZ", "5x_ff"),
    (b"\xaa\xaa\xaa", "NANAM", "3x_aa"),
    (b"f", "CR", "IETF-draft-f"),  # Start of draft IETF examples, Section 3.1
    (b"fo", "CSQG", "IETF-draft-fo"),
    (b"foo", "CSQPY", "IETF-draft-foo"),
    (b"foob", "CSQPYRG", "IETF-draft-foob"),
    (b"fooba", "CSQPYRK1", "IETF-draft-fooba"),
    (b"foobar", "CSQPYRK1E8", "IETF-draft-foobar"),
    (b"test", "EHJQ6X0", "IETF-draft-test"),
]

# Contract 4.6. 0xAA repeated, lengths 10-14 covering all five pad residues.
PERIODIC_AA_VECTORS = [
    (10, "NANANANANANANANA"),
    (11, "NANANANANANANANAN8"),
    (12, "NANANANANANANANANAN0"),
    (13, "NANANANANANANANANANAM"),
    (14, "NANANANANANANANANANANAG"),
]


# Contract 4.6. 0xFF repeated, same lengths. Uniform period, tail-confirmer only.
PERIODIC_FF_VECTORS = [
    (10, "Z" * 16),
    (11, ("Z" * 17) + "W"),
    (12, ("Z" * 19) + "G"),
    (13, ("Z" * 20) + "Y"),
    (14, ("Z" * 22) + "R"),
]

# Contract 4.6. 0x00 repeated, same lengths. Tail-blind, certifies length only.
PERIODIC_ZERO_VECTORS = [
    (10, "0" * 16),
    (11, "0" * 18),
    (12, "0" * 20),
    (13, "0" * 21),
    (14, "0" * 23),
]


REFERENCE_ENCODED_VECTORS = [
    (0, "NW9MKEFNZ6GTD8209QN3DQ69"),
    (1023, "2088JW7EV8ZBJCNTNGA2HHX2"),
    (1024, "88GMEEFGJPJ0DWZWGFFBH2BM"),
    (1025, "T017HBJ7XCKV6KXESXKV9ZH6"),
    (2049, "BX6Q5X0DF9FR5CAWMASE8JRX"),
]

CONVENIENCE_ENCODED_VECTORS = [
    (b"Hello, World!\n", "C8SR6JYEF0BXP7J03F7EMAWB", "hello"),
    (b"\x00\xff\r\n\x1a", "56V71DGBAMEA57K94KP1NKF8", "hard_bytes"),
    (b"\xe2\x9c\x85", "2A9V46HDZYE86ESAZ71PZ8Y6", "check_emoji"),
]


def reference_input(input_len: int) -> bytes:
    """Reconstruct a reference input: byte i is i mod 251, per vector file rule."""
    return bytes(i % 251 for i in range(input_len))


def chunked(data: bytes, chunk_size: int | None) -> list[bytes]:
    """Split data into chunk_size pieces; None means one whole chunk."""
    if chunk_size is None:
        return [data]
    return [data[i : (i + chunk_size)] for i in range(0, len(data), chunk_size)]
