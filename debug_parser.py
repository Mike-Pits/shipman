#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.disp_parser import disp_parser

# Replace this with the actual raw text from the email
raw_text = """т/к СП Дудинка

Дисп. 05/01-2026

1 1901/0800

2 6903N/03303E Порт Мурманск, Якорная стоянка №77/11

4 170/11

5 170/0,5

6 546,235/214,376

26 1501/1208

27 2001/AM

36 47

43 Мурманск

44 1501/1208

100 1801/1740 т/к «Берген Т» ошвартовался к левому борту судна. Бункеровка

        1801/2208 т/к «Берген Т» отошел от л/борта. Принято IFO – 221,62 т

Проспекты (с дальнейшим уточнением):

        2001/AM – Предполагаемая дата снятия с якоря (с уточнением)
"""

result = disp_parser.parse(raw_text)

print("=== PARSER OUTPUT ===")
for key, value in result.items():
    print(f"{key:25}: {value}")