"""
Capture the report's figures from a running, English-seeded instance, with the
UI in the requested locale. Also scans every captured screen for text in the
other language, which is how mixed-language UI was found (DEC-032).

    SEED_LANG=en python3 scripts/seed-demo.py http://localhost:8091
    .pwenv/bin/python scripts/report-screenshots.py http://localhost:8091 report/figures en
"""
import asyncio, os, re, sys
from playwright.async_api import async_playwright

BASE, OUT, LOCALE = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "en")
VI = re.compile(r"[ăâđêôơưàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ]", re.I)
# Data, not UI: people's and seeded names may legitimately be Vietnamese.
ALLOW = ["Phạm", "Đàm", "Đôn", "Tú", "Huynh", "Tiếng Việt", "Văn", "Minh", "Đức"]
leaks = {}


async def scan(pg, name):
    if LOCALE != "en":
        return
    text = await pg.evaluate("document.body.innerText")
    bad = []
    for line in text.split("\n"):
        stripped = line
        for a in ALLOW:
            stripped = stripped.replace(a, "")
        if len(line.strip()) > 3 and VI.search(stripped):  # 2-3 chars = avatar initials
            bad.append(line.strip()[:90])
    if bad:
        leaks[name] = sorted(set(bad))[:8]


async def shot(pg, name, wait=700):
    await pg.wait_for_timeout(wait)
    await pg.screenshot(path=f"{OUT}/{name}.png")
    await scan(pg, name)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=False, args=["--headless=new"])
        ctx = await b.new_context(viewport={"width": 1440, "height": 860}, device_scale_factor=2, locale="en-GB")
        await ctx.add_init_script(f"localStorage.setItem('koshi_locale','{LOCALE}'); localStorage.setItem('koshi_theme','light')")
        pg = await ctx.new_page()
        await pg.goto(BASE + "/")
        await shot(pg, "landing", 1500)
        await pg.evaluate("window.scrollTo(0, 900)")
        await shot(pg, "landing-features")
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.get_by_role("button", name=re.compile("Sign in|Đăng nhập")).first.click()
        await pg.fill('input[type="email"]', "huynh@koshi.dev")
        await pg.fill('input[type="password"]', os.environ.get("SEED_PASSWORD", "Koshi@2026"))
        await shot(pg, "login")
        await pg.click('button[type="submit"]')
        await pg.wait_for_timeout(2500)
        # Open the Scrum project from the dashboard.
        await pg.locator("header button").filter(has_text=re.compile("Online Store|Website|Koshi Mobile")).first.click()
        await pg.wait_for_timeout(800)
        await shot(pg, "dashboard")
        await pg.get_by_role("button", name="Koshi Mobile App").first.click()
        await pg.wait_for_timeout(1000)
        await pg.keyboard.press("Escape")
        await shot(pg, "board-kanban", 1200)
        await pg.keyboard.press("b")
        await shot(pg, "board-table")
        await pg.keyboard.press("b")
        await pg.wait_for_timeout(400)
        # A task with discussion: "Offline change queue".
        await pg.get_by_text(re.compile("Offline change queue|Hàng đợi thay đổi khi mất mạng")).first.click()
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1200)
        hist = pg.locator('[data-testid="task-history"] button')
        if await hist.count():
            await hist.first.click()
        await shot(pg, "task-detail", 1200)
        await pg.keyboard.press("Escape")
        await pg.click('[data-testid="open-scrum"]')
        await shot(pg, "scrum-sprints", 1500)
        for tab in ["PLANNING", "BURNDOWN", "VELOCITY"]:
            await pg.click(f'[data-tab="{tab}"]')
            await shot(pg, f"scrum-{tab.lower()}", 1200)
        await pg.click('[data-tab="RETRO"]')
        await pg.click('[data-action="retro"]')
        await pg.wait_for_selector('[data-testid="retro"]', timeout=60000)
        await shot(pg, "scrum-retro")
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(400)
        async def ai(menu_text, name, action=None, wait_sel=None, wait=9000):
            await pg.get_by_role("button", name=re.compile("AI Tools|Công cụ AI")).click()
            await pg.locator("button", has_text=menu_text).first.click()
            await pg.wait_for_timeout(600)
            if action:
                await pg.locator("button", has_text=action).first.click()
            await pg.wait_for_timeout(wait)
            await shot(pg, name, 300)
            await pg.keyboard.press("Escape")
            await pg.wait_for_timeout(400)
        await ai(re.compile("Weekly Summary|Tóm tắt tuần"), "ai-weekly")
        await ai(re.compile("Meeting Minutes|Biên bản họp"), "ai-minutes", re.compile("Extract|Trích xuất"))
        await ai(re.compile("Smart Assignment|Giao việc"), "ai-assign", re.compile("Recommend|Gợi ý người"))
        await pg.get_by_role("button", name=re.compile("AI Tools|Công cụ AI")).click()
        await pg.locator("button", has_text=re.compile("Goal Decomposer|Chia nhỏ")).first.click()
        await pg.wait_for_timeout(500)
        await pg.get_by_placeholder(re.compile("Describe your|Mô tả mục tiêu")).fill("Add MoMo e-wallet payments to the online store" if LOCALE == "en" else "Thêm thanh toán ví MoMo cho cửa hàng online")
        await pg.locator("button", has_text=re.compile("^\\s*Decompose|Chia nhỏ$")).first.click()
        await pg.wait_for_timeout(9000)
        await shot(pg, "ai-decomposer", 300)
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(400)
        await pg.keyboard.press("v")
        await shot(pg, "dag", 1200)
        await pg.keyboard.press("Escape")
        await pg.keyboard.press("?")
        await shot(pg, "shortcuts")
        await pg.keyboard.press("Escape")
        await pg.click("#notifications-bell")
        await shot(pg, "notifications", 1000)
        await pg.locator("button", has_text=re.compile("Back to board|Về bảng")).first.click()
        await pg.wait_for_timeout(600)
        await pg.locator("header button").filter(has_text=re.compile("PM:|MEMBER:|THÀNH VIÊN:")).first.click()
        await shot(pg, "profile", 1000)
        await b.close()
    if leaks:
        print("MIXED-LANGUAGE TEXT FOUND:")
        for k, v in leaks.items():
            print(" ", k, v)
    else:
        print("no mixed-language UI text in", LOCALE)


asyncio.run(main())
