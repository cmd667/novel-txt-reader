import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import re

def get_page_text(driver, curr_url):
    """
    Purpose: 获取本页小说内容
    """
    driver.get(curr_url)
    nr1_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "nr1"))
    )
    html = nr1_element.get_attribute("innerHTML")
    # 删除 HTML 原本的换行符
    html = html.replace("\n", "")

    soup = BeautifulSoup(html, 'html.parser')

    # 去掉分页区块和提示内容
    for tag in soup.select("center.chapterPages, font, br+center"):
        tag.decompose()    
    
    # 将所有 <br> 替换成换行
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # 提取纯文本
    raw_text = soup.get_text()
    # with open("raw.txt",'w',encoding='utf-8') as f:
    #     f.write(raw_text)
    # 根据规则：删除换行符后面紧跟文字的情况
    cleaned_text = re.sub(r'\n(?=\S)', '', raw_text)
    cleaned_text = re.sub(r'\n(?=\S)', '', cleaned_text)
    # with open("cl.txt",'w',encoding='utf-8') as f:
    #     f.write(cleaned_text.strip())
    # exit()
    return cleaned_text.strip()
# end def

def get_chapter_text(driver, chapter_url):
    """
    Purpose:整合小说分页内容，单章保存 
    """
    print("正在加载章节...")
    driver.get(chapter_url)
    # time.sleep(1)
    # 获取章节名
    chapter_title = driver.find_element(By.CSS_SELECTOR, "h1.page-title").text

    chapter = []
    page_count = 1
    urls = []
    
    # 查找所有分页链接，填入后续页的文本
    page_links = driver.find_elements(By.CSS_SELECTOR, "center.chapterPages a")

    # 由于后续会跳转页面，此处生成urls数组备用
    urls.append(chapter_url)
    for page_link in page_links:
        urls.append(page_link.get_attribute("href"))
    for url in urls:
        chapter.append(get_page_text(driver, url)) # 获取内容
        print(f"获取章节 {chapter_title} 页数:{page_count}")
        page_count += 1
    return chapter
# end def

def get_novel_by_catalog(driver, catalog_url):
    """
    Purpose: 根据目录获取所有章节
    """
    print("正在加载目录...")
    driver.get(catalog_url)
    time.sleep(2)
    # driver.save_screenshot('diyibanzhu.png')
    # 获取小说标题（在 <h1> 中）
    try:
        novel_title = driver.find_element(By.CSS_SELECTOR, "div.right h1").text 
        print("获取小说：" + novel_title)
    except Exception as e:
        print("❌ 无法获取小说标题:", e)
        return    
    # 创建以小说标题为名的文件夹
    folder_path = os.path.join("novels", novel_title)
    os.makedirs(folder_path, exist_ok=True)
    print(f"📁 小说目录已创建：{folder_path}")
    # 从目录获取全部目录分页
    # 定位select标签
    select_element = driver.find_element(By.CSS_SELECTOR, 'select[name="pagelist"]')
    # 找到所有option标签，提取value属性
    option_elements = select_element.find_elements(By.TAG_NAME, "option")
    option_links = [option.get_attribute("value") for option in option_elements]

    index = 1
    for link in option_links:
        driver.get(f"https://m.diyibanzhu.space/{link}")
        # 章节链接位于 ul.list li a 中
        chapter_list_div = driver.find_elements(By.CSS_SELECTOR, "div.mod.block.update.chapter-list")
        if len(chapter_list_div) == 2:
            chapter_links = chapter_list_div[1].find_elements(By.CSS_SELECTOR, "ul.list li a")
        else:
            chapter_links = chapter_list_div[0].find_elements(By.CSS_SELECTOR, "ul.list li a")
        
        # 按照所有目录分页，制作chapter_urls
        chapter_urls = []
        for chapter_link in chapter_links:
            chapter_urls.append(chapter_link.get_attribute("href"))
        # 读取每章内容
        for chapter_url in chapter_urls:
            chapter_text = get_chapter_text(driver, chapter_url)
            chapter_title = driver.find_element(By.CSS_SELECTOR, "div.container h1").text
            safe_title = re.sub(r'[\\/:*?"<>|]', '', chapter_title).strip() 
            filename = os.path.join(folder_path, f"{index:04d}_{safe_title}.txt")
            with open(filename, 'w', encoding='UTF-8') as f:
                for page_text in chapter_text:
                    f.write(page_text)
            print(f"✅ 已保存章节：{filename}")
            f.close()
            index += 1
# end def

if __name__ == "__main__":

    # chapter_url = 'https://m.diyibanzhu.space/view/777076.html'
    # catalog_url = 'https://m.diyibanzhu.space/list/12170.html'

    options = uc.ChromeOptions()
    options.add_argument('--headless') # 无头模式
    options.add_argument('lang=zh_CN.UTF-8') # 中文
    options.add_argument('--disable-gpu') # 禁用gpu加速
    options.add_argument('--blink-settings=imagesEnabled=False') # 禁止加载图片，降低性能需求

    driver = uc.Chrome(options=options)
    
    try:
        while True:
            novel_id = input("请输入小说目录id（直接回车退出）：").strip()
            if not novel_id:
                print("退出程序")
                break
            catalog_url = f'https://m.diyibanzhu.space/list/{novel_id}.html'
            get_novel_by_catalog(driver, catalog_url)
    except KeyboardInterrupt:
        print("\n手动中断程序")
    finally:
        driver.quit()