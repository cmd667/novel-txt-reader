from flask import Flask, render_template, abort, redirect, url_for, request, flash
import os
from markupsafe import Markup
from function import split_chapters, read_file_auto, split_novel_by_chapter
import shutil

app = Flask(__name__)
NOVEL_FOLDER = 'novels'  # 定义小说文件存储的文件夹路径
app.secret_key = os.urandom(24)  # 设置Flask应用的密钥用于session加密

from flask import request

@app.route('/')
def index():
    # 获取小说文件夹列表（忽略非目录）
    folders = [f for f in os.listdir(NOVEL_FOLDER) if os.path.isdir(os.path.join(NOVEL_FOLDER, f))]
    novels = [{'filename': f, 'title': f} for f in sorted(folders)]

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 20
    total = len(novels)

    start = (page - 1) * per_page
    end = start + per_page
    novels_paginated = novels[start:end]

    total_pages = (total + per_page - 1) // per_page  # 向上取整

    return render_template(
        'index.html',
        novels=novels_paginated,
        page=page,
        total_pages=total_pages
    )


@app.route('/view/<novel_name>/toc')
def view_toc(novel_name):
    # 小说所在的目录
    novel_dir = os.path.join(NOVEL_FOLDER, novel_name)
    if not os.path.isdir(novel_dir):
        abort(404)

    # 获取所有章节文件并排序
    chapter_files = sorted(os.listdir(novel_dir))

    # 生成章节标题（去掉编号）
    chapter_titles = [os.path.splitext(f)[0].split('_', 2)[-1] for f in chapter_files]

    return render_template(
        'toc.html',
        title=novel_name,
        filename=novel_name,
        chapter_titles=chapter_titles
    )

@app.route('/view/<novel_name>/chapter/<int:chapter_index>')
def view_chapter(novel_name, chapter_index):
    # 拼接小说目录路径
    novel_dir = os.path.join(NOVEL_FOLDER, novel_name)
    # 如果小说目录不存在，返回404错误
    if not os.path.isdir(novel_dir):
        abort(404)

    # 获取该小说目录下所有章节文件名，排序保证顺序一致
    chapter_files = sorted(os.listdir(novel_dir))

    # 检查传入的章节索引是否合法（不能超出文件列表范围）
    if chapter_index < 0 or chapter_index >= len(chapter_files):
        abort(404)

    # 获取当前章节对应的文件名和完整路径
    current_chapter_file = chapter_files[chapter_index]
    filepath = os.path.join(novel_dir, current_chapter_file)

    # 读取当前章节文件内容，使用utf-8编码
    with open(filepath, 'r', encoding='utf-8') as f:
        chapter_content = f.read()

    # 从所有章节文件名中提取章节标题（假设文件名格式带编号和标题，中间用下划线分割）
    chapter_titles = [os.path.splitext(f)[0].split('_', 2)[-1] for f in chapter_files]
    # 当前章节标题
    chapter_title = chapter_titles[chapter_index]

    # 从URL参数获取分页页码，默认是第一页
    page = request.args.get('page', '1')
    try:
        page = int(page)
    except ValueError:
        # 如果页码不是整数，默认第一页
        page = 1

    # 把章节内容按换行拆成段落，并去除空白段落
    paragraphs = [p for p in chapter_content.split('\n') if p.strip()]

    # 每页显示的段落数
    paragraphs_per_page = 40
    # 计算总页数（向上取整）
    total_pages = (len(paragraphs) + paragraphs_per_page - 1) // paragraphs_per_page

    # 保证页码在合理范围内
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    # 计算当前页的段落范围索引
    start = (page - 1) * paragraphs_per_page
    end = start + paragraphs_per_page
    # 当前页要显示的段落列表
    page_paragraphs = paragraphs[start:end]

    # 渲染模板，传递所需数据
    return render_template(
        'view.html',
        title=novel_name,              # 小说名（用于显示或SEO）
        chapter_index=chapter_index,  # 当前章节索引
        chapter_count=len(chapter_files),  # 章节总数
        filename=novel_name,           # 用于url_for构建链接
        chapter_title=chapter_title,   # 当前章节标题
        chapter_titles=chapter_titles, # 所有章节标题（目录用）
        page_paragraphs=page_paragraphs, # 当前分页显示的段落
        current_page=page,             # 当前页码
        total_pages=total_pages        # 总页数
    )

import shutil  # 用于删除整个文件夹

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('novel')
    if file and file.filename.endswith('.txt'):
        # 小说名（去掉扩展名）
        novel_name = os.path.splitext(file.filename)[0]
        novel_dir = os.path.join(NOVEL_FOLDER, novel_name)
        os.makedirs(novel_dir, exist_ok=True)

        save_path = os.path.join(novel_dir, file.filename)
        file.save(save_path)

        try:
            # 调用分章节函数（改为存放到 novel_dir）
            chapter_files = split_novel_by_chapter(save_path, novel_dir)
            flash(f'上传成功！共分割出 {len(chapter_files)} 个章节。')
        except Exception as e:
            flash(f'上传成功，但分章节失败：{str(e)}')

        # 删除原始整本文件
        os.remove(save_path)
    else:
        flash('只支持 .txt 文件上传')
    return redirect(url_for('manage'))

# 删除整本小说（文件夹）
@app.route('/delete/<novel_name>', methods=['POST'])
def delete(novel_name):
    safe_name = os.path.basename(novel_name)  # 确保安全
    novel_path = os.path.join(NOVEL_FOLDER, safe_name)
    if os.path.exists(novel_path) and os.path.isdir(novel_path):
        shutil.rmtree(novel_path)  # 删除整个小说文件夹
        flash('删除成功')
    else:
        flash('小说不存在')
    return redirect(url_for('manage'))

# 管理页面
@app.route('/manage')
def manage():
    # 获取小说目录（只取文件夹）
    novels = []
    for name in os.listdir(NOVEL_FOLDER):
        dir_path = os.path.join(NOVEL_FOLDER, name)
        if os.path.isdir(dir_path):
            novels.append({'filename': name, 'title': name})
    return render_template('manage.html', novels=novels)

# 重命名小说文件夹
@app.route('/rename', methods=['POST'])
def rename():
    old_name = request.form.get('old_filename', '').strip()
    new_name = request.form.get('new_name', '').strip()

    if not old_name or not new_name:
        flash("重命名信息不完整")
        return redirect(url_for('manage'))

    old_path = os.path.join(NOVEL_FOLDER, os.path.basename(old_name))
    new_path = os.path.join(NOVEL_FOLDER, os.path.basename(new_name))

    if not os.path.exists(old_path):
        flash("原文件夹不存在")
    elif os.path.exists(new_path):
        flash("新小说名已存在")
    else:
        os.rename(old_path, new_path)
        flash("重命名成功")
    return redirect(url_for('manage'))

if __name__ == '__main__':
    os.makedirs(NOVEL_FOLDER, exist_ok=True)  # 创建小说文件夹（如果不存在）
    app.run(host='0.0.0.0', port=5000, debug=True)  # 启动Flask应用
