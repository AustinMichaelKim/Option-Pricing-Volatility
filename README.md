# Option Pricing and Volatility Analysis

Hull의 옵션 관련 장을 읽고, 실제 옵션 데이터를 이용해 가격결정 모형과
변동성 분석을 단계적으로 실험하는 Python 프로젝트입니다.

이 저장소는 Jupyter Notebook을 주 작업 공간으로 사용합니다. 노트북에서
아이디어를 검증한 뒤 재사용할 가치가 있는 계산 로직만 `src/` 패키지로
옮깁니다.

## 범위

- 실제 옵션체인 수집 및 정리
- Binomial option pricing
- Geometric Brownian Motion (GBM)
- Black-Scholes-Merton (BSM)
- Monte Carlo simulation
- Implied volatility
- Delta hedging
- Hull Chapter 10, 11, 13, 14, 15 독해 기록

현재 단계에서는 프로젝트 구조만 제공합니다. 금융모형의 계산 로직은 아직
구현하지 않습니다.

## 작업 흐름

1. `docs/reading_notes/`에 개념, 수식, 가정과 질문을 정리합니다.
2. 주제에 대응하는 `notebooks/` 하위 디렉터리에서 실험합니다.
3. 데이터 처리나 계산 로직이 안정되면 작은 함수 단위로 `src/`에 옮깁니다.
4. 이후 노트북은 복사된 코드를 유지하지 않고 `src` 패키지에서 import합니다.
5. 옮긴 로직에는 `tests/`의 pytest 테스트를 추가합니다.

노트북은 `01_topic_description.ipynb`처럼 실행 순서를 알 수 있는 이름을
사용합니다. 커밋하기 전 출력에 원본 데이터나 비밀정보가 포함되지 않았는지
확인합니다.

## 디렉터리

```text
.
├── data/                         # 로컬 데이터 저장소(Git 제외)
│   ├── raw/
│   ├── interim/
│   └── processed/
├── docs/reading_notes/           # Hull 독해 노트
├── notebooks/                    # 탐색, 실험, 그래프의 주 작업 공간
│   ├── 00_sandbox/
│   ├── 01_option_chain/
│   ├── 02_binomial/
│   ├── 03_gbm/
│   ├── 04_bsm/
│   ├── 05_monte_carlo/
│   ├── 06_implied_volatility/
│   └── 07_delta_hedging/
├── src/option_pricing_volatility/ # 검증된 재사용 Python 코드
└── tests/                         # pytest 테스트
```

## 개발 환경

프로젝트 루트에서 가상환경을 만들고 개발 및 노트북 dependency를
설치합니다. 두 그룹은 선택 dependency이며 패키지의 런타임 dependency는
없습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,notebook]"
python -m jupyter lab
```

패키지 import와 테스트는 다음과 같이 확인합니다.

```bash
python -c "import option_pricing_volatility"
python -m pytest
```

editable install 전에는 다음처럼 직접 확인할 수 있습니다.

```bash
PYTHONPATH=src python3 -c "import option_pricing_volatility"
```

## 데이터와 비밀정보

- 다운로드한 옵션체인과 모든 파생 데이터는 `data/` 아래에만 저장합니다.
- `data/README.md`와 디렉터리 유지용 `.gitkeep` 이외의 데이터 파일은 Git에서
  제외됩니다.
- API 키와 계정 정보는 `.env` 같은 로컬 파일에만 두며 커밋하지 않습니다.
- 재현에 필요한 환경변수 이름이 생기면 값이 없는 `.env.example`만 추가합니다.
