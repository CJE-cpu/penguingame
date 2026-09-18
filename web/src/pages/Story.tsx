import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Check,
  Code2,
  Compass,
  Heart,
  MoveRight,
} from "lucide-react";
import { PageHeading } from "../components";

const chapters = [
  {
    number: "01",
    title: "발끝을 기준으로, 자연스러운 움직임.",
    before: "프레임마다 펭귄 크기가 달라 보이고 걷는 속도가 지나치게 빨랐어요.",
    after:
      "공통 비율과 발끝 기준으로 스프라이트를 정렬하고, 이동 속도에 맞춘 8프레임 걷기를 적용했습니다.",
    image: "preview-coast.png",
  },
  {
    number: "02",
    title: "같은 눈밭에, 서로 다른 모험을.",
    before: "맵 구조가 단순하고 사건이 연달아 일어나 탐험할 여유가 부족했어요.",
    after:
      "맵을 10,800픽셀로 확장하고, 관성·바람·붕괴 발판·잠수·동굴 퍼즐로 지역별 경험을 나눴습니다.",
    image: "preview-cave.png",
  },
  {
    number: "03",
    title: "기록이 남으면, 모험도 이어집니다.",
    before: "게임을 종료하면 점수와 플레이어 기록을 다시 확인하기 어려웠어요.",
    after:
      "로컬 이름별 기록을 추가하고, 웹에서는 로그인한 계정에 기록을 가져와 추이와 순위를 확인할 수 있게 만들었습니다.",
    image: "preview-ocean.png",
  },
];
export default function Story() {
  return (
    <main className="section-shell page-main story-page">
      <PageHeading
        eyebrow="BEHIND THE LITTLE ADVENTURE"
        title="작은 게임이, 하나의 경험으로."
        description="한 번의 수정이 다음 모험을 바꿉니다. 펭귄의 모험을 만들며 해결한 문제들."
      />
      <div className="story-intro">
        <Code2 size={28} />
        <div>
          <h2>플레이 경험을 웹으로 연결하기.</h2>
          <p>
            Pygame 게임의 이미지와 탐험 세계를 React·TypeScript로 확장했습니다.
            반응형 화면, 인터랙티브 지도와 도감, 계정 인증, 점수 차트와 기록
            업로드가 하나의 흐름으로 이어집니다.
          </p>
        </div>
        <a
          href="https://github.com/CJE-cpu/penguingame/tree/main/web"
          target="_blank"
          rel="noreferrer"
          className="text-link"
        >
          소스 코드 <ArrowUpRight size={18} />
        </a>
      </div>
      <div className="story-chapters">
        {chapters.map((chapter) => (
          <article key={chapter.number} className="story-chapter">
            <div className="chapter-image">
              <img
                src={`/assets/${chapter.image}`}
                alt={chapter.title}
                loading="lazy"
              />
            </div>
            <div className="chapter-body">
              <span className="eyebrow">CHAPTER {chapter.number}</span>
              <h2>{chapter.title}</h2>
              <div className="chapter-problem">
                <span>발견한 문제</span>
                <p>{chapter.before}</p>
              </div>
              <div className="chapter-solution">
                <span>
                  <Check size={14} />
                  개선한 경험
                </span>
                <p>{chapter.after}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
      <div className="story-principles">
        <div>
          <Compass size={25} />
          <h3>탐험할 수 있는 인터페이스</h3>
          <p>
            지대 선택은 URL에 남고, 도감은 분류와 검색으로 좁혀볼 수 있습니다.
          </p>
        </div>
        <div>
          <Heart size={25} />
          <h3>데이터를 정직하게 보여주기</h3>
          <p>
            데모와 실제 기록을 구분하고, 데이터가 없거나 실패했을 때도 다음
            행동을 안내합니다.
          </p>
        </div>
        <div>
          <Code2 size={25} />
          <h3>작동하는 기능으로 완성하기</h3>
          <p>
            계정과 점수는 SQLite에 저장하고, HttpOnly 세션과 비밀번호 해시로
            인증을 처리합니다.
          </p>
        </div>
      </div>
      <Link to="/dashboard" className="button button-dark">
        기록 대시보드 체험하기 <MoveRight size={18} />
      </Link>
    </main>
  );
}
