# -*- coding: utf-8 -*-
import re
from pathlib import Path

# -----------------------------
# 민감 정보 패턴 정의 (붙어 있어도 매칭 가능)
# -----------------------------
patterns = [
    # 주민등록번호 / 외국인 등록번호
    ("RRN", re.compile(r"\d{6}-?\d{7}")),

    # 여권
    ("PASSPORT1", re.compile(r"[A-Za-z]\d{3}[A-Za-z]\d{4}", re.IGNORECASE)),   # 차세대 전자여권 ANNNANNNN
    ("PASSPORT2", re.compile(r"[A-Za-z]\d{8}", re.IGNORECASE)),                # 차세대 전자여권 이전 ANNNNNNNN
    ("PASSPORT3", re.compile(r"[A-Za-z]{2}\d{7}", re.IGNORECASE)),             # 초기 전자여권 AANNNNNNN

    # 전화번호: 모바일/지역번호/단축번호 +82 포함
    ("PHONE", re.compile(
        r"(?<!\d)(?:"
        r"\+82[-.\s]?\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}"   # +82 국가번호
        r"|010[-.\s]?\d{3,4}[-.\s]?\d{4}"                # 010 모바일
        r"|0\d{1,2}[-\).\s]?\d{3,4}[-.\s]?\d{4}"         # 지역번호 포함 일반 전화
        r"|\d{4}[-.\s]\d{4}"                               # 대표번호는 구분자 필수
        r")(?!\d)"  
    )),

    # IPv4
    ("IPV4", re.compile(
        r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
        r"(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}"
    )),

    # IPv6 (주요 형태)
    ("IPV6", re.compile(
        r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
        r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
        r"|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}"
    )),

    # 이메일
    ("EMAIL", re.compile(r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")),   #이메일 

    # 계좌번호: 은행 포맷 (2~6자리)-(2~6자리)-(2~7자리), 구분자(하이픈/공백) 필수, '.' 제외
    ("ACCOUNT", re.compile(r"\b\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}\b")),
]

# -----------------------------
# 파일 입출력
# -----------------------------
input_file = Path("input.txt")
output_file = Path("output.txt")

with input_file.open(encoding="utf-8") as f, output_file.open("w", encoding="utf-8") as out_f:
    text = f.read()
    masked_text = text
    # 패턴별 치환
    for label, pat in patterns:
        masked_text = pat.sub(f"[{label}]", masked_text)
    out_f.write(masked_text)

print(f"마스킹 완료! 결과는 '{output_file}'에 저장되었습니다.")