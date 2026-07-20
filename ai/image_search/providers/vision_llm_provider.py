# Google Gemini(멀티모달 LLM)로 사진을 이해해 장소를 추정하는 Provider
# 캐스케이드의 2차 식별기: 랜드마크가 못 잡는 일반 장소(카페·골목·음식)와 분위기에 강하다.
from google import genai
from google.genai import types

from ai.image_search.domain.schemas import VisionIdentification
from ai.image_search.providers.env import get_gemini_api_key


# Gemini 에게 보내는 지시. 구조화 출력(JSON 스키마)이 형식을 강제하므로 여기선 '무엇을' 판단할지만 지시한다.
# 프롬프트 강화: 환각 억제(근거 없으면 지어내지 말 것)·confidence 캘리브레이션·카테고리 경계 기준 중심.
_INSTRUCTION = """너는 여행 사진에서 장소를 추정하는 전문가다. 이 단계는 2차 식별기다 — 유명 랜드마크는 앞 단계가 이미 처리했고, 너에게는 카페·골목·음식·간판처럼 이름이 겉으로 드러나지 않는 사진이 주로 온다. 그러니 유명 명소로 성급히 단정하지 말고, 사진 속 실제 단서(간판·글자, 건축·구조물, 음식·식기, 자연 요소, 조명·시간대)로 판단하라.

핵심 원칙: 확실한 시각적 근거가 없으면 장소명을 지어내지 마라. 실제 좌표는 다음 단계(장소 검색)가 확정하므로 위치를 맞히려 애쓸 필요가 전혀 없다. 장소를 특정 못 해도 괜찮으니, 억지로 이름을 붙이기보다 모르면 null로 두어라.

각 필드는 아래 기준으로 판단하라.
- visible_text: 장소를 특정하는 가장 강한 단서다. 이걸 먼저 읽어라. 사진 속 간판·상호·메뉴·안내판의 글자를 보이는 그대로(일본어는 일본어로) 옮겨라 — 번역·수정·추측 금지, 흐릿해도 최대한 읽는다. 글자가 없으면 빈 배열.
- place_name_guess: 이 값은 그대로 지도 검색어가 되므로, 근거 없이 지어내면 엉뚱한 좌표로 이어진다. visible_text의 상호나 명확히 식별되는 상징물처럼 실제 근거가 있을 때만 그 이름을 써라. 확인되지 않은 지점명·지역명·유명 체인을 임의로 갖다 붙이지 말고, 조금이라도 불확실하면 null로 둔다.
- category: 사진의 '주 피사체' 하나를 기준으로 목록에서 딱 하나만 골라라(근처 추천의 필터가 되니 정확해야 한다). 애매하다고 ETC로 도피하지 말고 가장 가까운 것을 고른 뒤 불확실함은 confidence로 낮춰 표현하라. 자주 헷갈리는 경계:
  · CAFE vs DESSERT: 음료·머무는 공간이 중심이면 CAFE, 케이크·빵이 주인공이면 DESSERT.
  · RESTAURANT vs BAR: 식사가 중심이면 RESTAURANT, 술·안주·이자카야 분위기면 BAR.
  · TEMPLE_SHRINE vs HISTORIC: 도리이·본당·불상 등 참배 공간이면 TEMPLE_SHRINE, 성·유적·옛 거리면 HISTORIC.
  · VIEWPOINT vs NIGHTVIEW: 낮의 조망·전망대면 VIEWPOINT, 밤 불빛 경관이 주 피사체면 NIGHTVIEW.
  · STREET vs SHOPPING vs MARKET: 걷는 거리·골목 풍경이면 STREET, 개별 상점·상점가면 SHOPPING, 먹거리 좌판이 늘어선 시장이면 MARKET.
  · NATURE vs PARK vs GARDEN: 손대지 않은 산·숲·바다면 NATURE, 도심 공원이면 PARK, 조경된 정원이면 GARDEN.
- vibe_keywords: 사진의 분위기를 구체적인 한국어 단어 2~4개로 뽑아라(예: "레트로", "우드톤", "네온", "한적함", "노포"). "좋다"·"예쁘다"처럼 막연한 말은 피하라.
- reason: 무엇을 보고 그렇게 판단했는지(특히 결정적 단서가 무엇이었는지) 한 문장으로.
- confidence: 실제 확신도를 정직하게 매겨라. 대략 — 0.9 이상: 간판·형태로 장소가 분명함 / 0.6~0.8: 근거는 있으나 확실치 않음 / 0.4~0.6: 카테고리는 확실하나 특정 장소는 불명(이때 place_name_guess는 보통 null) / 0.2 이하: 거의 추측. place_name_guess가 null이면 낮은 값이어야 한다."""


# Gemini 를 감싸 사진 -> VisionIdentification 으로 변환하는 Provider
class VisionLlmProvider:
    # 비전 지원 저비용 모델. 실제 응답 검증(step 7 CLI)에서 조정 가능.
    DEFAULT_MODEL = "gemini-2.5-flash"

    # api_key: Gemini API 키 (없으면 환경변수에서 가져옴)
    # model: 사용할 Gemini 모델명
    # client: google-genai Client 주입용 (테스트에서 가짜 client, 실제 사용 시 None)
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.model = model or self.DEFAULT_MODEL
        self._client = client or genai.Client(api_key=api_key or get_gemini_api_key())

    # 사진 바이트를 받아 장소를 추정한다.
    # image_bytes: 이미지 내용 (URL/경로 -> 바이트 변환은 호출자(recognizer)가 담당)
    # mime_type: 이미지 MIME 타입
    # note: 사용자 메모 (예: "야경") — 프롬프트에 힌트로 추가
    # 반환: VisionIdentification (LLM 출력을 pydantic 으로 재검증)
    def identify(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        note: str | None = None,
    ) -> VisionIdentification:
        prompt = self._build_prompt(note)
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        response = self._client.models.generate_content(
            model=self.model,
            contents=[prompt, image_part],
            # 구조화 출력: 자유 텍스트가 아닌, 스키마에 맞는 JSON 만 받는다
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VisionIdentification,
            ),
        )

        # LLM 출력을 그대로 믿지 않고 pydantic 으로 재검증 (범위·카테고리 폐집합 강제)
        return VisionIdentification.model_validate_json(response.text)

    # 지시문에 사용자 메모를 힌트로 덧붙인다
    @staticmethod
    def _build_prompt(note: str | None) -> str:
        if note:
            return f"{_INSTRUCTION}\n\n참고 - 사용자 메모: {note}"
        return _INSTRUCTION
