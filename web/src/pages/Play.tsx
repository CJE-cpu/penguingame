import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Download, Gamepad2, Maximize2 } from "lucide-react";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { DesktopRecord } from "../types";

const pendingKey = "penguin-pending-score";
const updatedKey = "penguin-score-updated";

export default function Play() {
  const { user, loading } = useAuth();
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "login" | "error">("idle");
  const [saveMessage, setSaveMessage] = useState("");
  const submit = useCallback(async (record: DesktopRecord) => {
    setSaveState("saving");
    setSaveMessage("엔딩 기록을 대시보드에 저장하고 있어요.");
    try {
      await api("/scores/import", {
        method: "POST",
        body: JSON.stringify({ records: [record], source: "browser" }),
      });
      localStorage.removeItem(pendingKey);
      localStorage.setItem(updatedKey, JSON.stringify({ run: record.run, at: Date.now() }));
      window.dispatchEvent(new Event(updatedKey));
      setSaveState("saved");
      setSaveMessage(`${record.score.toLocaleString("ko-KR")}점이 저장되었습니다.`);
    } catch (error) {
      setSaveState("error");
      setSaveMessage(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    if (loading || !user) return;
    const pending = localStorage.getItem(pendingKey);
    if (!pending) return;
    try {
      void submit(JSON.parse(pending) as DesktopRecord);
    } catch {
      localStorage.removeItem(pendingKey);
    }
  }, [loading, submit, user]);

  useEffect(() => {
    const receiveScore = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      try {
        const message = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (message?.type !== "penguin-score" || !message.record) return;
        const record = message.record as DesktopRecord;
        localStorage.setItem(pendingKey, JSON.stringify(record));
        if (user) void submit(record);
        else {
          setSaveState("login");
          setSaveMessage("로그인하면 방금 달성한 엔딩 점수가 자동 저장됩니다.");
        }
      } catch {
        setSaveState("error");
        setSaveMessage("엔딩 기록을 읽지 못했습니다.");
      }
    };
    window.addEventListener("message", receiveScore);
    return () => window.removeEventListener("message", receiveScore);
  }, [submit, user]);

  const fullscreen = () => {
    const shell = document.querySelector<HTMLElement>(".game-shell");
    void shell?.requestFullscreen?.();
  };

  return (
    <main className="section-shell page-main play-page">
      <div className="play-heading">
        <div>
          <span className="eyebrow">
            <span /> PLAY IN YOUR BROWSER
          </span>
          <h1>지금 바로 남극으로</h1>
          <p>설치 없이 화면을 클릭하면 모험이 시작됩니다.</p>
        </div>
        <div className="play-actions">
          <button className="button button-outline" onClick={fullscreen}>
            <Maximize2 size={17} /> 전체 화면
          </button>
          <a href="/api/download" className="button button-dark">
            <Download size={17} /> Windows 버전
          </a>
        </div>
      </div>
      <section className="game-shell" aria-label="남극 펭귄의 모험 게임">
        <iframe
          ref={frameRef}
          className="game-frame"
          src="/game/index.html?v=4"
          title="남극 펭귄의 모험"
          allow="autoplay; fullscreen"
          allowFullScreen
        />
      </section>
      {saveState !== "idle" && (
        <div className={`game-save-status is-${saveState}`} role="status">
          <Check size={19} />
          <span>{saveMessage}</span>
          {saveState === "saved" && <Link to="/dashboard">대시보드 보기</Link>}
          {saveState === "login" && <Link to="/login">로그인하기</Link>}
        </div>
      )}
      <div className="play-help">
        <Gamepad2 size={20} />
        <span><strong>화질</strong> F6</span>
        <p>
          <strong>이동</strong> 방향키 또는 A·D · <strong>점프</strong> Space ·{" "}
          <strong>슬라이딩</strong> 아래 방향키 또는 S
        </p>
      </div>
    </main>
  );
}
