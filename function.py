import re
import chardet
import os

def read_file_auto(filepath):
    # 自动检测编码
    with open(filepath, 'rb') as f:
        raw = f.read(100000)  # 最多读取 100KB
    result = chardet.detect(raw)
    encoding = result['encoding'] or 'utf-8'
    
    # 读取文件内容
    with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
        return f.read()

def split_chapters(text):
    pattern = re.compile(r'(第[一二三四五六七八九十百千万0-9]+章.*?)\n')
    matches = list(pattern.finditer(text))

    if not matches:
        # 如果没有匹配到章节标题，就整本作为一个章节返回
        return [{
            'title': '全文',
            'content': text.strip()
        }]

    chapters = []
    for i in range(len(matches)):
        start = matches[i].end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = matches[i].group(1)
        content = text[start:end].strip('\n')
        chapters.append({
            'title': title,
            'content': content
        })

    return chapters

def split_novel_by_chapter(file_path, novel_folder):
    """
    将上传的txt小说按章节分割并保存到以小说标题命名的文件夹中。

    :param file_path: 上传的小说文件路径
    :param novel_folder: 存放小说的根目录
    :return: 分割后的章节文件路径列表
    """
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # 如果 utf-8 失败，尝试 gbk（中文常见编码）
        with open(file_path, 'r', encoding='gbk') as f:
            content = f.read()

    # 使用正则匹配章节标题，支持多种格式
    chapter_pattern = re.compile(
        r'(第[一二三四五六七八九十百千0-9]+[章回集节]\s*.*)',
        re.IGNORECASE | re.MULTILINE
    )

    # 找到所有章节标题和位置
    chapters = [(match.group(1).strip(), match.start()) for match in chapter_pattern.finditer(content)]

    if not chapters:
        raise ValueError("未能识别出任何章节，请确保小说以“第X章”等格式分章。")

    # 获取小说标题（去掉路径和 .txt 后缀）
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]

    # 创建小说标题命名的文件夹
    book_folder = os.path.join(novel_folder, title)
    os.makedirs(book_folder, exist_ok=True)

    # 保存章节文件路径列表
    saved_files = []

    # 遍历章节，切分内容并保存
    for i, (chapter_title, start_pos) in enumerate(chapters):
        # 下一章的起始位置，或文件末尾
        end_pos = chapters[i + 1][1] if i + 1 < len(chapters) else len(content)

        # 提取章节内容（包含标题）
        chapter_content = content[start_pos:end_pos].strip()

        # 构造安全的文件名（避免特殊字符）
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', chapter_title)
        safe_title = safe_title[:50]  # 限制长度
        chapter_filename = f"{i:04d}_{safe_title}.txt"
        chapter_path = os.path.join(book_folder, chapter_filename)

        with open(chapter_path, 'w', encoding='utf-8') as cf:
            cf.write(chapter_content)

        saved_files.append(chapter_path)

    return saved_files