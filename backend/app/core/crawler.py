# 무신사 검색 결과 크롤링 및 스크린샷 저장
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime

class MusinsaCrawler:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options = chrome_options
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), "../screenshot")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def fetch_and_screenshot(self, keyword: str) -> Optional[str]:
        url = f"https://www.musinsa.com/search/goods?keyword={keyword}&keywordType=keyword&gf=M"
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
        try:
            driver.set_window_size(1280, 2000)
            driver.get(url)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_keyword = keyword.replace("/", "_")
            screenshot_path = os.path.join(self.screenshot_dir, f"{safe_keyword}_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            print(f"[크롤러] {keyword} 검색 결과 스크린샷 저장: {screenshot_path}")
            # API 엔드포인트와 일치하는 경로 반환
            return f"/screenshot/{safe_keyword}_{timestamp}.png"
        except Exception as e:
            print(f"[크롤러] 스크린샷 실패: {e}")
            return None
        finally:
            driver.quit() 