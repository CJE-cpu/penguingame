import { useEffect, useMemo, useRef, useState } from "react";
import { Search, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeading, EmptyState } from "../components";
import { collection } from "../data";

export default function Collection() {
  const [category, setCategory] = useState("전체");
  const [query, setQuery] = useState("");
  const search = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const focus = (event: KeyboardEvent) => {
      if (
        event.key === "/" &&
        !(event.target instanceof HTMLInputElement) &&
        !(event.target instanceof HTMLTextAreaElement)
      ) {
        event.preventDefault();
        search.current?.focus();
      }
    };
    window.addEventListener("keydown", focus);
    return () => window.removeEventListener("keydown", focus);
  }, []);
  const entries = useMemo(
    () =>
      collection.filter(
        (item) =>
          (category === "전체" || item.category === category) &&
          (item.name + item.description).includes(query.trim()),
      ),
    [category, query],
  );
  return (
    <main className="section-shell page-main">
      <PageHeading
        eyebrow="THE EXPEDITION FIELD GUIDE"
        title="만날 것들, 알아둘 것들."
        description="작은 물고기부터 낯선 친구까지. 모험을 조금 더 즐겁게 만드는 탐험 도감."
      />
      <div className="collection-toolbar">
        <div className="segmented" role="group" aria-label="도감 분류">
          {["전체", "물고기", "아이템", "친구와 적"].map((name) => (
            <button
              key={name}
              className={category === name ? "active" : ""}
              onClick={() => setCategory(name)}
              aria-pressed={category === name}
            >
              {name}
            </button>
          ))}
        </div>
        <label className="search-input">
          <Search size={17} />
          <input
            ref={search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="이름이나 특징 검색"
            aria-label="도감 검색"
          />
          <kbd>/</kbd>
        </label>
      </div>
      <div className="collection-count">
        총 <strong>{entries.length}</strong>개의 발견
      </div>
      <div className="collection-grid">
        {entries.map((item, i) => (
          <article className="collection-card" key={item.name}>
            <div
              className={`collection-art category-${item.category === "물고기" ? "fish" : item.category === "아이템" ? "item" : "friend"}`}
            >
              <span className="collection-index">
                FIELD NOTE {String(i + 1).padStart(2, "0")}
              </span>
              <img
                src={`/assets/${item.image}`}
                alt={item.name}
                loading="lazy"
              />
              <span className="collection-category">{item.category}</span>
            </div>
            <div className="collection-body">
              <h2>{item.name}</h2>
              <span className="collection-value">{item.value}</span>
              <p>{item.description}</p>
            </div>
          </article>
        ))}
      </div>
      {entries.length === 0 && (
        <EmptyState title="아직 발견하지 못했어요.">
          <p>다른 이름이나 분류로 검색해 보세요.</p>
          <button
            className="button button-outline"
            onClick={() => {
              setQuery("");
              setCategory("전체");
            }}
          >
            검색 초기화
          </button>
        </EmptyState>
      )}
      <div className="page-bottom-note">
        <p>이제 모험의 친구들을 만날 준비가 되었나요?</p>
        <Link to="/explore" className="text-link">
          탐험 지도 열기 <ArrowUpRight size={17} />
        </Link>
      </div>
    </main>
  );
}
