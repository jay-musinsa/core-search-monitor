# 무신사 검색 결과 크롤링 및 스크린샷 저장
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class BaseCrawler(ABC):
    def __init__(self, platform: str):
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), f"../screenshot/{platform}")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    @abstractmethod
    def fetch_and_screenshot(self, keyword: str) -> Optional[str]:
        pass


class CrawlerMusinsa(BaseCrawler):
    def __init__(self):
        self.platform = "musinsa"
        super().__init__(self.platform)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options = chrome_options

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
            return f"/screenshot/{self.platform}/{safe_keyword}_{timestamp}.png"
        except Exception as e:
            print(f"[크롤러] 스크린샷 실패: {e}")
            return None
        finally:
            driver.quit()


class Crawler29CM(BaseCrawler):
    def __init__(self):
        self.platform = "29cm"
        super().__init__(self.platform)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options = chrome_options

    def fetch_and_screenshot(self, keyword: str) -> Optional[str]:
        url = f"https://shop.29cm.co.kr/search?keyword={keyword}"
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
        try:
            driver.set_window_size(1280, 2000)
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-bar"))
                )
            except Exception as e:
                print(f"[크롤러] 로딩바 사라짐 대기 중 예외: {e}")

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-list__item"))
                )
            except Exception as e:
                print(f"[크롤러] 검색 결과 대기 중 예외: {e}")

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_keyword = keyword.replace("/", "_")
            screenshot_path = os.path.join(self.screenshot_dir, f"{safe_keyword}_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            print(f"[크롤러] {keyword} 검색 결과 스크린샷 저장: {screenshot_path}")
            return f"/screenshot/{self.platform}/{safe_keyword}_{timestamp}.png"
        except Exception as e:
            print(f"[크롤러] 스크린샷 실패: {e}")
            return None
        finally:
            driver.quit()
