# 🧱 Image Search Domain

이미지 장소 검색 모듈의 **데이터 계약 DTO와 provider 원신호 모델, 그리고 공용 카테고리 어휘**를 정의합니다.

이 디렉터리는 사진을 인식하거나 외부 API를 호출하지 않습니다. Provider 구현과 Application(`PlaceRecognizer`), 그리고 백엔드 사이에서 오가는 **데이터 계약과 기본 필드 검증**만 담당합니다.

> 상위 문서: [Image Search](../README.md)

<br>

## 📚 목차

1. [🎯 디렉터리 역할](#-디렉터리-역할)
2. [📁 파일 구성](#-파일-구성)
3. [🗂️ 장소 카테고리 (PlaceCategory)](#-장소-카테고리-placecategory)
4. [🔬 Provider 원신호 모델](#-provider-원신호-모델)
5. [📥 요청 DTO (ImageSearchRequest)](#-요청-dto-imagesearchrequest)
6. [📦 결과 DTO](#-결과-dto)
7. [🔒 도메인 불변조건](#-도메인-불변조건)
8. [⚠️ 현재 모델의 주의사항](#-현재-모델의-주의사항)
9. [🔗 관련 문서](#-관련-문서)

<br>


## 🎯 디렉터리 역할

`ai/image_search/domain`은 다음 책임을 가집니다.

- 사진을 이해하는 세 외부 소스의 원신호를 내부 모델로 표현
- Cloud Vision 랜드마크 감지 원신호(`LandmarkDetection`) 정의
- Gemini 비전 식별 원신호(`VisionIdentification`) 정의
- Google Places로 확정한 실제 장소 정보(`ResolvedPlace`) 정의
- 사진 식별과 근처 추천 필터에 공통으로 쓰는 폐집합 어휘 `PlaceCategory` 정의
- 백엔드와 주고받는 요청 DTO(`ImageSearchRequest`) 정의
- 백엔드 후보 계약 DTO(`PlaceCandidate`)와 결과 래퍼(`ImageSearchResult`) 정의
- 후보 출처(`CandidateSource`)와 인식 상태(`RecognitionStatus`) Enum 정의
- 원신호 로깅 컨테이너(`RecognitionSignals`) 정의
- DTO 생성 단계의 기본 타입·범위 검증과 요청 최소 조건 검증

도메인 모델은 Provider 구현과 Application(`PlaceRecognizer`), 그리고 백엔드 계약 사이의 공통 언어로 사용됩니다.

```text
Backend Request
→ ImageSearchRequest
→ PlaceRecognizer (LandmarkDetection · VisionIdentification · ResolvedPlace)
→ ImageSearchResult (PlaceCandidate 목록)
→ Backend Response
```

이 디렉터리의 두 파일은 서로 다른 대상을 향합니다.

```text
schemas.py         내부/provider 방향 (원신호 · 공용 어휘)
search_schemas.py  백엔드 계약 방향 (요청 · 후보 · 결과)
```

> **관련 문서**
>
> - [Image Search](../README.md) — 도메인 모델이 흐르는 전체 처리 순서
> - [Services](../services/README.md) — 원신호를 조합해 `ImageSearchResult`를 만드는 계층
> - [Providers](../providers/README.md) — 원신호를 생산하는 외부 연동

<br>

## 📁 파일 구성

```text
ai/image_search/domain/
├── README.md
├── schemas.py          provider 원신호 모델 + PlaceCategory 어휘
└── search_schemas.py   백엔드 계약 DTO (요청 · 후보 · 결과)
```

| 파일 | 책임 |
|---|---|
| `schemas.py` | `PlaceCategory` 어휘와 provider 원신호 모델 `LandmarkDetection` · `VisionIdentification` · `ResolvedPlace` |
| `search_schemas.py` | 계약 Enum `CandidateSource` · `RecognitionStatus`, 요청 `ImageSearchRequest`, 후보 `PlaceCandidate`, 원신호 로깅 `RecognitionSignals`, 결과 `ImageSearchResult` |

### 의존 방향은 한 방향

`search_schemas.py`는 `schemas.py`에서 `LandmarkDetection`, `PlaceCategory`, `VisionIdentification`을 import합니다. 반대 방향은 없습니다.

```text
search_schemas.py  ──import──▶  schemas.py
      (계약 DTO)                  (원신호 · 공용 어휘)

역방향 금지: schemas.py 는 search_schemas.py 를 알지 못한다
```

이 규칙은 코드 주석에 명시되어 있습니다.

```text
# 내부 모델(원신호·Places 결과)은 domain/schemas.py 에 있다.
# 의존은 이 파일 → schemas 한 방향만 허용.
```

원신호·어휘를 정의하는 쪽이 계약 DTO를 참조하지 않으므로, provider 계층은 계약 DTO를 몰라도 원신호를 생산할 수 있습니다. 계약을 조립하는 책임은 계약 파일과 Application 계층에 모입니다.

<br>


## 🗂️ 장소 카테고리 (PlaceCategory)

`PlaceCategory`는 `str` 기반 `Enum`으로, 사진 기반 식별과 근처 추천 필터에 공통으로 쓰는 폐집합 택소노미입니다. 내부 원신호(`VisionIdentification.category`)와 계약 후보(`PlaceCandidate.category`) 양쪽이 같은 어휘를 참조하므로, 두 파일이 공유하는 유일한 어휘 타입입니다.

### 카테고리 그룹

코드는 카테고리를 다섯 그룹의 주석으로 묶어 선언합니다.

```text
명소·역사·문화   LANDMARK · TEMPLE_SHRINE · HISTORIC · MUSEUM · GALLERY · ARCHITECTURE
자연·풍경        NATURE · PARK · GARDEN · BEACH · VIEWPOINT · NIGHTVIEW · ONSEN
음식·카페        CAFE · RESTAURANT · DESSERT · BAR · MARKET
활동·쇼핑·거리   SHOPPING · STREET · THEME_PARK · AQUARIUM_ZOO
기타            ETC
```

### 전체 값과 의미

값과 이름은 동일합니다(`LANDMARK = "LANDMARK"` 형태). 각 값의 뜻은 코드 주석 기준입니다.

| 값 | 의미 |
|---|---|
| `LANDMARK` | 랜드마크·명소 |
| `TEMPLE_SHRINE` | 사찰·신사 |
| `HISTORIC` | 유적·역사지구·성(城) |
| `MUSEUM` | 박물관 |
| `GALLERY` | 미술관·갤러리 |
| `ARCHITECTURE` | 건축물·근대건축 |
| `NATURE` | 자연·산·숲 |
| `PARK` | 공원 |
| `GARDEN` | 정원 |
| `BEACH` | 해변·바다 |
| `VIEWPOINT` | 전망대·뷰포인트 |
| `NIGHTVIEW` | 야경 |
| `ONSEN` | 온천 |
| `CAFE` | 카페 |
| `RESTAURANT` | 음식점 |
| `DESSERT` | 디저트·베이커리 |
| `BAR` | 바·이자카야 |
| `MARKET` | 시장·먹자골목 |
| `SHOPPING` | 쇼핑·상점가 |
| `STREET` | 거리·골목 풍경 |
| `THEME_PARK` | 테마파크·놀이공원 |
| `AQUARIUM_ZOO` | 수족관·동물원 |
| `ETC` | 기타 |

### 폐집합이라는 성질

`ETC`를 제외한 값 22개는 특정 성격을 지목하고, `ETC` 하나가 나머지를 흡수합니다. 카테고리는 클라이언트가 임의 문자열로 전달하는 값이 아니라 서버 도메인 Enum으로 고정됩니다.

```text
목록에 있는 성격      해당 값으로 분류
목록에 없는 성격      가장 가까운 값으로 근사, 또는 ETC
```

애매한 경계(예: `CAFE`와 `DESSERT`, `RESTAURANT`와 `BAR`)에서 불확실함은 카테고리를 바꾸는 방식이 아니라 `confidence`를 낮추는 방식으로 표현하도록 설계되었습니다. 이 판단 규칙 자체는 Application·Provider 계층에 있고, 도메인은 값의 폐집합만 보장합니다.

> **관련 문서**
>
> - [Providers](../providers/README.md) — `VisionLlmProvider`가 카테고리를 채우는 규칙
> - [Services](../services/README.md) — 카테고리를 근처 추천 필터로 쓰는 단계

<br>

## 🔬 Provider 원신호 모델

`schemas.py`는 세 외부 소스가 준 "가공 전 신호"를 각각 Pydantic 모델로 표현합니다. 세 모델은 계약 DTO가 아니라 내부 모델이며, 계약 파일이 이 셋을 참조하는 것은 허용되지만 세 모델이 계약 파일을 참조하지는 않습니다.

```text
LandmarkDetection     Cloud Vision 랜드마크 감지 원신호
VisionIdentification  Gemini 비전 식별 원신호
ResolvedPlace         Google Places 로 확정한 실제 장소
```

### LandmarkDetection

Cloud Vision 랜드마크 감지가 준 하나의 후보를 표현합니다.

```text
LandmarkDetection
├── name        str
├── latitude    float   (-90 ≤ x ≤ 90)
├── longitude   float   (-180 ≤ x ≤ 180)
└── score       float   (0 ≤ x ≤ 1)   Vision 신뢰도
```

| 필드 | 타입 | 제약 |
|---|---|---|
| `name` | `str` | 필수 |
| `latitude` | `float` | `ge=-90`, `le=90` |
| `longitude` | `float` | `ge=-180`, `le=180` |
| `score` | `float` | `ge=0`, `le=1` |

랜드마크 감지는 좌표를 함께 반환하므로 이 모델에는 위·경도가 있습니다. 그러나 이 좌표는 모듈의 1급 불변조건에 따라 그대로 쓰이지 않고, `name`을 검색어로 삼아 Places가 좌표를 재확정합니다. 좌표 필드는 원신호를 있는 그대로 보존하기 위한 것이며 최종 사실이 아닙니다.

### VisionIdentification

Gemini 비전 식별이 준 결과입니다. 랜드마크와 달리 좌표 필드가 없습니다.

```text
VisionIdentification
├── place_name_guess  str | None = None            추정 장소명 (없을 수 있음)
├── category          PlaceCategory                추정 카테고리/분위기
├── vibe_keywords     list[str] = []               분위기 키워드
├── reason            str                          추정 근거
├── confidence        float (0 ≤ x ≤ 1)            LLM 자기 확신도
└── visible_text      list[str] = []               사진 속 간판/글자 (장소 특정 단서)
```

| 필드 | 타입 | 제약 · 기본값 |
|---|---|---|
| `place_name_guess` | `str \| None` | 기본 `None` |
| `category` | `PlaceCategory` | 필수 |
| `vibe_keywords` | `list[str]` | 기본 `default_factory=list` |
| `reason` | `str` | 필수 |
| `confidence` | `float` | `ge=0`, `le=1` |
| `visible_text` | `list[str]` | 기본 `default_factory=list` |

이 모델에는 위·경도가 없습니다. 비전 LLM에는 애초에 좌표를 맞히라고 요구하지 않으며, 위치 확정은 다음 단계(Places)의 책임입니다. `category`는 필수라서 LLM은 항상 폐집합 중 하나를 골라야 하고, `place_name_guess`는 `None`일 수 있어 이름 추정이 없을 수도 있습니다. `visible_text`는 사진 속 간판·글자로, 장소를 특정하는 추가 단서로 쓰입니다.

### ResolvedPlace

Google Places로 확정한 실제 장소입니다. 좌표는 항상 여기서 나옵니다.

```text
ResolvedPlace
├── place_id           str
├── name               str
├── latitude           float (-90 ≤ x ≤ 90)
├── longitude          float (-180 ≤ x ≤ 180)
├── formatted_address  str | None = None
├── city               str | None = None
├── country            str | None = None
├── rating             float | None = None  (0 ≤ x ≤ 5)
├── review_count       int | None = None    (x ≥ 0)     내부 미사용·보관만
└── primary_type       str | None = None                내부 미사용·보관만
```

| 필드 | 타입 | 제약 · 기본값 |
|---|---|---|
| `place_id` | `str` | 필수 |
| `name` | `str` | 필수 |
| `latitude` | `float` | `ge=-90`, `le=90` |
| `longitude` | `float` | `ge=-180`, `le=180` |
| `formatted_address` | `str \| None` | 기본 `None` |
| `city` | `str \| None` | 기본 `None` |
| `country` | `str \| None` | 기본 `None` |
| `rating` | `float \| None` | 기본 `None`, `ge=0`, `le=5` |
| `review_count` | `int \| None` | 기본 `None`, `ge=0` |
| `primary_type` | `str \| None` | 기본 `None` |

`city`와 `country`는 Places의 addressComponents에서 구조화 파싱한 값으로, 백엔드 계약 매핑을 위해 존재합니다. 마지막 두 필드 `review_count`와 `primary_type`은 파싱해 보관만 하며, 코드 주석에 따르면 현재 내부 로직에서 사용하지 않고 백엔드 매핑·향후 활용을 대비한 필드입니다.

```text
Places 응답 → ResolvedPlace
             ├─ 좌표·place_id·주소   최종 사실로 채택
             ├─ city·country         계약 매핑용 파싱값
             └─ review_count·primary_type   보관만(현재 미사용)
```

> **관련 문서**
>
> - [Providers](../providers/README.md) — 세 원신호를 각각 생산하는 provider
> - [Services](../services/README.md) — 원신호를 시드·확정으로 조합하는 순서

<br>

## 📥 요청 DTO (ImageSearchRequest)

`ImageSearchRequest`는 `search_schemas.py`에 정의된 요청 DTO이며, 코드 주석에 따르면 백엔드 `PhotoPlaceSearchRequest`의 상위집합입니다.

```text
ImageSearchRequest
├── image_url        str | None = None    호스팅 이미지 URL
├── image_path       str | None = None    로컬 파일 경로
├── note             str | None = None    사용자 메모 (예: "야경")
├── latitude         float | None = None  촬영/현재 위치 힌트
├── longitude        float | None = None
├── city             str | None = None    여행 맥락 힌트
├── country          str | None = None
└── max_candidates   int = 5              반환 후보 최대 개수
```

### 필드 제약

| 필드 | 타입 | 제약 · 기본값 |
|---|---|---|
| `image_url` | `str \| None` | 기본 `None`, `min_length=1` |
| `image_path` | `str \| None` | 기본 `None`, `min_length=1` |
| `note` | `str \| None` | 기본 `None`, `min_length=1` |
| `latitude` | `float \| None` | 기본 `None`, `ge=-90`, `le=90` |
| `longitude` | `float \| None` | 기본 `None`, `ge=-180`, `le=180` |
| `city` | `str \| None` | 기본 `None`, `min_length=1` |
| `country` | `str \| None` | 기본 `None`, `min_length=1` |
| `max_candidates` | `int` | 기본 `5`, `ge=1` |

`min_length=1`은 빈 문자열을 거부합니다. 값을 전달하지 않으려면 필드를 생략하거나 `None`으로 두어야 하고, `""`를 넣으면 검증에서 걸립니다. `max_candidates`는 1 이상이며, 이 값이 1이면 근처 추천 없이 식별 장소 하나만 요청한 것으로 해석됩니다(해석 자체는 Application 책임).

### 이미지 소스 최소 조건

`image_url`과 `image_path`는 둘 다 선택 필드이지만, 요청 전체로는 **최소 하나가 반드시 있어야** 합니다. 이 조건은 `mode="after"` `model_validator`로 검증합니다.

```text
@model_validator(mode="after")
_require_image_source:
    image_url 도 없고 image_path 도 없으면
        → ValueError("image_url 또는 image_path 중 하나는 반드시 필요합니다.")
```

두 필드 각각의 `min_length=1`은 "값이 있다면 비어 있지 않다"를 보장하고, `_require_image_source`는 "적어도 하나는 값이 있다"를 보장합니다. 둘 다 지정하는 것 자체는 이 검증에서 막지 않습니다.

```text
image_url 만 있음        통과
image_path 만 있음       통과
둘 다 있음               통과 (소스 선택은 Application 책임)
둘 다 없음               ValueError
```

위치 힌트(`latitude`·`longitude`·`city`·`country`)는 값 범위만 검증할 뿐, 현재 도메인·서비스에서 Places 검색의 locationBias로는 활용되지 않습니다(상위 문서 "현재 한계" 참고).

> **관련 문서**
>
> - [Image Search](../README.md) — 입력과 출력 요약
> - [Services](../services/README.md) — `image_url`·`image_path`를 안전하게 로딩하는 `image_loader`

<br>

## 📦 결과 DTO

`search_schemas.py`의 나머지는 백엔드로 돌려주는 결과 계약입니다. 계약 Enum 두 개, 후보 모델, 원신호 로깅 컨테이너, 그리고 결과 래퍼로 구성됩니다.

### CandidateSource

후보가 어느 경로로 나왔는지 표시하는 내부 분류 Enum입니다.

```text
LANDMARK   랜드마크 식별에서 나온 후보
LLM        비전 LLM 식별에서 나온 후보
NEARBY     근처 추천에서 나온 후보
```

### RecognitionStatus

인식 결과 상태 Enum입니다.

```text
SUCCESS   식별 + 요청한 근처 추천까지 확보 (또는 애초에 근처 미요청)
PARTIAL   식별은 됐으나 요청한 근처 추천을 얻지 못함
FAILED    식별 자체 실패 (시드 없음 또는 Places 확정 실패)
```

상태 판정 로직은 Application 계층에 있고, 도메인은 세 값의 집합만 정의합니다.

### PlaceCandidate

최종 장소 후보 모델입니다. 코드 주석에 따르면 앞쪽은 백엔드 `PhotoPlaceCandidateRead`에 1:1 매핑되는 계약 필드, 뒤쪽은 seam에서 무시되는 내부 확장 필드입니다.

```text
PlaceCandidate
│  --- 백엔드 계약 매핑 필드 ---
├── name         str
├── city         str
├── country      str
├── latitude     float (-90 ≤ x ≤ 90)
├── longitude    float (-180 ≤ x ≤ 180)
├── confidence   float (0 ≤ x ≤ 1)
├── reason       str
│  --- 내부 분류 필드 ---
├── category     PlaceCategory
├── source       CandidateSource
│  --- 내부 선택 필드 ---
├── place_id     str | None = None
└── rating       float | None = None (0 ≤ x ≤ 5)
```

필드는 세 묶음으로 나뉩니다.

| 묶음 | 필드 | 성격 |
|---|---|---|
| 계약 매핑 | `name` · `city` · `country` · `latitude` · `longitude` · `confidence` · `reason` | 백엔드 `PhotoPlaceCandidateRead`와 1:1 |
| 내부 분류 | `category` · `source` | 카테고리 어휘와 출처 표시 |
| 내부 선택 | `place_id` · `rating` | 있으면 채우고 seam에서 무시 |

필드 제약:

| 필드 | 타입 | 제약 · 기본값 |
|---|---|---|
| `name` | `str` | 필수 |
| `city` | `str` | 필수 |
| `country` | `str` | 필수 |
| `latitude` | `float` | `ge=-90`, `le=90` |
| `longitude` | `float` | `ge=-180`, `le=180` |
| `confidence` | `float` | `ge=0`, `le=1` |
| `reason` | `str` | 필수 |
| `category` | `PlaceCategory` | 필수 |
| `source` | `CandidateSource` | 필수 |
| `place_id` | `str \| None` | 기본 `None` |
| `rating` | `float \| None` | 기본 `None`, `ge=0`, `le=5` |

주목할 대비가 있습니다. `PlaceCandidate`에서 `city`와 `country`는 **필수 문자열**인데, 원신호 쪽 `ResolvedPlace`에서는 같은 필드가 `str | None`으로 **선택**입니다. 계약이 두 값을 요구하므로, Places가 `city`·`country`를 채우지 못한 경우 후보를 조립하는 Application 계층이 빈 값을 메워야 합니다(이 메우기 책임은 도메인이 아니라 서비스에 있습니다).

```text
ResolvedPlace.city / country   선택 (없을 수 있음)
        │
        ▼  (Application 매핑)
PlaceCandidate.city / country  필수 (반드시 채워야 계약 통과)
```

### RecognitionSignals

원신호 로깅용 컨테이너입니다. 코드 주석에 따르면 추후 병렬 앙상블 확장을 대비합니다.

```text
RecognitionSignals
├── landmark   LandmarkDetection | None = None
└── llm        VisionIdentification | None = None
```

계약 파일이 `schemas.py`의 원신호 모델을 참조하는 지점이 바로 여기입니다. 두 슬롯 모두 단일 값이라 현재는 랜드마크 하나·LLM 하나만 담습니다.

### ImageSearchResult

사진 장소 검색의 최종 결과 래퍼입니다.

```text
ImageSearchResult
├── identified   PlaceCandidate | None            식별된 1순위 장소 (실패 시 None)
├── candidates   list[PlaceCandidate] = []        식별 + 근처 추천
├── status       RecognitionStatus
└── signals      RecognitionSignals
```

| 필드 | 타입 | 제약 · 기본값 |
|---|---|---|
| `identified` | `PlaceCandidate \| None` | 필수(값 자체는 `None` 허용) |
| `candidates` | `list[PlaceCandidate]` | 기본 `default_factory=list` |
| `status` | `RecognitionStatus` | 필수 |
| `signals` | `RecognitionSignals` | 필수 |

`identified`는 타입에 `None`을 허용하지만 필드 선언 자체에 기본값이 없어, 결과를 만들 때 반드시 값을 지정해야 합니다(실패면 명시적으로 `None`). `candidates`는 식별 장소와 근처 추천 후보를 함께 담는 목록이며 기본은 빈 목록입니다.

> **관련 문서**
>
> - [Image Search](../README.md) — 인식 상태와 근처 추천 규칙
> - [Services](../services/README.md) — `ImageSearchResult`를 조립하는 `PlaceRecognizer`
> - [응답 계약](../../../contracts/ai_image_search/README.md) — `ImageSearchResult`에서 생성되는 백엔드 JSON Schema 계약

<br>

## 🔒 도메인 불변조건

이 디렉터리가 모델 수준에서 보장하는 불변조건입니다. 값의 진위(예: 좌표가 실제 존재하는 장소의 것인지)는 Application·Provider 계층이 책임지고, 여기서는 타입·범위·최소 조건만 강제합니다.

### 의존 방향

```text
search_schemas.py → schemas.py  한 방향만 허용
schemas.py 는 계약 DTO 를 참조하지 않음
```

### 좌표·수치 범위

```text
위도   -90 ≤ latitude ≤ 90     (LandmarkDetection · ResolvedPlace · ImageSearchRequest · PlaceCandidate)
경도   -180 ≤ longitude ≤ 180
score        0 ≤ x ≤ 1         (LandmarkDetection)
confidence   0 ≤ x ≤ 1         (VisionIdentification · PlaceCandidate)
rating       0 ≤ x ≤ 5         (ResolvedPlace · PlaceCandidate, None 허용)
review_count x ≥ 0             (ResolvedPlace, None 허용)
```

### 요청 최소 조건

```text
image_url 또는 image_path 중 최소 하나 필수 (_require_image_source)
문자열 힌트 필드는 값이 있으면 비어 있지 않음 (min_length=1)
max_candidates ≥ 1
```

### 어휘와 출처

```text
category 는 PlaceCategory 폐집합의 값만 허용
source 는 CandidateSource(LANDMARK · LLM · NEARBY) 중 하나
status 는 RecognitionStatus(SUCCESS · PARTIAL · FAILED) 중 하나
```

### 계약 매핑 필드

```text
PlaceCandidate.name / city / country 는 필수 문자열
ResolvedPlace.city / country 는 선택 → 매핑 시 Application 이 채운다
```

> **관련 문서**
>
> - [Services](../services/README.md) — 값의 진위와 상태 판정을 책임지는 실행 계층

<br>

## ⚠️ 현재 모델의 주의사항

### 좌표는 도메인이 아니라 서비스가 확정함

`LandmarkDetection`은 위·경도를 보존하고 `ResolvedPlace`·`PlaceCandidate`도 좌표 필드를 갖지만, 도메인은 범위(`ge`/`le`)만 검증합니다. "식별기 좌표를 폐기하고 Places 좌표로 확정한다"는 불변조건은 도메인 모델이 아니라 `PlaceRecognizer`가 실행합니다. 모델에 좌표 필드가 있다는 이유로 그 좌표가 최종 사실이라고 가정하면 안 됩니다.

### city·country 매핑 갭

`ResolvedPlace.city`·`country`는 선택 필드인데 `PlaceCandidate.city`·`country`는 필수입니다. Places가 두 값을 주지 못하면 후보 조립 시 빈 값을 채워 넣어야 하고, 이 메우기 규칙은 도메인이 아니라 Application 계층에 있습니다.

### 보관만 하는 필드

`ResolvedPlace.review_count`와 `primary_type`은 파싱해 보관만 하며 현재 내부 로직에서 사용하지 않습니다. 코드 주석대로 백엔드 매핑·향후 활용을 위한 필드이므로, 이 값이 인식·추천에 반영된다고 가정하면 부정확합니다.

### RecognitionSignals는 단일 슬롯

`RecognitionSignals`는 `landmark`·`llm` 각각 하나씩만 담습니다. 병렬 앙상블(같은 종류 신호 여러 개)은 아직 반영되지 않았고, 이 모델은 추후 확장을 대비한 로깅용 컨테이너입니다.

### 같은 이름, 다른 Enum

`PlaceCategory`에도 `LANDMARK`가 있고 `CandidateSource`에도 `LANDMARK`가 있습니다. 문자열 값은 같지만 서로 다른 Enum이며 의미가 다릅니다.

```text
PlaceCategory.LANDMARK    사진 피사체의 성격이 "랜드마크·명소"
CandidateSource.LANDMARK  후보가 "랜드마크 식별 경로"에서 나옴
```

두 값을 문자열만 보고 같은 축으로 취급하면 안 됩니다.

### URL·경로 형식은 검증하지 않음

`ImageSearchRequest`는 `image_url`이 실제 URL 형식인지, `image_path`가 안전한 경로인지 검증하지 않고 `min_length=1`만 강제합니다. 스킴·SSRF·경로 탈출 검증은 도메인이 아니라 `services/image_loader.py`의 책임입니다.

### category는 항상 채워져야 함

`VisionIdentification.category`는 필수라서, 비전 LLM은 사진이 애매하더라도 폐집합 중 하나를 반드시 반환해야 합니다. 불확실함은 카테고리 생략이 아니라 `confidence`를 낮추는 방식으로만 표현됩니다.

<br>

## 🔗 관련 문서

| 문서 | 설명 |
|---|---|
| [Image Search](../README.md) | 전체 처리 흐름과 좌표 확정 원칙, 입력·출력 요약 |
| [Providers](../providers/README.md) | Cloud Vision · Gemini · Places 외부 연동과 원신호 생산 |
| [Services](../services/README.md) | 원신호를 조합하는 `PlaceRecognizer`와 이미지 로딩 보안 |
| [Route Planner Domain](../../route_planner/domain/README.md) | 형제 모듈 · 계약 DTO와 도메인 불변조건 |
| [Free Time Recommender Domain](../../free_time_recommender/domain/README.md) | 형제 모듈 · 순수 도메인 객체와 카테고리 모델 |
