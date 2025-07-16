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
        
        # Chrome 옵션 공통 설정
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1280,1024')
        self.chrome_options.add_argument('--disable-web-security')
        self.chrome_options.add_argument('--allow-running-insecure-content')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')  # 이미지 로딩 비활성화로 속도 향상
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    @abstractmethod
    def capture_screenshot(self, keyword: str) -> Optional[str]:
        """키워드로 검색 페이지 스크린샷 캡처"""
        pass

    def capture_full_page_screenshot(self, driver: webdriver.Chrome, screenshot_path: str) -> bool:
        """전체 페이지 스크린샷 캡처"""
        try:
            print(f"[크롤러] 전체 페이지 스크린샷 시작: {screenshot_path}")
            
            # 페이지 로딩 완료 대기
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print(f"[크롤러] 페이지 로딩 완료")
            
            # 추가 로딩 대기 (동적 콘텐츠)
            import time
            time.sleep(2)
            print(f"[크롤러] 추가 로딩 대기 완료")
            
            # 전체 페이지 높이 계산
            total_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            print(f"[크롤러] 페이지 높이: {total_height}, 뷰포트 높이: {viewport_height}")
            
            # 창 크기를 전체 페이지에 맞게 조정
            driver.set_window_size(1280, total_height)
            print(f"[크롤러] 창 크기 조정: 1280x{total_height}")
            
            # 페이지가 완전히 로드될 때까지 대기
            time.sleep(1)
            
            # 전체 페이지 스크린샷 캡처
            driver.save_screenshot(screenshot_path)
            
            # 파일이 실제로 생성되었는지 확인
            if os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                print(f"[크롤러] 전체 페이지 스크린샷 캡처 완료: {screenshot_path}")
                print(f"[크롤러] 파일 크기: {file_size} bytes")
                return True
            else:
                print(f"[크롤러] 스크린샷 파일이 생성되지 않음: {screenshot_path}")
                return False
            
        except Exception as e:
            print(f"[크롤러] 전체 페이지 스크린샷 캡처 실패: {e}")
            import traceback
            print(f"[크롤러] 상세 에러: {traceback.format_exc()}")
            return False


class CrawlerMusinsa(BaseCrawler):
    def __init__(self):
        self.platform = "musinsa"
        super().__init__(self.platform)
        # self.chrome_options = Options() # BaseCrawler에서 이미 설정되어 있으므로 중복 설정 제거

    def capture_screenshot(self, keyword: str) -> Optional[str]:
        """무신사 검색 페이지 스크린샷 캡처"""
        url = f"https://www.musinsa.com/search/goods?keyword={keyword}&keywordType=keyword&gf=M"
        
        try:
            # ChromeDriver 서비스 설정
            service = Service(ChromeDriverManager().install())
            print(f"[크롤러] ChromeDriver 경로: {service.path}")
            
            # macOS에서 Chrome 경로 명시적 지정
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                self.chrome_options.binary_location = chrome_path
                print(f"[크롤러] Chrome 경로 설정: {chrome_path}")
            
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            print(f"[크롤러] Chrome 드라이버 생성 성공")
            
        except Exception as e:
            print(f"[크롤러] Chrome 드라이버 생성 실패: {e}")
            return None
        
        try:
            print(f"[크롤러] 무신사 스크린샷 시작: {keyword}")
            print(f"[크롤러] URL: {url}")
            driver.get(url)
            
            # 검색 결과 로딩 대기
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".list-item"))
                )
                print(f"[크롤러] 무신사 검색 결과 로딩 완료: {keyword}")
            except Exception as e:
                print(f"[크롤러] 무신사 검색 결과 대기 중 예외: {e}")
                print(f"[크롤러] 현재 페이지 제목: {driver.title}")
                print(f"[크롤러] 현재 URL: {driver.current_url}")
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_keyword = keyword.replace("/", "_").replace(" ", "_")
            screenshot_path = os.path.join(self.screenshot_dir, f"{safe_keyword}_{timestamp}.png")
            
            print(f"[크롤러] 스크린샷 저장 경로: {screenshot_path}")
            
            # 전체 페이지 스크린샷 캡처
            if self.capture_full_page_screenshot(driver, screenshot_path):
                relative_path = f"/screenshot/{self.platform}/{safe_keyword}_{timestamp}.png"
                print(f"[크롤러] 무신사 스크린샷 성공: {relative_path}")
                return relative_path
            else:
                print(f"[크롤러] 무신사 스크린샷 캡처 실패: {keyword}")
                return None
                
        except Exception as e:
            print(f"[크롤러] 무신사 스크린샷 실패: {e}")
            import traceback
            print(f"[크롤러] 상세 에러: {traceback.format_exc()}")
            return None
        finally:
            try:
                driver.quit()
                print(f"[크롤러] 무신사 드라이버 종료: {keyword}")
            except Exception as e:
                print(f"[크롤러] 드라이버 종료 실패: {e}")


