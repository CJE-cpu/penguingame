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
  await expect(page.getByText("기록이 비어 있습니다")).toBeVisible();
  await expect(page.locator(".latest-score-card > strong")).toContainText("0");
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

test("register, auto-save, deduplicate, persist a session, logout and login again", async ({
  page,
}) => {
  const unique = Date.now();
  const email = `browser-${unique}@example.test`;
  const nickname = `탐험가${String(unique).slice(-7)}`;
  const password = "Penguin-web-test-123";
  await page.goto("/login?mode=register");
  await page.locator("input[name=nickname]").fill(nickname);
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
        score: 17000,
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
  await page.goto("/play");
  const game = page.frameLocator(".game-frame");
  await expect(game.locator("body")).toBeAttached();
  for (let attempt = 0; attempt < 2; attempt++) {
    for (const record of fixture.history) {
      await game.locator("body").evaluate((_, completedRun) => {
        window.parent.postMessage(
          { type: "penguin-score", record: completedRun },
          window.location.origin,
        );
      }, record);
    }
  }
  await expect(page.locator(".game-save-status")).toContainText("\uC800\uC7A5");
  await page.goto("/dashboard");
  await expect(page.locator(".latest-score-card > strong")).toContainText("17,000");
  await expect(page.locator("tbody tr")).toHaveCount(2);
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

test("browser game package loads from the play page", async ({ page }) => {
  test.setTimeout(120_000);
  const failed: string[] = [];
  const errors: string[] = [];
  const logs: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400)
      failed.push(`${response.status()} ${response.url()}`);
  });
  page.on("requestfailed", (request) =>
    failed.push(`${request.failure()?.errorText} ${request.url()}`),
  );
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    logs.push(`${message.type()}: ${message.text()}`);
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/play");
  await expect(page.getByRole("heading", { name: "지금 바로 남극으로" })).toBeVisible();
  const game = page.frameLocator(".game-frame");
  await expect(game.locator("#canvas")).toBeAttached({ timeout: 30_000 });
  await expect(game.locator("#progress")).toBeAttached();
  await expect(game.locator("#canvas")).toBeVisible({ timeout: 90_000 });
  try {
    await game.locator("#infobox").waitFor({ state: "hidden", timeout: 90_000 });
  } catch {
    const state = await game.locator("body").evaluate(() => ({
      infobox: document.querySelector("#infobox")?.textContent,
      status: document.querySelector("#status")?.textContent,
      progress: (document.querySelector("#progress") as HTMLProgressElement)?.value,
      busy: (window as unknown as { busy?: number }).busy,
      python: "python" in window,
      module: "Module" in window,
    }));
    throw new Error(
      JSON.stringify({ state, failed, errors, logs: logs.slice(-80) }, null, 2),
    );
  }
  await expect.poll(async () => game.locator("#canvas").evaluate((node) => {
    const canvas = node as HTMLCanvasElement;
    const bounds = canvas.getBoundingClientRect();
    return Math.max(Math.abs(canvas.width - bounds.width), Math.abs(canvas.height - bounds.height));
  })).toBeLessThanOrEqual(8);
  expect(failed).toEqual([]);
  expect(errors).toEqual([]);
  await game.locator("body").evaluate(() => {
    window.parent.postMessage(
      JSON.stringify({
        type: "penguin-score",
        record: {
          run: "browser-bridge-test",
          name: "탐험가",
          score: 900,
          fish: 8,
          rescued: 0,
          seconds: 240,
          cleared: true,
          ending: 1,
          date: new Date().toISOString(),
        },
      }),
      window.location.origin,
    );
  });
  await expect(
    page.getByText("로그인하면 방금 달성한 엔딩 점수가 자동 저장됩니다."),
  ).toBeVisible();
});
