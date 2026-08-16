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
```

`--l-min`, `--l-max`(OKLab L, 0=검정 ~ 1=흰색)로 가장 어두운/밝은 톤의
명도 범위를 조절할 수 있습니다.