class Crawler29CM(BaseCrawler):
    def __init__(self):
        self.platform = "29cm"
        super().__init__(self.platform)
        # self.chrome_options = Options() # BaseCrawler에서 이미 설정되어 있으므로 중복 설정 제거

    def capture_screenshot(self, keyword: str) -> Optional[str]:
        """29cm 검색 페이지 스크린샷 캡처"""
        url = f"https://shop.29cm.co.kr/search?keyword={keyword}"
        
        try:
            # ChromeDriver 서비스 설정
            service = Service(ChromeDriverManager().install())
            print(f"[크롤러] ChromeDriver 경로: {service.path}")
            
            # macOS에서 Chrome 경로 명시적 지정
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                self.chrome_options.binary_location = chrome_path
                print(f"[크롤러] Chrome 경로 설정: {chrome_path}")
            
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            print(f"[크롤러] Chrome 드라이버 생성 성공")
            
        except Exception as e:
            print(f"[크롤러] Chrome 드라이버 생성 실패: {e}")
            return None
        
        try:
            print(f"[크롤러] 29cm 스크린샷 시작: {keyword}")
            print(f"[크롤러] URL: {url}")
            driver.get(url)

            # 로딩바 사라짐 대기
            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-bar"))
                )
                print(f"[크롤러] 29cm 로딩바 사라짐: {keyword}")
            except Exception as e:
                print(f"[크롤러] 29cm 로딩바 대기 중 예외: {e}")
                print(f"[크롤러] 현재 페이지 제목: {driver.title}")
                print(f"[크롤러] 현재 URL: {driver.current_url}")

            # 검색 결과 로딩 대기
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-list__item"))
                )
                print(f"[크롤러] 29cm 검색 결과 로딩 완료: {keyword}")
            except Exception as e:
                print(f"[크롤러] 29cm 검색 결과 대기 중 예외: {e}")
                print(f"[크롤러] 현재 페이지 제목: {driver.title}")
                print(f"[크롤러] 현재 URL: {driver.current_url}")

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_keyword = keyword.replace("/", "_").replace(" ", "_")
            screenshot_path = os.path.join(self.screenshot_dir, f"{safe_keyword}_{timestamp}.png")
            
            print(f"[크롤러] 스크린샷 저장 경로: {screenshot_path}")
            
            # 전체 페이지 스크린샷 캡처
            if self.capture_full_page_screenshot(driver, screenshot_path):
                relative_path = f"/screenshot/{self.platform}/{safe_keyword}_{timestamp}.png"
                print(f"[크롤러] 29cm 스크린샷 성공: {relative_path}")
                return relative_path
            else:
                print(f"[크롤러] 29cm 스크린샷 캡처 실패: {keyword}")
                return None
                
        except Exception as e:
            print(f"[크롤러] 29cm 스크린샷 실패: {e}")
            import traceback
            print(f"[크롤러] 상세 에러: {traceback.format_exc()}")
            return None
        finally:
            try:
                driver.quit()
                print(f"[크롤러] 29cm 드라이버 종료: {keyword}")
            except Exception as e:
                print(f"[크롤러] 드라이버 종료 실패: {e}")
