import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  Fish,
  Flag,
  Heart,
  Info,
  RefreshCw,
  Trophy,
} from "lucide-react";
import { useAuth } from "../auth";
import { api, ApiError, errorMessage, formatDate, formatNumber } from "../api";
import { EmptyState, LoadingState, PageHeading } from "../components";
import type { DashboardData } from "../types";

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}분 ${String(rest).padStart(2, "0")}초`;
};

const emptyDashboard: DashboardData = {
  demo: false,
  summary: { best: 0, average: 0, games: 0, clears: 0, rank: null },
  records: [],
  trend: [],
  leaderboard: [],
};

export default function Dashboard() {
  const { user, loading: authLoading, refresh } = useAuth();
  const [range, setRange] = useState("all");
  const [tab, setTab] = useState("records");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!user) return;
    const refreshScores = (event?: Event) => {
      if (event instanceof StorageEvent && event.key !== "penguin-score-updated") return;
      setRevision((value) => value + 1);
    };
    window.addEventListener("penguin-score-updated", refreshScores);
    window.addEventListener("storage", refreshScores);
    window.addEventListener("focus", refreshScores);
    return () => {
      window.removeEventListener("penguin-score-updated", refreshScores);
      window.removeEventListener("storage", refreshScores);
      window.removeEventListener("focus", refreshScores);
    };
  }, [user]);
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setData(emptyDashboard);
      setLoading(false);
      setError("");
      setPage(0);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setPage(0);
    api<DashboardData>(`/dashboard?range=${range}`, {
      signal: controller.signal,
    })
      .then((result) => {
        setData(result);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(errorMessage(err));
        if (err instanceof ApiError && err.status === 401) void refresh();
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [user, range, revision, authLoading, refresh]);
  const trend = useMemo(
    () =>
      data?.trend.map((row, i) => ({
        ...row,
        label: formatDate(row.date),
        chartIndex: i + 1,
      })) || [],
    [data],
  );
  const latest = data?.records[0];
  const exportRecords = () => {
    if (!data) return;
    const lines = [
      "date,score,fish,rescued,seconds,cleared",
      ...data.records.map((row) =>
        [
          row.date,
          row.score,
          row.fish,
          row.rescued,
          row.seconds,
          row.cleared,
        ].join(","),
      ),
    ];
    const url = URL.createObjectURL(
      new Blob(["\uFEFF" + lines.join("\r\n")], {
        type: "text/csv;charset=utf-8",
      }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "penguin-my-records.csv";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <main className="section-shell page-main dashboard-page">
      <PageHeading
        eyebrow="YOUR EXPEDITION LOG"
        title="모험을 숫자로."
        description={
          user
            ? user.nickname + "님의 실제 탐험 기록입니다. 게임을 마치면 점수가 자동으로 갱신됩니다."
            : "로그인하면 게임에서 달성한 실제 점수와 순위를 확인할 수 있습니다."
        }
      >
        <Link className="button button-dark" to={user ? "/play" : "/login"}>
          {user ? "게임 시작하기" : "로그인하기"} <ArrowUpRight size={17} />
        </Link>
      </PageHeading>
      <div className="dashboard-banner">
        <span>
          <Info size={17} />
          <strong>{user ? "나의 실제 기록" : "기록이 비어 있습니다"}</strong>
          <span>
            {user
              ? "게임에서 완료한 기록만 계정에 자동 저장됩니다."
              : "예시 데이터는 표시하지 않습니다. 로그인 후 게임을 시작해 주세요."}
          </span>
        </span>
        {!user && (
          <Link className="text-link" to="/login">
            로그인하기 <ArrowUpRight size={15} />
          </Link>
        )}
      </div>
      <div className="dashboard-toolbar">
        <div className="dashboard-owner">
          <span className="avatar avatar-large">
            {user ? user.nickname.slice(0, 1) : "—"}
          </span>
          <div>
            <strong>{user ? user.nickname + "님의 대시보드" : "저장된 기록 없음"}</strong>
            <span>{user ? "MY EXPEDITION RECORDS" : "SIGN IN TO START"}</span>
          </div>
        </div>
        <div className="segmented compact" role="group" aria-label="조회 기간">
          {[
            ["all", "전체"],
            ["week", "최근 7일"],
            ["month", "최근 30일"],
          ].map(([value, label]) => (
            <button
              className={range === value ? "active" : ""}
              key={value}
              onClick={() => setRange(value)}
              aria-pressed={range === value}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {(loading || authLoading) && <LoadingState />}
      {!loading && !authLoading && error && (
        <div className="error-state" role="alert">
          <p>{error}</p>
          <button
            className="button button-outline"
            onClick={() => setRevision((value) => value + 1)}
          >
            <RefreshCw size={16} />
            다시 불러오기
          </button>
        </div>
      )}
      {!loading && !authLoading && !error && data && (
        <>
          <section className="score-overview" aria-label="점수 요약" aria-live="polite">
            <div className="score-overview-heading">
              <div>
                <span className="eyebrow">SCORE SNAPSHOT</span>
                <h2>내 탐험 점수</h2>
              </div>
              <span className="score-sync-state">
                <span className="status-dot" />
                {user ? "게임 종료 후 자동 저장" : "로그인 후 기록 표시"}
              </span>
            </div>
            <div className="score-overview-grid">
              <article className="latest-score-card">
                <span className="score-card-label">
                  <Trophy size={18} />
                  최근 플레이 점수
                </span>
                <strong>
                  {latest ? formatNumber(latest.score) : "0"}
                  <small>점</small>
                </strong>
                {latest ? (
                  <>
                    <div className="latest-score-meta">
                      <span><Fish size={14} /> 물고기 {latest.fish}/30</span>
                      <span><Heart size={14} /> 동료 {latest.rescued}/3</span>
                      <span><Flag size={14} /> {formatDuration(latest.seconds)}</span>
                    </div>
                    <span className={"latest-result " + (latest.cleared ? "is-cleared" : "")}>
                      {latest.cleared ? "탐험 완료" : "게임오버"}
                      <small>{formatDate(latest.date)} 자동 저장</small>
                    </span>
                  </>
                ) : (
                  <p>게임을 완료하면 점수가 자동으로 표시됩니다.</p>
                )}
              </article>
              <article className="score-metric-card">
                <span>최고 점수 <Trophy size={17} /></span>
                <strong>{formatNumber(data.summary.best)}<small>점</small></strong>
                <p>선택한 기간의 가장 높은 기록</p>
              </article>
              <article className="score-metric-card">
                <span>전체 순위 <Flag size={17} /></span>
                <strong>{data.summary.rank ? data.summary.rank : "-"}<small>{data.summary.rank ? "위" : ""}</small></strong>
                <p>탐험가별 최고 점수 기준</p>
              </article>
              <article className="score-metric-card">
                <span>완주 기록 <Check size={18} /></span>
                <strong>{data.summary.clears}<small>/ {data.summary.games}회</small></strong>
                <p>평균 {formatNumber(data.summary.average)}점</p>
              </article>
            </div>
          </section>
          <div className="dashboard-chart-grid">
            <section className="dashboard-panel chart-panel">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">SMALL STEPS, BETTER SCORES</span>
                  <h2>조금씩, 더 멀리.</h2>
                </div>
                <span className="chart-key">
                  <i /> 탐험 점수
                </span>
              </div>
              {trend.length ? (
                <>
                  <div className="score-chart" aria-label="탐험별 점수 추이">
                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                      minWidth={0}
                    >
                      <AreaChart
                        data={trend}
                        margin={{ top: 16, right: 12, bottom: 0, left: -15 }}
                      >
                        <defs>
                          <linearGradient
                            id="score-fill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#3f8984"
                              stopOpacity={0.24}
                            />
                            <stop
                              offset="100%"
                              stopColor="#3f8984"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          stroke="#e6e8df"
                          vertical={false}
                          strokeDasharray="4 5"
                        />
                        <XAxis
                          dataKey="label"
                          tickLine={false}
                          axisLine={false}
                          tick={{ fill: "#7a8580", fontSize: 12 }}
                          minTickGap={24}
                          dy={8}
                        />
                        <YAxis
                          tickLine={false}
                          axisLine={false}
                          tick={{ fill: "#7a8580", fontSize: 12 }}
                          width={55}
                        />
                        <Tooltip
                          contentStyle={{
                            borderRadius: 12,
                            border: "1px solid #e0e4da",
                            fontFamily: "Gowun",
                            fontSize: 14,
                          }}
                          formatter={(value) => [
                            `${formatNumber(Number(value))}점`,
                            "탐험 점수",
                          ]}
                        />
                        <Area
                          isAnimationActive={false}
                          type="monotone"
                          dataKey="score"
                          stroke="#3f8984"
                          strokeWidth={3}
                          fill="url(#score-fill)"
                          dot={{ r: 4, fill: "#fbfaf5", strokeWidth: 2 }}
                          activeDot={{ r: 6 }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="chart-footnote">
                    최근 최대 30개의 탐험 기록을 시간순으로 표시합니다.
                  </p>
                </>
              ) : (
                <EmptyState title="첫 발걸음을 기다리고 있어요.">
                  <p>게임 기록을 가져오면 점수의 변화가 여기에 나타나요.</p>
                  <Link to={user ? "/play" : "/login"} className="text-link">
                    첫 모험 시작하기 <ArrowUpRight size={15} />
                  </Link>
                </EmptyState>
              )}
            </section>
            <section className="dashboard-panel progress-panel">
              <span className="eyebrow">LAST EXPEDITION</span>
              <h2>지난 모험의 발자국.</h2>
              <img
                className="progress-penguin"
                src="/assets/penguin.png"
                alt=""
              />
              <p>
                {latest
                  ? `${formatDate(latest.date)} 탐험 · ${latest.cleared ? "모두 함께 귀환했어요" : "다음 모험에서 다시 만나요"}`
                  : "아직 남겨진 탐험 기록이 없어요."}
              </p>
              <div className="progress-item">
                <div>
                  <span>
                    <Fish size={16} />
                    모은 물고기
                  </span>
                  <strong>
                    {latest?.fish || 0}
                    <small>/30</small>
                  </strong>
                </div>
                <div className="progress-track">
                  <span
                    style={{ width: `${((latest?.fish || 0) / 30) * 100}%` }}
                  />
                </div>
              </div>
              <div className="progress-item">
                <div>
                  <span>
                    <Heart size={16} />
                    구조한 친구
                  </span>
                  <strong>
                    {latest?.rescued || 0}
                    <small>/3</small>
                  </strong>
                </div>
                <div className="progress-track yellow">
                  <span
                    style={{ width: `${((latest?.rescued || 0) / 3) * 100}%` }}
                  />
                </div>
              </div>
              <span className="progress-note">
                물고기 30마리와 친구 3마리, 빙붕 탈출 후 귀환!
              </span>
            </section>
          </div>
          <section className="dashboard-panel record-table-panel">
            <div className="record-table-heading">
              <div className="record-tabs" role="group" aria-label="기록 종류">
                <button
                  className={tab === "records" ? "active" : ""}
                  onClick={() => {
                    setTab("records");
                    setPage(0);
                  }}
                >
                  나의 탐험 기록<span>{data.records.length}</span>
                </button>
                <button
                  className={tab === "ranking" ? "active" : ""}
                  onClick={() => {
                    setTab("ranking");
                    setPage(0);
                  }}
                >
                  전체 탐험가 순위
                </button>
              </div>
              {tab === "records" && (
                <button
                  className="text-link"
                  onClick={exportRecords}
                  disabled={!data.records.length}
                >
                  <Download size={15} />
                  CSV 내보내기
                </button>
              )}
            </div>
            {tab === "records" && data.records.length > 0 && (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>탐험 날짜</th>
                      <th>점수</th>
                      <th>물고기</th>
                      <th>구조한 친구</th>
                      <th>탐험 시간</th>
                      <th>결과</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.records
                      .slice(page * 8, (page + 1) * 8)
                      .map((record, index) => (
                        <tr key={record.id}>
                          <td>
                            <span className="table-index">
                              {String(page * 8 + index + 1).padStart(2, "0")}
                            </span>
                            {new Date(record.date).toLocaleDateString("ko-KR")}
                            <small className="source-label">웹 게임 자동 저장</small>
                          </td>
                          <td className="table-score">
                            {formatNumber(record.score)}
                            <small>점</small>
                          </td>
                          <td>
                            {record.fish}
                            <small> / 30</small>
                          </td>
                          <td>
                            {record.rescued}
                            <small> / 3</small>
                          </td>
                          <td>
                            {Math.floor(record.seconds / 60)}분{" "}
                            {record.seconds % 60}초
                          </td>
                          <td>
                            <span
                              className={`result-pill ${record.cleared ? "cleared" : ""}`}
                            >
                              {record.cleared ? (
                                <>
                                  <Check size={12} />
                                  완주
                                </>
                              ) : (
                                "미완주"
                              )}
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
            {tab === "ranking" && data.leaderboard.length > 0 && (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>순위</th>
                      <th>탐험가</th>
                      <th>최고 점수</th>
                      <th>물고기 / 친구</th>
                      <th>기록 날짜</th>
                      <th>결과</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.leaderboard
                      .slice(page * 8, (page + 1) * 8)
                      .map((rank) => (
                        <tr
                          key={rank.rank}
                          className={rank.isMe ? "my-rank" : ""}
                        >
                          <td>
                            <span className={`rank-medal medal-${rank.rank}`}>
                              {String(rank.rank).padStart(2, "0")}
                            </span>
                          </td>
                          <td>
                            <strong>{rank.nickname}</strong>
                            {rank.isMe && <span className="me-pill">나</span>}
                          </td>
                          <td className="table-score">
                            {formatNumber(rank.score)}
                            <small>점</small>
                          </td>
                          <td>
                            {rank.fish}/30 · {rank.rescued}/3
                          </td>
                          <td>
                            {new Date(rank.date).toLocaleDateString("ko-KR")}
                          </td>
                          <td>
                            <span
                              className={`result-pill ${rank.cleared ? "cleared" : ""}`}
                            >
                              {rank.cleared ? "완주" : "미완주"}
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
            {(tab === "records"
              ? !data.records.length
              : !data.leaderboard.length) && (
              <EmptyState
                title={
                  tab === "records"
                    ? "아직 기록이 없어요."
                    : "첫 번째 탐험가가 되어보세요."
                }
              >
                <p>게임에서 엔딩을 달성하면 점수가 여기에 자동 저장됩니다.</p>
                <Link className="button button-outline" to={user ? "/play" : "/login"}>
                  게임 시작하기 <ArrowUpRight size={16} />
                </Link>
              </EmptyState>
            )}
            <div className="table-footer">
              <span>실제 게임에서 저장된 기록만 표시됩니다.</span>
              <div className="pagination">
                <button
                  className="icon-button"
                  disabled={page === 0}
                  onClick={() => setPage((value) => value - 1)}
                  aria-label="이전 페이지"
                >
                  <ChevronLeft size={16} />
                </button>
                <span>
                  {page + 1} /{" "}
                  {Math.max(
                    1,
                    Math.ceil(
                      (tab === "records"
                        ? data.records.length
                        : data.leaderboard.length) / 8,
                    ),
                  )}
                </span>
                <button
                  className="icon-button"
                  disabled={
                    (page + 1) * 8 >=
                    (tab === "records"
                      ? data.records.length
                      : data.leaderboard.length)
                  }
                  onClick={() => setPage((value) => value + 1)}
                  aria-label="다음 페이지"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </section>
          <p className="dashboard-storage-note">
            계정과 점수는 서버에 저장됩니다. 데스크톱 게임의 로컬 순위표와는
            별도로 관리됩니다.
          </p>
        </>
      )}
    </main>
  );
}
