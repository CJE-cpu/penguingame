# PENGUIN CLUB — 프론트엔드 포트폴리오

남극 펭귄 게임을 소개하고 탐험 세계와 플레이 기록을 웹으로 연결하는 React·TypeScript 프로젝트입니다. 로그인과 점수 대시보드는 로컬에서 Express·SQLite, Vercel에서 Express Functions·Neon PostgreSQL에 연결됩니다.

## 로컬 실행

Node.js 24 이상이 필요합니다. Python은 웹사이트 실행에 필요하지 않습니다.

```powershell
cd C:\CJE\python_ex\web
npm ci
npm run dev
```

사이트: http://127.0.0.1:5173 / API: http://127.0.0.1:3001

`npm run dev` 하나로 두 서버가 실행됩니다. 종료는 Ctrl+C입니다. 개발 모드에서는 Vite가 `/api` 요청을 서버로 전달하므로 별도의 CORS 설정이 필요하지 않습니다.

## Vercel 배포

프로덕션은 Vercel Functions와 싱가포르 리전의 Neon PostgreSQL을 사용합니다. `vercel.json`이 `/api` 요청을 Express Function으로 전달하고, 나머지 경로는 React 앱으로 연결합니다.

```powershell
npx vercel --prod
```

Neon 연동이 없는 새 프로젝트에는 `DATABASE_URL` 환경 변수가 필요합니다. 비밀번호는 scrypt 해시만 저장되며 세션 쿠키는 HttpOnly, Secure, SameSite=Lax로 설정됩니다.

## 화면과 기능

| 경로          | 기능                                                                                          |
| ------------- | --------------------------------------------------------------------------------------------- |
| `/`           | 게임 소개, 걷는 펭귄, 실제 게임 화면 미리보기, Windows EXE 다운로드                           |
| `/explore`    | 지대 선택이 URL에 남는 인터랙티브 탐험 지도, 지형·적·목표 소개                                |
| `/collection` | 종류별 필터, 이름·특징 검색, `/` 검색창 단축키                                                |
| `/login`      | 이메일 회원가입·로그인, 비밀번호 표시 전환, 오류와 로딩 상태                                  |
| `/dashboard`  | 기간별 최고·평균 점수, 완주 수, 점수 차트, 최근 수집 상태, 기록 목록, 전체 순위, CSV 내보내기 |
| `/story`      | 게임과 웹의 구현 과정, 문제와 개선 경험 소개                                                  |

모바일 내비게이션, 키보드 포커스, 본문 바로가기, 네이티브 모달, 동작 줄이기 설정, 빈 상태·실패 상태·재시도, 경로별 지연 로딩을 제공합니다.

## 로그인과 저장

회원가입한 계정은 `web/.data/penguin.sqlite`에 저장됩니다. 비밀번호는 개별 salt를 사용한 scrypt 해시로 저장하며 원문을 보관하지 않습니다. 세션 토큰은 HttpOnly·SameSite 쿠키로 전달하고 서버에는 토큰의 해시와 만료 시각을 저장합니다. 로그아웃하면 해당 세션이 폐기됩니다. 이메일은 공개 순위표에 표시하지 않습니다.

쓰기 요청은 Origin을 확인하고, 인증 요청에는 횟수 제한을 적용합니다. SQL은 매개변수 바인딩을 사용합니다. 데이터 파일과 실제 계정은 Git에 포함하지 않습니다. 이메일 인증, 비밀번호 찾기, 소셜 로그인은 제공하지 않습니다.

## 게임 점수 가져오기

1. 데스크톱 게임 시작 전에 F4로 닉네임을 설정합니다.
2. 모험을 플레이하고 정상 종료하여 점수 기록을 저장합니다.
3. 웹사이트에 가입하거나 로그인합니다.
4. 대시보드의 **게임 기록 가져오기**에서 `%LOCALAPPDATA%\AntarcticPenguin\scores.json`을 선택합니다.
5. 파일에 여러 닉네임이 있으면 가져올 게임 닉네임을 선택합니다.

선택한 게임 닉네임의 기록은 로그인한 웹 계정에 연결됩니다. 같은 모험의 재업로드는 기존 행을 갱신하며 낮은 점수로 최고 점수를 덮어쓰지 않습니다. 서버가 점수·수집 수·완주 조건·시간·날짜를 검증하고, 잘못된 파일은 전체를 거절합니다. 파일은 최대 512KB, 업로드당 100개, 계정당 1,000개 기록으로 제한합니다.

**데모 기록은 예시임을 표시하며 실제 DB에 저장하지 않습니다.** 게임 파일의 점수는 사용자 업로드 데이터로 표시합니다. 서버에서 실제 플레이를 검증한 경쟁 순위나 치트 방지 기능은 아닙니다. 데스크톱의 로컬 순위표와 웹 DB는 자동 동기화되지 않습니다.

## 확인

```powershell
npm run build
npm test
npm run test:e2e
```

API 테스트는 격리된 메모리 DB와 임시 DB에서 가입·로그인·로그아웃·세션 만료·재실행 복원·기록 갱신·계정 분리·검증·Origin 방어를 확인합니다.

브라우저 테스트는 별도 포트 5174/3002와 `.data/e2e.sqlite`를 사용하므로 실제 DB에 테스트 계정을 만들지 않습니다. Windows에서는 설치된 Edge를 자동 사용합니다. 다른 환경은 `npx playwright install chromium`을 먼저 실행하거나 `BROWSER_PATH`에 브라우저 실행 파일을 지정합니다. 테스트 결과는 `test-results/`에 저장되며 Git에서 제외됩니다.

## 빌드 파일 실행과 배포

```powershell
npm run build
npm start
```

빌드 후 `npm start`는 API와 웹 화면을 모두 http://127.0.0.1:3001 에서 제공합니다. `npm run preview`는 화면만 제공하므로 로그인 검증에는 `npm start`를 사용합니다.

인터넷에 공개하려면 **Node 서버를 실행할 수 있는 호스팅**과 지속 저장 디스크가 필요합니다. 정적 페이지만 제공하는 GitHub Pages에서는 이 서버의 로그인·DB 기능이 작동하지 않습니다.

환경변수 설정 예시:

```powershell
$env:NODE_ENV='production'
$env:APP_ORIGIN='https://실제도메인'
$env:HOST='0.0.0.0'
$env:DB_PATH='/persistent-data/penguin.sqlite'
npm start
```

프로덕션 모드는 `APP_ORIGIN` 설정을 필수로 요구합니다. 실제 도메인에는 HTTPS를 적용하세요. HTTPS origin에서는 세션 쿠키에 Secure를 적용합니다. 신뢰하는 HTTPS 리버스 프록시 1개 뒤에서 운영할 때만 `TRUST_PROXY=1`을 설정합니다. `.env.example`은 설정 참고용이며 자동 로딩하지 않습니다. 호스팅 환경변수나 셸에서 설정하세요.

`.data`의 DB 및 WAL 파일은 배포 시 유지하고 백업해야 합니다. 다운로드 API는 기본적으로 `../pygame/AntarcticPenguin.exe`를 사용합니다. 실행 파일을 별도로 배포하면 `GAME_EXE_PATH`로 위치를 지정하세요.

## 에셋

게임의 기존 남극 배경과 스프라이트를 재사용했고, 게임 코드에서 실제 화면을 캡처했습니다. Jua와 Gowun Dodum은 SIL OFL 라이선스를 포함하며 WOFF2로 압축해 제공합니다. 서버·브라우저 테스트를 위해 별도의 실제 사용자 정보는 필요하지 않습니다.
