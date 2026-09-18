import { useSearchParams, Link } from "react-router-dom";
import {
  ArrowRight,
  Compass,
  Flag,
  MapPin,
  Mountain,
  Shield,
} from "lucide-react";
import { PageHeading } from "../components";
import { worlds } from "../data";

export default function Explore() {
  const [params, setParams] = useSearchParams();
  const parsed = Number(params.get("region") || 0);
  const selected =
    Number.isInteger(parsed) && parsed >= 0 && parsed < worlds.length
      ? parsed
      : 0;
  const world = worlds[selected];
  return (
    <main className="section-shell page-main">
      <PageHeading
        eyebrow="YOUR NEXT DESTINATION"
        title="여섯 지대, 하나의 모험."
        description="지도 위의 지점을 선택해, 다음 탐험의 힌트를 찾아보세요."
      />
      <div className="map-layout">
        <div className="expedition-map">
          <div className="map-top">
            <Compass size={20} />
            <span>ANTARCTICA FIELD MAP</span>
            <small>90° S</small>
          </div>
          <div className="map-island">
            <svg
              viewBox="0 0 600 460"
              role="img"
              aria-label="여섯 남극 지대의 탐험 경로"
            >
              <path
                className="island-shadow"
                d="M90 110L170 48 300 72 370 40 482 106 540 232 485 350 365 420 220 396 135 333 68 210Z"
              />
              <path
                className="island"
                d="M84 99L164 37 294 61 364 29 476 95 534 221 479 339 359 409 214 385 129 322 62 199Z"
              />
              <path
                className="map-route"
                d="M135 290C125 215 170 145 235 139S350 75 388 158 480 206 429 286 345 366 295 302"
              />
              <path
                className="map-mountain"
                d="M234 225L267 171 300 225 280 215 267 190 254 215Z M340 300L373 246 406 300 386 290 373 265 360 290Z"
              />
              <text x="176" y="345" className="map-label">
                SOUTH POLE
              </text>
            </svg>
            {worlds.map((region, i) => (
              <button
                key={region.name}
                onClick={() => setParams({ region: String(i) })}
                className={`map-pin pin-${i} ${i === selected ? "selected" : ""}`}
                aria-label={`${i + 1}. ${region.name}`}
                aria-pressed={selected === i}
              >
                <span>0{i + 1}</span>
                <small>{region.name}</small>
              </button>
            ))}
          </div>
          <div className="map-legend">
            <span>
              <i /> 현재 탐험 지점
            </span>
            <span>
              <i /> 다음 목적지
            </span>
            <small>전체 길이 10,800 px</small>
          </div>
        </div>
        <article className="destination-card" key={selected}>
          <div className="destination-image">
            <img src={`/assets/${world.image}`} alt={world.name} />
            <span>REGION 0{selected + 1}</span>
          </div>
          <div className="destination-body">
            <span className="eyebrow">{world.en}</span>
            <h2>{world.name}</h2>
            <p>{world.description}</p>
            <dl className="destination-facts">
              <div>
                <dt>
                  <Mountain size={16} /> 지형
                </dt>
                <dd>{world.terrain}</dd>
              </div>
              <div>
                <dt>
                  <Shield size={16} /> 만나는 적
                </dt>
                <dd>{world.enemy}</dd>
              </div>
              <div>
                <dt>
                  <Flag size={16} /> 탐험 목표
                </dt>
                <dd>{world.mission}</dd>
              </div>
            </dl>
          </div>
        </article>
      </div>
      <div className="region-tabs" role="group" aria-label="지대 선택">
        {worlds.map((region, i) => (
          <button
            key={region.name}
            onClick={() => setParams({ region: String(i) })}
            className={selected === i ? "active" : ""}
          >
            <span>0{i + 1}</span>
            {region.name}
            <MapPin size={15} />
          </button>
        ))}
      </div>
      <div className="page-bottom-note">
        <Compass size={20} />
        <p>
          길을 돌아와도 괜찮아요. 수집 기록과 구조한 친구들은 모험을 이어갑니다.
        </p>
        <Link to="/collection" className="text-link">
          준비물 살펴보기 <ArrowRight size={17} />
        </Link>
      </div>
    </main>
  );
}
