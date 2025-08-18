import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import time
import re

def safe_get(driver, url, wait_time=10):
    """
    打开页面并等待加载完成（使用 WebDriverWait 替代 time.sleep）
    :param driver: Selenium driver
    :param url: 要访问的链接
    :param wait_time: 最大等待秒数
    """
    print(f"[INFO] 正在访问页面：{url}")
    driver.get(url)
    try:
        # 等待 <body> 元素加载完成
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("[INFO] 页面加载完成")
    except TimeoutException:
        print("[WARN] 页面加载超时，可能内容不完整")


def convert_cookies(input_file):
    """读取 cookies.txt 并返回列表"""
    print(f"[INFO] 正在读取 Cookie 文件：{input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        cookie_string = f.read().strip()
    return [
        {
            "name": name.strip(),
            "value": value.strip(),
            "domain": ".pixiv.net",
            "path": "/"
        }
        for name, value in (entry.split('=', 1) for entry in cookie_string.split('; '))
    ]


def sanitize_filename(filename):
    """去除文件名非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", filename)[:32]

def get_chapter_text(driver, chapter_url, novel_title=""):
    """获取单章正文"""
    safe_get(driver, chapter_url)
    if not novel_title:
        novel_title = driver.find_element(By.CLASS_NAME, 'sc-d4cbc2e2-3.jRicjE').text.strip()
    print(f"[INFO] 正在获取章节内容：{novel_title}")
    spans = driver.find_elements(By.CSS_SELECTOR, 'p.sc-dAbbOL.kwpKEA span.text-count')
    texts = [span.text.strip() for span in spans if span.text.strip() and span.text.strip() != '…']
    return '\n'.join(texts)


def save_text(folder_path, index, title, text):
    """保存章节内容到文件"""
    safe_title = sanitize_filename(title)
    filename = os.path.join(folder_path, f"{index:04d}_{safe_title}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"[SAVE] 已保存章节：{filename}")


def get_series_text(driver, series_url, folder_path):
    """获取系列所有章节"""
    print("[INFO] 开始获取系列章节列表...")
    safe_get(driver, series_url)
    li_elements = driver.find_elements(By.CSS_SELECTOR, 'li.sc-72a2a0c5-2.bdsPlW')
    urls = [li.find_element(By.TAG_NAME, "a").get_attribute("href") for li in li_elements]
    titles = [li.find_elements(By.TAG_NAME, "a")[1].text.strip() for li in li_elements]
    print(f"[INFO] 共检测到 {len(urls)} 章")
    for index, (url, title) in enumerate(zip(urls, titles), start=1):
        chapter_text = get_chapter_text(driver, url, title)
        save_text(folder_path, index, title, chapter_text)
    print("[INFO] 系列章节下载完成！")


def create_folder(path, title):
    """创建小说文件夹"""
    folder_path = os.path.join(path, sanitize_filename(title))
    os.makedirs(folder_path, exist_ok=True)
    print(f"[FOLDER] 小说目录已创建：{folder_path}")
    return folder_path


def get_novel_text(driver, url, tag, title):
    """根据类型获取小说"""
    folder_path = create_folder("novels", title)
    if tag == "chapter":
        print("[INFO] 检测到单章模式，开始下载...")
        chapter_text = get_chapter_text(driver, url, title)
        save_text(folder_path, 1, title, chapter_text)
    elif tag == "series":
        print("[INFO] 检测到系列模式，开始下载...")
        get_series_text(driver, url, folder_path)


def is_chapter_or_series(driver, novel_id):
    """判断是单章还是系列"""
    chapter_url = f"https://www.pixiv.net/novel/show.php?id={novel_id}"
    safe_get(driver, chapter_url)
    novel_title = driver.find_element(By.CSS_SELECTOR, 'h1.sc-d4cbc2e2-3.jRicjE').text.strip()

    try:
        # series_element = WebDriverWait(driver, 5).until(
        #     EC.presence_of_element_located(
        #         (By.CSS_SELECTOR, 'a.sc-26a75719-3.enzfvB.gtm-novel-work-series-detail')
        #     )
        # )
        series_element = driver.find_element(By.CSS_SELECTOR, 'a.sc-26a75719-3.enzfvB.gtm-novel-work-series-detail')
        print(f"[INFO] 检测到系列标签: {series_element.text}")
        get_novel_text(driver, series_element.get_attribute("href"), "series", series_element.text)
    except (TimeoutException, NoSuchElementException):
        print(f"[INFO] 未检测到系列标签，作为单章处理: {novel_title}")
        get_novel_text(driver, chapter_url, "chapter", novel_title)


def set_driver():
    """初始化 driver"""
    print("[INFO] 正在启动浏览器...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('lang=zh_CN.UTF-8')
    options.add_argument('--disable-gpu')
    options.add_argument('--blink-settings=imagesEnabled=False')
    return uc.Chrome(options=options)


def load_cookies(driver, cookies):
    """加载 cookie"""
    print("[INFO] 正在加载 Cookie...")
    driver.get("https://www.pixiv.net")
    for cookie in cookies:
        driver.add_cookie(cookie)
    print("[INFO] Cookie 加载完成")

def process_by_file(driver, filename):
    
    # 读取文件并解析成数字列表
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # 判断分隔符
    if "\n" in content:
        novel_ids = content.splitlines()
        sep = "\n"
    else:
        novel_ids = content.split()
        sep = " "

    while novel_ids:
        novel_id = novel_ids[0]  # 取第一个
        start_time = time.time()
        is_chapter_or_series(driver, novel_id)
        print(f"[DONE] 本次用时: {time.time() - start_time:.2f} 秒")
        novel_ids.pop(0)  # 处理完成后从列表移除

        # 把剩余数字写回文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(sep.join(novel_ids))



if __name__ == "__main__":
    driver = set_driver()
    cookies = convert_cookies("cookies.txt")
    load_cookies(driver, cookies)
    try:
        # while True:
            # start_time = time.time()
            # novel_id = input("\n请输入小说id（直接回车退出）：").strip()
            # if not novel_id:
            #     print("[EXIT] 退出程序")
            #     break
            # is_chapter_or_series(driver, novel_id)
            # print(f"[DONE] 本次用时: {time.time() - start_time:.2f} 秒")
        process_by_file(driver, "id.txt")
    except KeyboardInterrupt:
        print("\n[EXIT] 手动中断程序")
    finally:
        driver.quit()
        print("[INFO] 浏览器已关闭")
