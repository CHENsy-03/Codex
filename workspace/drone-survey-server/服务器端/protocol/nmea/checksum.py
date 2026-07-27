# -*- coding: utf-8 -*-
"""V2.1 NMEA Checksum - XOR verification for GPGGA sentences"""
def verify(sentence: str) -> bool:
    if "*" not in sentence:
        return False
    data, checksum = sentence.rsplit("*", 1)
    calc = 0
    for c in data[1:]:
        calc ^= ord(c)
    return format(calc, "02X") == checksum.strip()[:2]
def compute(sentence_without_star: str) -> str:
    calc = 0
    for c in sentence_without_star.lstrip("$"):
        calc ^= ord(c)
    return format(calc, "02X")
