# hello-world
just another repository

## OKLab PPT 색조(Tone) 설정 도구

`oklab_ppt/`는 OKLab 색 공간을 이용해 하나의 기준 색상에서 색조(hue)는
고정하고 명도(L)만 단계적으로 바꾼 "톤 팔레트"를 만들고, 이를
PowerPoint(.pptx) 파일에 적용하는 CLI 도구입니다.

RGB나 HSL로 밝기를 조절하면 단계별 밝기 차이가 눈에 고르게 느껴지지 않는
경우가 많습니다. CIELAB도 이를 어느 정도 해결하지만, 특히 파란색 계열에서
명도가 바뀔 때 색조가 보라 쪽으로 틀어지는 문제가 있습니다. OKLab은 이
문제를 개선해서, 같은 색조를 유지한 채 훨씬 더 자연스러운 명도 단계를
만들 수 있습니다.

### 설치

```bash
pip install -r oklab_ppt/requirements.txt
```

### 사용법

```bash
# 1) 팔레트만 미리 확인 (OKLab 값 + hex)
python3 oklab_ppt/cli.py palette "#2E86AB" --steps 6

# 2) pptx 테마 색상(dk1/lt1/accent1-6 등)에 팔레트 적용
python3 oklab_ppt/cli.py theme "#2E86AB" --steps 8 --out my_deck.pptx
#   --template existing.pptx 를 추가하면 기존 파일의 테마 색을 덮어씁니다.

# 3) 팔레트를 색상 견본(swatch) 슬라이드로 눈으로 확인
python3 oklab_ppt/cli.py swatches "#2E86AB" --steps 6 --out swatches.pptx

# 4) 기존 pptx의 특정 도형을 팔레트 그라데이션으로 채우기
python3 oklab_ppt/cli.py gradient "#2E86AB" --steps 5 --l-min 0.10 --l-max 0.55 \
    --template existing.pptx --shape "직사각형 2" --angle 45 --out existing_gradient.pptx
#   --shape는 도형의 정확한 이름(PowerPoint의 선택 창에서 확인 가능), --slide로 특정
#   슬라이드만 지정할 수도 있습니다(기본값: 이름이 일치하는 모든 슬라이드).
#   --text-color/--text-shapes를 추가하면 지정한 도형(제목/부제목 등)의 텍스트 색도
#   함께 바꿔서, 밝은 배경에 흰 텍스트가 묻히는 문제를 같이 해결할 수 있습니다.
python3 oklab_ppt/cli.py gradient "#FF1234" --color2 "#FFCB23" --steps 3 --angle 154 \
    --template existing.pptx --shape "직사각형 2" \
    --text-color black --text-shapes "제목 1,부제목 5" --out existing_gradient.pptx

# 6) 선형 대신 방사형/사각형 그라데이션 + 중심 위치 지정
python3 oklab_ppt/cli.py gradient "#7A0C1E" --color2 "#A67C00" --steps 5 \
    --type radial --center "top-left" \
    --template existing.pptx --shape "직사각형 2" --out existing_radial.pptx
#   --type linear(기본)/radial/rectangular, --center는 키워드(center, top-left, top,
#   top-right, left, right, bottom-left, bottom, bottom-right) 또는 "X%,Y%" 형식.
#   --type linear일 때는 --angle이, 그 외에는 --center가 적용됩니다.

# 7) 방사형/사각형 그라데이션을 여러 시작 위치에서 섞기
python3 oklab_ppt/cli.py gradient "#7A0C1E" --color2 "#A67C00" --steps 5 \
    --type radial --center "top-left;bottom-right" \
    --template existing.pptx --shape "직사각형 2" --out existing_multi.pptx
#   --center를 ';'로 구분해 여러 개 지정하면, 각 위치에서 시작하는 그라데이션을
#   가장자리가 투명해지는 도형 여러 장으로 겹쳐 쌓아서 서로 자연스럽게 섞습니다.
#   (OOXML gradFill 자체는 중심을 하나만 가질 수 있어서, 도형을 복제해 구현합니다.)

# 5) 색조 유지 대신 두 색 사이를 보간(예: 빨강 -> 노랑)
python3 oklab_ppt/cli.py gradient "#7A0C1E" --color2 "#A67C00" --steps 5 \
    --template existing.pptx --shape "직사각형 2" --angle 45 --out existing_red_yellow.pptx
#   --color2를 지정하면 --l-min/--l-max는 무시되고, OKLab 공간에서 두 색을 직선으로
#   보간합니다. palette/theme/swatches에도 동일하게 --color2를 쓸 수 있습니다.
```

`--l-min`, `--l-max`(OKLab L, 0=검정 ~ 1=흰색)로 가장 어두운/밝은 톤의
명도 범위를 조절할 수 있습니다.
