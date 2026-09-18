import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  Code2,
  LogOut,
  Menu,
  X,
  Compass,
  Snowflake,
} from "lucide-react";
import { useAuth } from "./auth";
import { errorMessage } from "./api";

export function Sprite({ className = "" }: { className?: string }) {
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = setInterval(() => setFrame((value) => (value + 1) % 8), 145);
    return () => clearInterval(timer);
  }, []);
  return (
    <img
      className={`penguin-sprite ${className}`}
      src={`/assets/walk-${frame}.png`}
      alt=""
      aria-hidden="true"
    />
  );
}
export function Modal({
  title,
  children,
  onClose,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${className}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="닫기">
          <X size={22} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function SiteHeader() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);
  const signOut = async () => {
    try {
      await logout();
      navigate("/");
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  return (
    <>
      <div className="top-strip">
        <Snowflake size={12} /> A LITTLE ADVENTURE AT THE END OF THE WORLD{" "}
        <Snowflake size={12} />
      </div>
      <header className="site-header">
        <div className="header-inner">
          <Link to="/" className="brand" aria-label="펭귄 클럽 홈">
            <span className="brand-mark">
              <img src="/assets/penguin.png" alt="" />
            </span>
            <span>
              PENGUIN
              <br />
              CLUB<span className="brand-dot">.</span>
            </span>
          </Link>
          <button
            className="mobile-menu icon-button"
            aria-label="메뉴"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            {open ? <X /> : <Menu />}
          </button>
          <nav
            className={open ? "main-nav is-open" : "main-nav"}
            aria-label="메인 메뉴"
          >
            <NavLink to="/" end>
              모험의 시작
            </NavLink>
            <NavLink to="/explore">탐험 지도</NavLink>
            <NavLink to="/collection">탐험 도감</NavLink>
            <NavLink to="/dashboard">점수 대시보드</NavLink>
            {user ? (
              <div className="account-nav">
                <Link className="account-pill" to="/dashboard">
                  <span className="avatar">{user.nickname.slice(0, 1)}</span>
                  {user.nickname}
                </Link>
                <button
                  className="icon-button"
                  onClick={() => void signOut()}
                  aria-label="로그아웃"
                >
                  <LogOut size={18} />
                </button>
              </div>
            ) : (
              <Link to="/login" className="button button-dark nav-login">
                로그인 <ArrowUpRight size={16} />
              </Link>
            )}
          </nav>
        </div>
      </header>
      {error && (
        <div className="global-alert" role="alert">
          {error}
        </div>
      )}
    </>
  );
}
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-main">
        <div>
          <div className="footer-wordmark">
            PENGUIN CLUB<span>.</span>
          </div>
          <p>
            작은 발걸음이 모여, 커다란 모험이 됩니다.
            <br />
            남극에서 만나요.
          </p>
        </div>
        <div className="footer-links">
          <Link to="/explore">탐험 지도</Link>
          <Link to="/collection">탐험 도감</Link>
          <Link to="/dashboard">나의 기록</Link>
          <Link to="/story">
            만드는 이야기 <ArrowUpRight size={13} />
          </Link>
        </div>
        <a
          className="footer-github"
          href="https://github.com/CJE-cpu/penguingame"
          target="_blank"
          rel="noreferrer"
        >
          <Code2 size={20} /> 프로젝트 코드 보기 <ArrowUpRight size={16} />
        </a>
      </div>
      <div className="footer-bottom">
        <span>
          © {new Date().getFullYear()} PENGUIN CLUB. MADE FOR THE ADVENTURE.
        </span>
        <span>
          <Compass size={13} /> 90° S · ANTARCTICA
        </span>
      </div>
    </footer>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">
          <span />
          {eyebrow}
        </span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Compass size={32} />
      </span>
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function LoadingState() {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" />
      탐험 기록을 불러오고 있어요.
    </div>
  );
}
