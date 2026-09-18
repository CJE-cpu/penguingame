import { lazy, Suspense, useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { SiteHeader, SiteFooter, LoadingState } from "./components";
import { useAuth } from "./auth";
import Home from "./pages/Home";
const Explore = lazy(() => import("./pages/Explore"));
const Collection = lazy(() => import("./pages/Collection"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Login = lazy(() => import("./pages/Login"));
const Story = lazy(() => import("./pages/Story"));
const titles: Record<string, string> = {
  "/": "남극 펭귄의 모험",
  "/explore": "탐험 지도",
  "/collection": "탐험 도감",
  "/dashboard": "점수 대시보드",
  "/login": "탐험가 로그인",
  "/story": "만드는 이야기",
};
export default function App() {
  const location = useLocation();
  const { error, refresh } = useAuth();
  useEffect(() => {
    window.scrollTo({ top: 0 });
    document.title = `${titles[location.pathname] || "페이지를 찾을 수 없습니다"} · PENGUIN CLUB`;
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main-content">
        본문으로 바로가기
      </a>
      <SiteHeader />
      {error && (
        <div className="global-alert" role="alert">
          {error}
          <button onClick={() => void refresh()}>다시 연결</button>
        </div>
      )}
      <div id="main-content">
        <Suspense
          fallback={
            <div className="section-shell page-main">
              <LoadingState />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/login" element={<Login />} />
            <Route path="/story" element={<Story />} />
            <Route
              path="*"
              element={
                <main className="section-shell page-main not-found">
                  <span>404 · LOST IN THE SNOW</span>
                  <h1>잠깐, 길을 잃었나요?</h1>
                  <p>발자국을 따라 모험의 시작으로 돌아가요.</p>
                  <Link to="/" className="button button-dark">
                    시작으로 돌아가기 <ArrowRight size={18} />
                  </Link>
                </main>
              }
            />
          </Routes>
        </Suspense>
      </div>
      <SiteFooter />
    </>
  );
}
