# -*- coding: utf-8 -*-
import re
from pathlib import Path
from schools import school_list

# -----------------------------
# 파일 경로
# -----------------------------
input_file = Path("input.txt")
output_file = Path("output.txt")

# -----------------------------
# 1️⃣ 정규표현식 기반 학교명 패턴
# -----------------------------
patterns = [
    re.compile(r"[가-힣]{2,}(?:초등학교|중학교|고등학교|대학교)"),  # 풀네임
    re.compile(r"[가-힣]{2,}(?:고교|대학|여대)")                     # 축약형
]
# -----------------------------
# 3️⃣ 파일 읽기
# -----------------------------
with input_file.open(encoding="utf-8") as f:
    text = f.read()

masked_text = text

# -----------------------------
# 4️⃣ 정규표현식 치환
# -----------------------------
for pat in patterns:
    for match in pat.findall(masked_text):
        masked_text = masked_text.replace(match, "[학교명]")

# -----------------------------
# 5️⃣ 사전 기반 치환
# -----------------------------
for school in school_list:
    masked_text = masked_text.replace(school, "[학교명]")

# -----------------------------
# 6️⃣ 결과 저장
# -----------------------------
with output_file.open("w", encoding="utf-8") as f:
    f.write(masked_text)

print(f"마스킹 완료! 결과는 '{output_file}'에 저장되었습니다.")
