import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  Upload,
  X,
} from "lucide-react";
import { useAuth } from "../auth";
import { api, ApiError, errorMessage, formatDate, formatNumber } from "../api";
import { EmptyState, LoadingState, Modal, PageHeading } from "../components";
import type { DashboardData, DesktopRecord } from "../types";

export default function Dashboard() {
  const { user, loading: authLoading, refresh } = useAuth();
  const [demo, setDemo] = useState(!user);
  const [range, setRange] = useState("all");
  const [tab, setTab] = useState("records");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [upload, setUpload] = useState(false);
  const [notice, setNotice] = useState("");
  const navigate = useNavigate();
  useEffect(() => {
    setDemo(!user);
    setPage(0);
  }, [user]);
  useEffect(() => {
    if (authLoading) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setPage(0);
    api<DashboardData>(demo ? "/demo" : `/dashboard?range=${range}`, {
      signal: controller.signal,
    })
      .then((result) => {
        if (demo && range !== "all") {
          const after = Date.now() - (range === "week" ? 7 : 30) * 86400000;
          const records = result.records.filter(
            (row) => Date.parse(row.date) >= after,
          );
          result = {
            ...result,
            records: [...records].reverse(),
            trend: records,
            summary: {
              ...result.summary,
              games: records.length,
              clears: records.filter((r) => r.cleared).length,
              best: records.length
                ? Math.max(...records.map((r) => r.score))
                : 0,
              average: records.length
                ? Math.round(
                    records.reduce((sum, r) => sum + r.score, 0) /
                      records.length,
                  )
                : 0,
            },
          };
        } else if (demo)
          result = { ...result, records: [...result.records].reverse() };
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
  }, [demo, range, revision, authLoading, refresh]);
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
  const startImport = () => {
    if (!user) {
      navigate("/login");
      return;
    }
    setUpload(true);
  };
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
    anchor.download = demo
      ? "penguin-demo-records.csv"
      : "penguin-my-records.csv";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <main className="section-shell page-main dashboard-page">
      <PageHeading
        eyebrow="YOUR EXPEDITION LOG"
        title="모험을 숫자로."
        description={
          demo
            ? "작은 발걸음도, 멋진 기록이 됩니다. 예시 대시보드를 둘러보세요."
            : `${user?.nickname}님의 탐험 기록. 지난 모험을 돌아보고 다음 발걸음을 준비해요.`
        }
      >
        <button className="button button-dark" onClick={startImport}>
          <Upload size={17} /> 게임 기록 가져오기
        </button>
      </PageHeading>
      <div className={`dashboard-banner ${demo ? "is-demo" : ""}`}>
        <span>
          <Info size={17} />
          {demo ? (
            <>
              <strong>미리보기 · 예시 데이터</strong>
              <span> 실제 유저 기록이 아닌 대시보드 체험용 기록입니다.</span>
            </>
          ) : (
            <>
              <strong>나의 실제 기록</strong>
              <span> 게임에서 업로드한 탐험 기록을 계정에 보관합니다.</span>
            </>
          )}
        </span>
        {user ? (
          <button
            className="text-link"
            onClick={() => {
              setDemo(!demo);
              setPage(0);
            }}
          >
            {demo ? "내 기록으로 돌아가기" : "예시 데이터 보기"}
            <ArrowUpRight size={15} />
          </button>
        ) : (
          <Link className="text-link" to="/login">
            로그인하고 기록 시작 <ArrowUpRight size={15} />
          </Link>
        )}
      </div>
      <div className="dashboard-toolbar">
        <div className="dashboard-owner">
          <span className="avatar avatar-large">
            {demo ? "❄" : user?.nickname.slice(0, 1)}
          </span>
          <div>
            <strong>
              {demo
                ? "빙하 탐험가의 대시보드"
                : `${user?.nickname}님의 대시보드`}
            </strong>
            <span>{demo ? "DEMO EXPLORER" : "MY EXPEDITION RECORDS"}</span>
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
          <div className="stat-grid">
            <div className="stat-card stat-featured">
              <span>
                나의 최고 점수
                <Trophy size={19} />
              </span>
              <strong>
                {formatNumber(data.summary.best)}
                <small>점</small>
              </strong>
              <p>
                <Flag size={13} /> 선택한 기간의 가장 빛나는 기록
              </p>
            </div>
            <div className="stat-card">
              <span>
                탐험가 순위
                <Flag size={19} />
              </span>
              <strong>
                {data.summary.rank ? `${data.summary.rank}` : "—"}
                <small>{data.summary.rank ? "위" : ""}</small>
              </strong>
              <p>탐험가별 최고 점수 기준</p>
            </div>
            <div className="stat-card">
              <span>
                완주한 모험
                <Check size={20} />
              </span>
              <strong>
                {data.summary.clears}
                <small>/ {data.summary.games}회</small>
              </strong>
              <p>물고기와 친구들을 데리고 귀환</p>
            </div>
            <div className="stat-card">
              <span>
                평균 탐험 점수
                <Fish size={20} />
              </span>
              <strong>
                {formatNumber(data.summary.average)}
                <small>점</small>
              </strong>
              <p>총 {data.summary.games}번의 탐험이 쌓였어요</p>
            </div>
          </div>
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
                  <button onClick={startImport} className="text-link">
                    첫 기록 가져오기 <Upload size={15} />
                  </button>
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
                            <small className="source-label">
                              {record.source === "demo"
                                ? "예시 기록"
                                : "게임 업로드"}
                            </small>
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
                <p>게임을 플레이한 뒤 기록 파일을 가져와 주세요.</p>
                <button className="button button-outline" onClick={startImport}>
                  <Upload size={16} /> 게임 기록 가져오기
                </button>
              </EmptyState>
            )}
            <div className="table-footer">
              <span>
                {demo
                  ? "예시 데이터입니다."
                  : "유저가 업로드한 게임 기록이며 서버에서 플레이를 검증한 경쟁 순위는 아닙니다."}
              </span>
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
      {notice && (
        <div className="toast" role="status">
          <Check size={17} />
          {notice}
          <button
            className="icon-button"
            onClick={() => setNotice("")}
            aria-label="알림 닫기"
          >
            <X size={16} />
          </button>
        </div>
      )}
      {upload && (
        <ImportModal
          onClose={() => setUpload(false)}
          onImported={(count) => {
            setUpload(false);
            setDemo(false);
            setRevision((value) => value + 1);
            setNotice(
              `${count}개 기록을 가져왔어요. 같은 모험의 기록은 갱신됩니다.`,
            );
          }}
        />
      )}
    </main>
  );
}

function ImportModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (count: number) => void;
}) {
  const [records, setRecords] = useState<DesktopRecord[]>([]);
  const [name, setName] = useState("");
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const names = useMemo(
    () => [...new Set(records.map((row) => row.name))],
    [records],
  );
  const selected = records.filter((row) => row.name === name && row.score > 0);
  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setRecords([]);
    setFilename(file.name);
    try {
      if (file.size > 512 * 1024)
        throw new Error("512KB 이하의 기록 파일을 선택해 주세요.");
      const json = JSON.parse(await file.text()) as {
        version?: number;
        history?: DesktopRecord[];
      };
      if (
        json.version !== 1 ||
        !Array.isArray(json.history) ||
        !json.history.length ||
        json.history.length > 100 ||
        json.history.some(
          (row) =>
            !row || typeof row.name !== "string" || typeof row.run !== "string",
        )
      )
        throw new Error("게임에서 생성한 scores.json 파일을 선택해 주세요.");
      setRecords(json.history);
      setName(json.history[0].name);
    } catch (err) {
      setError(
        err instanceof SyntaxError
          ? "JSON 형식의 점수 파일이 아닙니다."
          : errorMessage(err),
      );
    }
  };
  const save = async () => {
    if (!selected.length || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ imported: number }>("/scores/import", {
        method: "POST",
        body: JSON.stringify({ records: selected }),
      });
      onImported(result.imported);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      title="게임 기록 가져오기"
      onClose={() => {
        if (!busy) onClose();
      }}
      className="import-modal"
    >
      <p className="modal-intro">
        데스크톱 게임에서 남긴 발자국을 웹 계정으로 가져옵니다.
      </p>
      <div className="import-help">
        <span>1. 게임에서 F4로 이름을 설정하고 모험해요.</span>
        <span>2. 게임을 종료해 점수 기록을 저장해요.</span>
        <span>3. 아래 위치의 파일을 선택해 주세요.</span>
        <code>%LOCALAPPDATA%\AntarcticPenguin\scores.json</code>
      </div>
      <label className="upload-zone">
        <Upload size={26} />
        <strong>{filename || "scores.json 파일 선택"}</strong>
        <span>JSON 파일 · 최대 512KB</span>
        <input
          type="file"
          accept=".json,application/json"
          onChange={(event) => void choose(event)}
          disabled={busy}
          aria-label="점수 기록 파일 선택"
        />
      </label>
      {records.length > 0 && (
        <div className="import-selection">
          <label className="form-field">
            가져올 게임 닉네임
            <select
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={busy}
            >
              {names.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <p>
            <Fish size={16} />
            {selected.length}개 탐험 기록 · 최고{" "}
            {formatNumber(
              selected.length
                ? Math.max(...selected.map((row) => row.score))
                : 0,
            )}
            점
          </p>
          <small>
            선택한 닉네임의 기록을 현재 로그인한 웹 계정에 등록합니다.
          </small>
        </div>
      )}
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <button
        className="button button-dark import-submit"
        disabled={!selected.length || busy}
        onClick={() => void save()}
      >
        {busy ? "기록을 저장하고 있어요…" : "내 계정에 기록 저장"}
        <ArrowUpRight size={17} />
      </button>
    </Modal>
  );
}
