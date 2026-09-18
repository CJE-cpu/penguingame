import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
  Check,
  ArrowLeft,
} from "lucide-react";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import { Sprite } from "../components";
import type { User } from "../types";

export default function Login() {
  const [params, setParams] = useSearchParams();
  const register = params.get("mode") === "register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { setUser, user } = useAuth();
  const navigate = useNavigate();
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await api<{ user: User }>(
        register ? "/auth/register" : "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password, nickname }) },
      );
      setUser(data.user);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  if (user)
    return (
      <main className="section-shell page-main">
        <div className="signed-in-card">
          <img src="/assets/penguin.png" alt="" />
          <h1>다시 만났네요, {user.nickname}님.</h1>
          <p>당신의 모험 기록이 기다리고 있어요.</p>
          <Link to="/dashboard" className="button button-dark">
            대시보드로 이동 <ArrowRight size={18} />
          </Link>
        </div>
      </main>
    );
  return (
    <main className="section-shell login-page">
      <div className="login-art">
        <span className="eyebrow">A PLACE FOR YOUR STORY</span>
        <h1>
          당신의 모험도,
          <br />
          기록이 됩니다.
        </h1>
        <div className="login-landscape">
          <Sprite />
          <img src="/assets/baby.png" alt="아기 펭귄" />
        </div>
        <div className="login-art-caption">
          <span>SMALL FEET. BIG ADVENTURES.</span>
          <p>
            모은 물고기만큼, 걸어온 길만큼.
            <br />
            다음 모험을 위한 기록을 남겨보세요.
          </p>
        </div>
      </div>
      <div className="login-form-wrap">
        <Link to="/" className="back-link">
          <ArrowLeft size={15} /> 모험의 시작으로
        </Link>
        <div className="login-intro">
          <span className="eyebrow">WELCOME TO THE CLUB</span>
          <h2>{register ? "함께 모험을 시작해요." : "다시 만나 반가워요."}</h2>
          <p>
            {register
              ? "나만의 탐험 계정을 만들고 기록을 모아보세요."
              : "로그인하고 어제의 기록을 이어가 보세요."}
          </p>
        </div>
        <div className="segmented auth-tabs">
          <button
            className={!register ? "active" : ""}
            onClick={() => {
              setParams({});
              setError("");
            }}
          >
            로그인
          </button>
          <button
            className={register ? "active" : ""}
            onClick={() => {
              setParams({ mode: "register" });
              setError("");
            }}
          >
            회원가입
          </button>
        </div>
        <form onSubmit={(event) => void submit(event)}>
          {register && (
            <label className="form-field">
              닉네임
              <span className="field-input">
                <UserRound size={18} />
                <input
                  name="nickname"
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  placeholder="남극에서 불릴 이름"
                  autoComplete="nickname"
                  required
                  minLength={2}
                  maxLength={16}
                />
              </span>
            </label>
          )}
          <label className="form-field">
            이메일
            <span className="field-input">
              <Mail size={18} />
              <input
                type="email"
                name="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="penguin@example.com"
                autoComplete="email"
                required
                maxLength={254}
              />
            </span>
          </label>
          <label className="form-field">
            비밀번호
            <span className="field-input">
              <LockKeyhole size={18} />
              <input
                type={visible ? "text" : "password"}
                name="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={
                  register
                    ? "8자 이상 입력해 주세요"
                    : "비밀번호를 입력해 주세요"
                }
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 8 : 1}
                maxLength={128}
              />
              <button
                type="button"
                className="icon-button"
                aria-label={visible ? "비밀번호 숨기기" : "비밀번호 보기"}
                onClick={() => setVisible(!visible)}
              >
                {visible ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          {register && (
            <div className="form-tip">
              <Check size={14} /> 비밀번호는 암호화된 해시로 안전하게
              보관합니다.
            </div>
          )}
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <button
            className="button button-dark auth-submit"
            type="submit"
            disabled={busy}
          >
            {busy
              ? "잠시만 기다려 주세요…"
              : register
                ? "탐험 클럽 가입하기"
                : "로그인"}
            {!busy && <ArrowRight size={18} />}
          </button>
        </form>
        <p className="auth-note">
          가입하면 개인 기록과 전체 탐험가 순위를 볼 수 있어요.
          <br />
          이메일은 로그인에 사용되며 순위표에는 공개되지 않습니다.
        </p>
        <Link to="/dashboard" className="text-link auth-demo-link">
          가입 전에 예시 대시보드 둘러보기 <ArrowUpRightIcon />
        </Link>
      </div>
    </main>
  );
}
function ArrowUpRightIcon() {
  return <ArrowRight size={16} />;
}
