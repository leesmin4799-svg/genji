import streamlit as st
from openai import OpenAI
import pandas as pd
import io
import json
import os
import random
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="겐지모노가타리: 모노노아와레 탐구",
    page_icon="🌸",
    layout="wide"
)

# --- 헤이안 시대 고전 풍 커스텀 CSS ---
st.markdown("""
<style>
    .main {
        background-color: #fcfaf2;
    }
    h1, h2, h3 {
        color: #4a355c;
        font-family: 'Noto Serif KR', serif;
    }
    .poem-box {
        background-color: #f4efe6;
        border-left: 5px solid #6b4c7b;
        padding: 18px;
        border-radius: 6px;
        margin-bottom: 15px;
        line-height: 1.7;
    }
    .gallery-card {
        background-color: #fffdf9;
        border: 1px solid #dccaa6;
        border-top: 5px solid #8a649a;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.04);
        margin-bottom: 20px;
    }
    .penname {
        color: #7b588c;
        font-weight: bold;
        font-size: 1.05em;
    }
    .tag-badge {
        background-color: #ece3f0;
        color: #553b66;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.82em;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- OpenAI API Key 연동 (Streamlit Secrets 자동 감지) ---
api_key = (
    st.secrets.get("OPENAI_API_KEY") 
    or st.secrets.get("openai_api_key") 
    or st.secrets.get("API_KEY")
)

if not api_key and "openai" in st.secrets:
    api_key = st.secrets["openai"].get("api_key")

# --- 데이터 저장용 로컬 파일 설정 (필요 시 Supabase 등으로 교체 가능) ---
DATA_FILE = "submissions_data.json"

def load_submissions():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_submissions(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "반갑습니다. 『겐지모노가타리(源氏物語)』를 쓴 무라사키 시키부(紫式部)라 합니다. 풀잎 위의 이슬처럼 덧없이 스러지는 세상 속에서 빛나는 인간의 마음, '모노노아와레(もののあわれ)'에 대해 무엇이든 물어보시지요."
        }
    ]
if "thought_memo" not in st.session_state:
    st.session_state.thought_memo = ""
if "liked_posts" not in st.session_state:
    st.session_state.liked_posts = set()

# --- 헤이안 풍 익명 필명 목록 ---
PENNAMES = [
    "싸리꽃 이슬을 바라보는 이",
    "스마의 가을바람을 듣는 이",
    "달빛 아래 와카를 읊는 이",
    "황매화 옷자락을 스치는 바람",
    "후지쓰보의 그리움을 아는 이",
    "밤바다 파도 소리에 귀 기울이는 이",
    "새벽 닭 울음소리에 잠 못 이루는 이"
]

# --- 무라사키 시키부 시스템 프롬프트 ---
SYSTEM_PROMPT = """
당신은 헤이안 시대의 여류 작가이자 『겐지모노가타리(源氏物語)』의 저자인 '무라사키 시키부(紫式部)'입니다.
학생들과 대화하며 일본 고전 문학의 핵심 미학인 '모노노아와레(もののあわれ)'를 깊이 이해할 수 있도록 이끌어 주세요.

[말투 및 태도]
- 온화하고 우아하며 기품 있는 고전적 경어체("~하옵니다", "~이지요", "~한답니다")를 자연스럽게 사용하세요.
- 정답을 일방적으로 가르치기보다 학생의 생각을 긍정하고 스스로 일상 속의 아와레를 발견하도록 따뜻한 질문을 덧붙이세요.

[작품 속 주요 인용 배경]
1. 기리쓰보(桐壺): 황자를 두고 떠나는 기리쓰보 갱의의 슬픔 ("かぎりとて 別るる道の 悲しきに いかまほしきは 命なりけり")
2. 와카무라사키(若紫): 참새를 놓쳐 우는 어린 와카무라사키와, 그 속에서 사모하는 후지쓰보의 모습을 겹쳐 보며 눈물짓는 히카루 겐지
3. 스마(須磨) & 아카시(明石): 유배지의 쓸쓸한 가을바람, 파도 소리("恋ひわびて 泣く音にまがふ 浦波は 思ふ方より 風や吹くらむ"), 그리고 부원(상황)과 자신의 금지된 사랑에 대한 고뇌
4. 미노리(御法) & 마보로시(幻): 싸리나무 위의 이슬(露)처럼 사라지는 무라사키노우에와의 사별("おくと見る ほどぞはかなき...", "ややもせば 消えをあらそふ 露の世に...", "秋風に しばしとまらぬ 露の世を...", "もの思ふと 過ぐる月日も 知らぬ間に 年もわが世も 今日や尽きぬる")
"""

# --- 상단 헤더 ---
st.title("🌸 『겐지모노가타리(源氏物語)』와 모노노아와레(もののあわれ)")
st.markdown("천 년 전 헤이안 시대의 문장을 통해, 유한한 삶 속에서 피어나는 깊은 정서와 공감을 탐구해 봅니다.")

# --- 탭 구성 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. 원문 감상 및 사유",
    "2. 무라사키 시키부와의 문답",
    "3. 최종 성찰 제출",
    "4. 모노노아와레 갤러리",
    "🔒 교수자(관리자)"
])

# ==========================================
# TAB 1: 원문 감상 및 사유 질문
# ==========================================
with tab1:
    st.subheader("📖 『겐지모노가타리』 핵심 발췌문")
    
    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "기리쓰보 (桐壺)", "와카무라사키 (若紫)", "스마 (須磨)", "미노리·마보로시 (御法·幻)"
    ])
    
    with sub_t1:
        st.markdown("""
        <div class="poem-box">
        <b>[본문]</b><br>
        どの帝の御代であったか、大勢の女御や更衣がお仕えする中に、それほど高い身分ではないのに、とりわけ帝の寵愛を受ける方がいた。…前世からの縁が深かったのか、この世にないほど美しい玉のような皇子までお生まれになった。<br><br>
        <b>[번역]</b><br>
        어느 임금의 치세였던가, 수많은 여어(女御)와 갱의(更衣)가 모시는 가운데, 그리 높은 신분이 아님에도 유별나게 임금의 총애를 한 몸에 받는 이가 있었다. …전생부터의 인연이 깊었던 것인지, 이 세상 사람 같지 않게 아름다운 구슬 같은 황자까지 태어나셨다.
        </div>
        <div class="poem-box">
        <b>[와카(和歌)]</b><br>
        かぎりとて 別るる道の 悲しきに <span style="color:#b83b5e; font-weight:bold;">いかまほしき</span>は 命なりけり<br><br>
        <b>[번역]</b><br>
        이것이 마지막이라며 떠나는 길(죽음의 길)이 이리도 슬픈데, 정작 나아가고 싶은 곳은 생명(삶)의 길이옵니다.
        </div>
        <div class="poem-box">
        <b>[본문]</b><br>
        亡き母君のことは面影さえ覚えていらっしゃらないのに、「（藤壺様は母君に）本当によく似ていらっしゃいます」と典侍が申し上げたので、幼心にとても慕わしくお思いになって、いつもおそばに参りたい、親しくお姿を拝見したいとお思いになる。<br><br>
        <b>[번역]</b><br>
        돌아가신 어머니에 대해서는 그 모습조차 기억하지 못하시는데, '(후지쓰보 님은 어머니를) 정말 많이 닮으셨습니다'라고 나이시노스케(전시)가 아뢰었으므로, 어린 마음에 무척이나 그리운 마음이 드시어, 늘 곁으로 가고 싶고, 가까이서 그 모습을 뵙고 싶다고 생각하시게 된다.
        </div>
        """, unsafe_allow_html=True)

    with sub_t2:
        st.markdown("""
        <div class="poem-box">
        <b>[본문 1]</b><br>
        白い下着に山吹色の着なれた上着を重ねて走って来た女の子は、大勢いた子どもたちとは比べものにならず、成長した姿が思いやられる、たいそうかわいらしい顔立ちである。髪は扇を広げたようにゆらゆらとして、顔は（泣いて）こすってひどく赤くして立っている。…「雀の子を犬君が逃がしちゃったの。伏籠の中に閉じこめておいたのに」と言って、とても悔しそうにしている。<br><br>
        <b>[번역]</b><br>
        흰 속옷(시타기)에 황매화색의 손때 묻은 겉옷을 겹쳐 입고 달려온 여자아이는 여럿 모여 있던 아이들과는 비교도 되지 않으며, 앞으로 자란 모습이 눈에 선할 정도로 몹시 사랑스러운 생김새이다. 머리칼은 부채를 펼친 것처럼 풍성하게 흩날리고, 얼굴은 (울면서) 비벼대어 몹시 붉어진 채 서 있다. …"새끼 참새를 이누키가 놓쳐 버렸어. 후세고(바구니) 속에 가두어 두었는데 말이야"라며, 무척이나 분하고 아쉬워하고 있다.
        </div>
        <div class="poem-box">
        <b>[본문 2]</b><br>
        顔つきがとてもかわいらしく、眉のあたりがほんのりと美しい。子どもらしく髪をかき上げた額の様子や髪の生えぎわが、たいそう愛らしい。成長していく姿を見たい人だなあと、目がとまりなさる。それというのも、限りなく心を尽くしてお慕いしている方にとてもよく似ているので、つい見つめてしまうのだった、と思うにつけても涙がこぼれる。<br><br>
        <b>[번역]</b><br>
        얼굴 생김새가 무척 사랑스럽고, 눈썹 언저리가 은은하게 아름답다. 아이답게 머리를 쓸어 올린 이마의 모습이나 이마의 머리선(발제선)이 무척이나 사랑스럽다. 자라나는 모습을 지켜보고 싶은 사람이구나 하고, 시선이 머무신다. 그도 그럴 것이, 한없이 정성을 다해 사모하는 분과 너무나도 많이 닮았기에, 나도 모르게 빤히 바라보게 되는 것이었다, 라고 생각할 때마다 눈물이 흐른다.
        </div>
        """, unsafe_allow_html=True)

    with sub_t3:
        st.markdown("""
        <div class="poem-box">
        <b>[본문 1]</b><br>
        須磨では、いっそう物思いを誘う秋風が吹き、海は少し離れているが、行平の中納言が「関吹き越ゆる」と詠んだという浦波の音が、夜ごとに本当にすぐ近くに聞こえて、この上なく心にしみるのは、こうした所の秋なのであった。<br><br>
        <b>[번역]</b><br>
        스마에서는 한층 더 수심을 자아내는 가을바람이 불고, 바다는 조금 떨어져 있지만, 유키히라 주나곤(中納言)이 '관문을 불어 넘는'이라고 읊었다는 해변의 파도 소리가 밤마다 정말 바로 근처에서 들려와, 더할 나위 없이 마음에 사무치는 것은 바로 이러한 곳의 가을이었다.
        </div>
        <div class="poem-box">
        <b>[와카(和歌)]</b><br>
        恋ひわびて 泣く音にまがふ 浦波は 思ふ方より 風や吹くらむ<br><br>
        <b>[번역]</b><br>
        그리움에 지쳐 우는 소리와 분간하기 힘든 해변의 파도 소리는, 내가 그리는 임이 계신 곳에서 바람이 불어오기 때문일까.
        </div>
        <div class="poem-box">
        <b>[본문 2]</b><br>
        風の吹く夜の気配は冷ややかで、すぐには寝つくこともおできにならない。そばに仕える女房たちが変に思って聞くのではないかと、身じろぎ一つなさらないのも、やはりとても苦しそうである。夜更けに鶏の声が聞こえてくるのも、しみじみと胸にしみる。<br><br>
        <b>[번역]</b><br>
        바람 부는 밤의 기운은 차가워, 곧바로 잠들지도 못하신다. 곁에서 모시는 시녀들이 이상하게 생각하여 묻지 않을까 하여, 미동조차 하지 않으시는 것도 역시나 무척 괴로워 보이신다. 깊은 밤 닭 울음소리가 들려오는 것도 절절하게 가슴에 사무친다.
        </div>
        <div class="poem-box">
        <b>[본문 3]</b><br>
        亡き父院も、このように心の中ではご存じでいながら、知らないふりをなさっていたのだろうか。思えば、あの頃のことこそ、本当に恐ろしく、あってはならない過ちだった。そう身近な例を思い起こすと、恋の道に迷うことを、とても責めることはできないという気持ちもまじるのだった。<br><br>
        <b>[번역]</b><br>
        돌아가신 부원(상황)께서도 이처럼 마음속으로는 알고 계시면서도 모르는 척하고 계셨던 것일까. 돌이켜보면 그 시절의 일이야말로 정말 두렵고, 있어서는 안 될 잘못이었다. 그렇게 가까운 예를 떠올려보면, 사랑의 길에서 방황하는 것을 마냥 탓할 수만은 없다는 마음도 뒤섞이는 것이었다.
        </div>
        """, unsafe_allow_html=True)

    with sub_t4:
        st.markdown("""
        <div class="poem-box">
        <b>[와카 1 - 무라사키노우에]</b><br>
        おくと見る ほどぞはかなき ともすれば 風に乱るる 萩のうは<span style="color:#b83b5e; font-weight:bold;">露</span><br>
        맺혀 있다고 보는 순간조차 덧없는, 자칫하면 바람에 흩어지는 싸리나무 위의 이슬(처럼 허무한 제 목숨)이옵니다.
        </div>
        <div class="poem-box">
        <b>[와카 2 - 히카루 겐지]</b><br>
        ややもせば 消えをあらそふ <span style="color:#b83b5e; font-weight:bold;">露</span>の世に 後れ先だつ ほど経ずもがな<br>
        자칫하면 (서로 먼저) 스러지려 다투는 이슬 같은 세상에, 앞서거니 뒤서거니 떨어져 있는 시간이 길지 않았으면 좋겠구나.
        </div>
        <div class="poem-box">
        <b>[와카 3 - 아카시 중궁]</b><br>
        秋風に しばしとまらぬ <span style="color:#b83b5e; font-weight:bold;">露</span>の世を たれか草葉の うへとのみ見む<br>
        가을바람에 잠시도 머물지 못하는 이슬 같은 세상에, 그 누가 풀잎 위에만 맺힌 이슬이라 하겠습니까.
        </div>
        <div class="poem-box">
        <b>[와카 4 - 히카루 겐지 (마보로시)]</b><br>
        もの思ふと 過ぐる月日も 知らぬ間に <span style="color:#b83b5e; font-weight:bold;">年もわが世も</span> 今日や尽きぬる<br>
        슬픔에 잠겨 지내느라 흐르는 세월도 모르는 사이에, 올 한 해도 내 목숨도 오늘로 다하는 것인가.
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("💭 생각열기: 모노노아와레 사유 질문")
    st.info("""
    **질문:** 『겐지모노가타리』의 인물들은 참새를 놓친 사소한 순간부터 사랑하는 이와의 영원한 사별까지, 눈앞의 존재가 **'싸리나무 위의 이슬(露)'처럼 언젠가 사라진다는 유한함**을 마주할 때 깊은 탄식(あわれ)을 내뱉습니다.  
    모든 것이 결국 변하고 사라진다는 사실을 알면서도 우리가 무언가를 깊이 사랑하고 그로 인해 아파하는 이유는 무엇일까요? 그 덧없음이 오히려 대상을 더 아름답고 소중하게 만든 순간이 있었나요?
    """)
    st.session_state.thought_memo = st.text_area(
        "질문에 대한 자신의 첫인상이나 짧은 생각을 메모해 보세요 (2단계 문답과 3단계 작성에 활용됩니다).",
        value=st.session_state.thought_memo,
        height=100,
        placeholder="예: 벚꽃이 일주일 만에 지기 때문에 더 애틋하게 바라보게 되는 것처럼..."
    )

# ==========================================
# TAB 2: 무라사키 시키부(ChatGPT)와의 문답
# ==========================================
with tab2:
    st.subheader("🪭 작가 무라사키 시키부(紫式部)와의 대화")
    st.caption("원문 속 구절의 의미나 인물의 심리, 혹은 여러분이 생각하는 '모노노아와레'에 대해 작가에게 직접 질문해 보세요.")

    if not api_key:
        st.warning("⚠️ Streamlit Secrets에 `OPENAI_API_KEY`가 설정되어 있지 않습니다. `.streamlit/secrets.toml` 또는 Streamlit Cloud의 Secrets 설정을 확인해 주세요.")

    # 추천 질문 버튼
    st.markdown("**💡 추천 질문으로 대화 시작하기:**")
    q_cols = st.columns(2)
    sample_questions = [
        "와카무라사키에서 참새를 놓친 어린 소녀를 보고 겐지는 왜 눈물을 흘렸나요?",
        "스마의 가을바람과 파도 소리는 겐지의 외로움과 어떻게 연결되나요?",
        "왜 삶과 죽음을 '싸리나무 위의 이슬(露)'에 비유하셨나요?",
        "'모노노아와레'는 단순한 슬픔과 어떻게 다른 감정인가요?"
    ]
    
    triggered_question = None
    for idx, q_text in enumerate(sample_questions):
        with q_cols[idx % 2]:
            if st.button(q_text, key=f"sample_q_{idx}", use_container_width=True):
                triggered_question = q_text

    # 대화 기록 출력
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.messages:
            avatar = "👘" if msg["role"] == "assistant" else "🧑‍🎓"
            with st.chat_message(msg["role"], avatar=avatar):
                st.write(msg["content"])

    # 사용자 입력 처리
    user_input = st.chat_input("무라사키 시키부에게 질문을 입력하세요...")
    prompt_to_send = triggered_question or user_input

    if prompt_to_send:
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})
        with chat_container:
            with st.chat_message("user", avatar="🧑‍🎓"):
                st.write(prompt_to_send)

            with st.chat_message("assistant", avatar="👘"):
                if not api_key:
                    err_msg = "API 키가 연결되지 않아 답변을 드릴 수 없사옵니다. 교수님께 Secrets 설정을 문의해 주시지요."
                    st.error(err_msg)
                else:
                    try:
                        client = OpenAI(api_key=api_key)
                        stream = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                *st.session_state.messages
                            ],
                            stream=True,
                            temperature=0.7
                        )
                        response_text = st.write_stream(stream)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    except Exception as e:
                        st.error(f"호출 중 오류가 발생했습니다: {e}")
        st.rerun()

# ==========================================
# TAB 3: 최종 답변 제출
# ==========================================
with tab3:
    st.subheader("✍️ 내가 느낀 ‘모노노아와레’의 순간 제출하기")
    st.markdown("1단계의 원문 사유와 2단계 무라사키 시키부와의 대화를 바탕으로, **여러분 자신의 삶에서 ‘모노노아와레’를 느꼈던 순간**을 작성해 제출해 주세요.")

    with st.form("submission_form", clear_on_submit