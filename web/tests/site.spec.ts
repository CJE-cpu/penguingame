import { test, expect } from "@playwright/test";

test("home, map, collection and preview work on desktop and mobile", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/assets/") && response.status() >= 400) errors.push(`Missing asset: ${response.url()}`);
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "커다란 모험",
  );
  await page.getByRole("button", { name: "게임 둘러보기" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("img")).toBeVisible();
  await expect.poll(() => page.getByRole("dialog").getByRole("img").evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  await page.getByRole("button", { name: "다음 화면" }).click();
  await expect(
    page.getByRole("heading", { name: "얼음 아래의 푸른 바다" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "닫기", exact: true }).click();
  await page.screenshot({
    path: "../build/web-home-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "탐험 지도", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "3. 얼음 동굴" }).click();
  await expect(page).toHaveURL(/region=2/);
  await expect(page.locator(".destination-card h2")).toHaveText("얼음 동굴");
  await page.goto("/collection");
  await page.getByRole("button", { name: "물고기", exact: true }).click();
  await expect(page.locator(".collection-card")).toHaveCount(3);
  await page.getByRole("textbox", { name: "도감 검색" }).fill("황금");
  await expect(page.locator(".collection-card")).toHaveCount(1);
  await page.goto("/dashboard");
  await expect(page.getByText("미리보기 · 예시 데이터")).toBeVisible();
  await expect(page.locator(".stat-featured strong")).toContainText("1,680");
  await page.screenshot({
    path: "../build/web-dashboard-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const url of [
    "/",
    "/explore?region=2",
    "/collection",
    "/dashboard",
    "/login",
  ]) {
    await page.goto(url);
    await expect(page.locator("main")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390);
    await page.screenshot({
      path: `../build/web-mobile-${url.split("?")[0].replaceAll("/", "") || "home"}.png`,
      fullPage: true,
    });
  }
  await page.getByRole("button", { name: "메뉴", exact: true }).click();
  await page
    .getByRole("navigation", { name: "메인 메뉴" })
    .getByRole("link", { name: "점수 대시보드" })
    .click();
  await expect(page).toHaveURL(/dashboard/);
  expect(errors).toEqual([]);
});

test("register, upload, deduplicate, persist a session, logout and login again", async ({
  page,
}) => {
  const email = `browser-${Date.now()}@example.test`;
  const password = "Penguin-web-test-123";
  await page.goto("/login?mode=register");
  await page.getByRole("textbox", { name: "닉네임" }).fill("브라우저 탐험가");
  await page.getByRole("textbox", { name: "이메일" }).fill(email);
  await page.locator("input[name=password]").fill(password);
  await page.getByRole("button", { name: "탐험 클럽 가입하기" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText("나의 실제 기록")).toBeVisible();
  const fixture = {
    version: 1,
    history: [
      {
        name: "게임 펭귄",
        run: "web-test-one",
        score: 1700,
        fish: 30,
        rescued: 3,
        seconds: 420,
        cleared: true,
        date: new Date().toISOString(),
      },
      {
        name: "게임 펭귄",
        run: "web-test-two",
        score: 600,
        fish: 12,
        rescued: 1,
        seconds: 180,
        cleared: false,
        date: new Date(Date.now() - 86400000).toISOString(),
      },
    ],
  };
  for (let i = 0; i < 2; i++) {
    await page
      .getByRole("button", { name: "게임 기록 가져오기", exact: true })
      .first()
      .click();
    await page
      .getByLabel("점수 기록 파일 선택")
      .setInputFiles({
        name: "scores.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(fixture)),
      });
    await expect(
      page.getByRole("dialog").getByText(/2개 탐험 기록/),
    ).toBeVisible();
    await page.getByRole("button", { name: "내 계정에 기록 저장" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.locator(".stat-featured strong")).toContainText("1,700");
    await expect(page.locator("tbody tr")).toHaveCount(2);
  }
  await page.reload();
  await expect(page.getByText("나의 실제 기록")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page
    .getByRole("button", { name: "전체 탐험가 순위", exact: true })
    .click();
  await expect(page.locator(".my-rank")).toBeVisible();
  await page.getByRole("button", { name: "로그아웃" }).click();
  await expect(page).toHaveURL("http://127.0.0.1:5174/");
  await page.goto("/login");
  await page.getByRole("textbox", { name: "이메일" }).fill(email);
  await page.locator("input[name=password]").fill("incorrect-password");
  await page.locator("form").getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("일치하지 않습니다");
  await page.locator("input[name=password]").fill(password);
  await page.locator("form").getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.locator("tbody tr")).toHaveCount(2);
});
