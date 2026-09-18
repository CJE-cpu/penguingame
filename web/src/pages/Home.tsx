import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Download,
  Fish,
  Flag,
  Heart,
  MapPin,
  Play,
  Sparkles,
  Trophy,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Sprite, Modal } from "../components";
import { api, formatNumber } from "../api";
import { worlds } from "../data";
import type { Rank } from "../types";

const screenshots = [
  {
    file: "preview-coast.png",
    title: "햇빛 가득한 눈 덮인 해안",
    description: "발판을 건너며 물고기를 찾고, 친구의 위치를 확인하세요.",
  },
  {
    file: "preview-ocean.png",
    title: "얼음 아래의 푸른 바다",
    description: "산소를 확인하며 헤엄쳐 보너스 물고기를 모으세요.",
  },
  {
    file: "preview-cave.png",
    title: "봉인된 동굴의 비밀",
    description: "낮은 통로와 무너지는 다리 너머, 봉인석과 보물이 기다립니다.",
  },
];
export default function Home() {
  const [preview, setPreview] = useState<number | null>(null);
  const [ranks, setRanks] = useState<Rank[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    api<{ leaderboard: Rank[] }>("/demo", { signal: controller.signal })
      .then((data) => setRanks(data.leaderboard.slice(0, 3)))
      .catch(() => {});
    return () => controller.abort();
  }, []);
  return (
    <>
      <main>
        <section className="hero section-shell">
          <div className="hero-copy">
            <span className="eyebrow">
              <span />
              ANTARCTIC EXPEDITION · NO. 001
            </span>
            <h1>
              작은 발로,
              <br />
              <span className="hero-underline">커다란 모험.</span>
            </h1>
            <p>
              물고기를 찾아, 친구를 만나, 집으로 돌아가는 길.
              <br />
              우리의 작은 펭귄과 함께 남극을 탐험해요.
            </p>
            <div className="hero-actions">
              <a href="/api/download" className="button button-dark">
                모험 다운로드 <Download size={18} />
              </a>
              <button
                className="button button-outline"
                onClick={() => setPreview(0)}
              >
                <Play size={16} /> 게임 둘러보기
              </button>
            </div>
            <div className="hero-note">
              <span className="status-dot" /> Windows 데스크톱 게임{" "}
              <span>·</span> 무료로 시작하는 모험
            </div>
          </div>
          <div className="hero-art">
            <span className="hero-sun" />
            <div className="hero-scene">
              <div className="scene-label">
                <MapPin size={14} /> SOUTH POLE, ANTARCTICA
              </div>
              <Sprite className="hero-penguin" />
              <img
                className="hero-baby"
                src="/assets/baby.png"
                alt="작은 아기 펭귄"
              />
              <img
                className="hero-fish fish-one"
                src="/assets/gold-fish.png"
                alt=""
              />
              <img
                className="hero-fish fish-two"
                src="/assets/blue-fish.png"
                alt=""
              />
              <div className="hero-goal">
                <span className="goal-icon">
                  <Flag size={19} />
                </span>
                <div>
                  <strong>혼자 떠나, 함께 돌아와요.</strong>
                  <span>물고기 30마리 · 친구 3마리 · 하나의 모험</span>
                </div>
              </div>
            </div>
            <div className="hero-stamp">
              LITTLE FEET
              <br />
              <span>
                BIG
                <br />
                ADVENTURES
              </span>
              <SnowStamp />
            </div>
          </div>
        </section>
        <section className="journey-strip">
          <div className="section-shell journey-inner">
            <span className="strip-intro">모험의 한 페이지</span>
            <div>
              <strong>06</strong>
              <span>서로 다른 남극 지대</span>
            </div>
            <div>
              <strong>30</strong>
              <span>찾아야 할 물고기</span>
            </div>
            <div>
              <strong>03</strong>
              <span>함께 돌아올 친구</span>
            </div>
            <div>
              <strong>∞</strong>
              <span>당신만의 탐험 기록</span>
            </div>
          </div>
        </section>
        <section className="section-shell home-worlds">
          <div className="section-title">
            <div>
              <span className="eyebrow">
                <span />A WORLD WORTH EXPLORING
              </span>
              <h2>다음 발걸음은 어디로?</h2>
              <p>같은 눈밭은 없어요. 여섯 지대, 여섯 가지 모험.</p>
            </div>
            <Link to="/explore" className="text-link">
              전체 지도 살펴보기 <ArrowUpRight size={18} />
            </Link>
          </div>
          <div className="world-preview-grid">
            {[0, 2, 5].map((index) => (
              <Link
                className="world-preview"
                to={`/explore?region=${index}`}
                key={index}
              >
                <div className="world-preview-image">
                  <img
                    src={`/assets/${worlds[index].image}`}
                    alt={worlds[index].name}
                    loading="lazy"
                  />
                  <span className="world-number">0{index + 1}</span>
                  <span className="world-arrow">
                    <ArrowUpRight size={22} />
                  </span>
                </div>
                <div className="world-preview-text">
                  <span>{worlds[index].en}</span>
                  <h3>{worlds[index].name}</h3>
                  <p>{worlds[index].tag}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
        <section className="section-shell home-features">
          <div className="feature-story">
            <div className="feature-scene">
              <img
                src="/assets/ocean-panorama-v2.png"
                alt="남극의 푸른 바닷속"
                loading="lazy"
              />
              <span className="scene-chip">
                <Fish size={16} /> BELOW THE ICE
              </span>
            </div>
            <div className="feature-description">
              <span className="eyebrow">
                <span />
                MORE THAN A FISH HUNT
              </span>
              <h2>
                물고기 너머에도,
                <br />
                이야기가 있어요.
              </h2>
              <p>
                얼음 아래를 헤엄치고, 동굴의 봉인을 풀고,
                <br />
                길을 잃은 친구와 나란히 걸어요.
              </p>
              <div className="feature-list">
                <span>
                  <Fish size={17} /> 35초의 잠수 탐험
                </span>
                <span>
                  <Sparkles size={17} /> 두 곳의 보물 동굴
                </span>
                <span>
                  <Heart size={17} /> 세 친구의 구조 이야기
                </span>
              </div>
              <Link to="/collection" className="text-link">
                탐험 도감 열어보기 <ArrowRight size={17} />
              </Link>
            </div>
          </div>
        </section>
        <section className="section-shell home-records">
          <div className="record-invitation">
            <span className="eyebrow">
              <span />
              EVERY ADVENTURE COUNTS
            </span>
            <h2>
              당신의 모험을
              <br />
              기록해 주세요.
            </h2>
            <p>
              오늘의 점수, 어제보다 멀어진 발걸음.
              <br />
              로그인하고 나만의 탐험 대시보드를 만들어 보세요.
            </p>
            <Link to="/dashboard" className="button button-dark">
              점수 대시보드 <ArrowUpRight size={18} />
            </Link>
          </div>
          <div className="rank-preview">
            <div className="rank-preview-head">
              <Trophy size={20} />
              <strong>탐험가 명예의 전당</strong>
              <span className="sample-pill">예시 기록</span>
            </div>
            {ranks.map((rank) => (
              <div className="rank-preview-row" key={rank.rank}>
                <span className={`rank-medal medal-${rank.rank}`}>
                  {String(rank.rank).padStart(2, "0")}
                </span>
                <span className="rank-avatar">{rank.nickname.slice(0, 1)}</span>
                <span>{rank.nickname}</span>
                <strong>
                  {formatNumber(rank.score)} <small>점</small>
                </strong>
              </div>
            ))}
            <div className="rank-preview-foot">
              로그인하면 실제 기록을 등록하고 순위를 확인할 수 있어요.{" "}
              <Link to="/login">
                <ArrowRight size={18} aria-label="로그인하기" />
              </Link>
            </div>
          </div>
        </section>
        <section className="club-cta">
          <span>90° S. A NEW STORY STARTS HERE.</span>
          <h2>남극에서 만나요.</h2>
          <Link to="/login?mode=register" className="button button-yellow">
            탐험 클럽 가입하기 <ArrowUpRight size={18} />
          </Link>
          <img src="/assets/penguin.png" alt="" />
        </section>
      </main>
      {preview !== null && (
        <Modal
          title="모험 미리보기"
          onClose={() => setPreview(null)}
          className="preview-modal"
        >
          <img
            className="game-preview"
            src={`/assets/${screenshots[preview].file}`}
            alt={screenshots[preview].title}
          />
          <div className="preview-description">
            <div>
              <span className="eyebrow">0{preview + 1} / 03</span>
              <h3>{screenshots[preview].title}</h3>
              <p>{screenshots[preview].description}</p>
            </div>
            <div className="preview-controls">
              <button
                className="icon-button"
                onClick={() => setPreview((preview + 2) % 3)}
                aria-label="이전 화면"
              >
                <ChevronLeft />
              </button>
              <button
                className="icon-button"
                onClick={() => setPreview((preview + 1) % 3)}
                aria-label="다음 화면"
              >
                <ChevronRight />
              </button>
            </div>
          </div>
          <a href="/api/download" className="button button-dark">
            게임 다운로드 <Download size={17} />
          </a>
        </Modal>
      )}
    </>
  );
}
function SnowStamp() {
  return <span className="stamp-star">✳</span>;
}
