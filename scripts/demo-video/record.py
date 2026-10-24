"""
Record the landing-page demo video by driving the REAL app with Playwright.

Nothing here is mocked or staged: it signs into a seeded local instance
(scripts/seed-demo.py) and uses the product the way a person would. That is
what keeps the video honest (D6 P14) — it can only show features that work.

    python -m venv .pwenv && .pwenv/bin/pip install playwright==1.48.0
    .pwenv/bin/python scripts/demo-video/record.py http://localhost:8090 out/
    # then: scripts/demo-video/encode.sh out/  -> source/frontend/public/demo.mp4

Uses the system Chrome (channel="chrome"), so no browser download. Frames are
captured with the DevTools screencast and timestamped, rather than with
Playwright's recorder, which needs its own ffmpeg build.
"""
import asyncio
import base64
import os
import sys
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090"
OUT = sys.argv[2] if len(sys.argv) > 2 else "demo-out"
EMAIL, PASSWORD = "huynh@koshi.dev", os.environ.get("SEED_PASSWORD", "Koshi@2026")
W, H = 1280, 720


async def caption(pg, text):
    """A lower-third caption, injected into the page so it is part of the frame."""
    await pg.evaluate("""(t) => {
      let el = document.getElementById('__demo_caption');
      if (!el) {
        el = document.createElement('div'); el.id = '__demo_caption';
        el.style.cssText = 'position:fixed;left:50%;bottom:56px;transform:translateX(-50%);z-index:99999;' +
          'background:rgba(15,23,42,.88);color:#fff;font:600 20px/1.3 Inter,system-ui,sans-serif;' +
          'padding:12px 22px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.35);transition:opacity .3s;pointer-events:none';
        document.body.appendChild(el);
      }
      el.textContent = t; el.style.opacity = t ? '1' : '0';
    }""", text)


async def pause(pg, ms):
    await pg.wait_for_timeout(ms)


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False, args=["--headless=new"])
        ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1, locale="vi-VN")
        await ctx.add_init_script("localStorage.setItem('koshi_locale','vi')")
        pg = await ctx.new_page()

        frames = []  # (timestamp, filename)
        cdp = await ctx.new_cdp_session(pg)

        def on_frame(ev):
            name = f"{OUT}/f{len(frames):05d}.jpg"
            with open(name, "wb") as fh:
                fh.write(base64.b64decode(ev["data"]))
            frames.append((ev["metadata"]["timestamp"], name))
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))

        cdp.on("Page.screencastFrame", on_frame)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})

        # 1. Landing
        await pg.goto(BASE + "/")
        await pause(pg, 800)
        await caption(pg, "Koshi — quản lý dự án nhanh như suy nghĩ")
        await pause(pg, 2200)
        for _ in range(10):
            # The landing page scrolls an inner container, not the window, so
            # scroll whichever element actually overflows.
            await pg.evaluate("""() => { const el = [...document.querySelectorAll('*')].find(e => e.scrollHeight > e.clientHeight + 50 && getComputedStyle(e).overflowY.match(/auto|scroll/)) || document.scrollingElement; el.scrollBy({top: 330, behavior: 'smooth'}); }""")
            await pause(pg, 550)
        await pause(pg, 800)
        await pg.evaluate("""() => { const el = [...document.querySelectorAll('*')].find(e => e.scrollHeight > e.clientHeight + 50 && getComputedStyle(e).overflowY.match(/auto|scroll/)) || document.scrollingElement; el.scrollTo({top: 0, behavior: 'smooth'}); }""")
        await pause(pg, 1000)

        # 2. Sign in
        await caption(pg, "Đăng nhập — không cần chọn vai trò")
        await pg.get_by_role("button", name="Đăng nhập").first.click()
        await pause(pg, 500)
        await pg.locator('input[type="email"]').type(EMAIL, delay=45)
        await pg.locator('input[type="password"]').type(PASSWORD, delay=45)
        await pause(pg, 300)
        await pg.click('button[type="submit"]')
        await pause(pg, 1800)

        # 3. Switch to the Scrum project
        await caption(pg, "Mỗi dự án có vai trò riêng — PM hoặc thành viên")
        await pg.locator("header button", has_text="Website").first.click()
        await pause(pg, 1200)
        await pg.get_by_role("button", name="Koshi Mobile App").first.click()
        await pause(pg, 1200)
        await pg.keyboard.press("Escape")
        await pause(pg, 1200)

        # 4. Keyboard-first board
        await caption(pg, "Bảng Kanban điều khiển bằng bàn phím: h/j/k/l, Space đổi trạng thái")
        for key in ["l", "j", "l", "k", "h"]:
            await pg.keyboard.press(key)
            await pause(pg, 420)
        await pause(pg, 700)
        await pg.keyboard.press("Enter")
        await pause(pg, 2600)
        await pg.keyboard.press("Escape")
        await pause(pg, 600)

        # 5. Scrum
        await caption(pg, "Scrum: sprint, backlog, burndown và velocity")
        await pg.click('[data-testid="open-scrum"]')
        await pause(pg, 2000)
        for tab in ["PLANNING", "BURNDOWN", "VELOCITY"]:
            await pg.click(f'[data-tab="{tab}"]')
            await pause(pg, 2400)
        await pg.keyboard.press("Escape")
        await pause(pg, 600)

        # 6. AI weekly summary (a real model answers — Groq)
        await caption(pg, "AI tóm tắt tiến độ tuần và chỉ ra điểm nghẽn")
        await pg.get_by_role("button", name="AI Tools").click()
        await pause(pg, 600)
        await pg.locator("button", has_text="Weekly").first.click()
        await pg.wait_for_timeout(9000)
        await pg.keyboard.press("Escape")
        await pause(pg, 500)

        # 7. DAG
        await caption(pg, "Đồ thị phụ thuộc và đường găng (critical path)")
        await pg.keyboard.press("v")
        await pause(pg, 3500)
        await pg.keyboard.press("Escape")
        await caption(pg, "Koshi — dùng thử miễn phí")
        await pause(pg, 2500)

        await cdp.send("Page.stopScreencast")
        # The screencast only emits a frame when something changes, so each
        # frame is held until the next one — an ffconcat list with durations.
        with open(f"{OUT}/frames.txt", "w") as fh:
            fh.write("ffconcat version 1.0\n")
            for (t, name), nxt in zip(frames, frames[1:] + [(frames[-1][0] + 1.0, None)]):
                fh.write(f"file '{os.path.basename(name)}'\nduration {max(nxt[0] - t, 0.001):.3f}\n")
            fh.write(f"file '{os.path.basename(frames[-1][1])}'\n")
        await ctx.close()
        await browser.close()
    print(f"recorded {len(frames)} frames to {OUT}")


asyncio.run(main())
