# -*- coding: utf-8 -*-

import json
import platform
import os
import sys
# from workflow import Workflow3  # https://github.com/deanishe/alfred-workflow
import subprocess
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from fuzzywuzzy import fuzz  # similarity
from fuzzywuzzy import process
from ripgrepy import Ripgrepy

project_path = '/Users/mac/working_dirs/snippets_lab/'


def debug_file(content):
    with open('/Users/mac/alfred_py_debug.log', 'a') as f:
        f.write(str(content) + '\n')


# 获取输入的多个参数
def parse_args(argv):
    args = {}
    debug_file('here')
    _ = argv[0]
    # determine search mode
    if _ == "--tag":
        args["mode"] = "tag"
    else:
        args["mode"] = "text"
    debug_file(argv)
    # parsing query arguments
    arg1 = argv[1]
    query_args = arg1.split()
    # 多个tag，按照and关系搜索
    # 多个keyword，按照and关系搜索
    args["search_condition"] = query_args
    debug_file(args)
    return args


def to_alfred(res_list):
    # print(res_list)
    if not res_list[0]:
        items = Element('items')
        item = SubElement(items, 'item')
        item.set('arg', res_list[1].get('res'))
        item.set('valid', 'yes')
        title = SubElement(item, 'title')
        title.text = res_list[1].get('res')
        subtitle = SubElement(item, 'subtitle')
        subtitle.text = ','.join(res_list[1].get('subtitle'))
    elif res_list[0]==1:
        items = Element('items')
        for x in res_list[1]:
            item = SubElement(items, 'item')
            item.set('arg', x.get('res'))
            item.set('valid', 'yes')
            title = SubElement(item, 'title')
            title.text = x.get('res')
            subtitle = SubElement(item, 'subtitle')
            subtitle.text = ','.join(x.get('subtitle'))
        debug_file('items is %s' % tostring(items))
    else:
        items = Element('items')
        # print(res_list[1])
        for x in res_list[1]:
            item = SubElement(items, 'item')
            # print(type(x))
            # print(x)
            # print(x.get('data'))
            item.set('arg', x.get('data').get('path').get('text'))
            item.set('valid', 'yes')
            title = SubElement(item, 'title')
            title.text = x.get('data').get('lines').get('text')
            subtitle = SubElement(item, 'subtitle')
            subtitle.text = x.get('data').get('path').get('text')
        debug_file('items is %s' % tostring(items))
    return tostring(items)


def get_tag_command_result(tag_dir):
    # tag命令不能用部分匹配
    # brew install tag
    p = subprocess.Popen("/usr/local/bin/tag -tgf \* -R %s" % tag_dir, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, executable='/bin/bash')
    output, error = p.communicate()
    return output.decode('utf-8').split('\n')[:-1]


def get_rg_command_result(key_words):
    # rg命令不能指定路径参数
    # brew install rg
    # from ripgrepy import Ripgrepy , 只支持py3.7+
    debug_file('keywords passed %s' % key_words)
    # debug_file(os.popen('cd %s;/usr/local/bin/rg %s > ./rg_result.log' % (project_path, key_words)).read())
    # rg命令的结果无法通过subprocess获取
    # p = subprocess.Popen("cd /Users/mac/working_dirs/snippets_lab; grep -R tet *", shell=True,
    #                      stdout=subprocess.PIPE,
    #                      stderr=subprocess.STDOUT, executable='/bin/bash')
    # rg = Ripgrepy('{}.*'.format(key_words), '{}'.format(project_path))
    rg = Ripgrepy(key_words, project_path).json().run()
    debug_file('output is %s' % rg)
    return rg.as_dict()


def search_tag(tags):
    global flag
    tags_and_files = []

    tag_dir = project_path
    res_to_process = get_tag_command_result(tag_dir)

    group_index = grouped_index(res_to_process)
    # print(group_index)
    if not group_index:
        flag = 0  # 没有结果
        return flag, {'res': 'no res', 'subtitle': tags}
    else:
        flag = 1
        grouped_res = [res_to_process[group_index[i]:group_index[i + 1]] for i in range(0, len(group_index) - 1)]
        grouped_res += [res_to_process[group_index[-1]:]]
        for e in grouped_res:
            res = {'res': e[0], 'subtitle': [x.strip() for x in e[1:]]}
            tags_and_files.append(res)
        debug_file('tag_res is %s' % tags_and_files)

        # print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        debug_file('tags is %s' % tags)
        all_tags = []
        for e in tags_and_files:
            # print 'e is ', e
            all_tags.append(e.get('subtitle'))
        if not filtered_by_similarity(tags, all_tags, tags_and_files):
            flag = 0  # 没有结果
            return flag, {'res': 'no res', 'subtitle': tags}
        else:
            flag = 1
            return flag, filtered_by_similarity(tags, all_tags, tags_and_files)


def filtered_by_similarity(tags, all_tags, before_filtered):
    similarity = process.extract(tags[0], all_tags)
    # print(similarity)
    similarity_filtered_res = []
    for tag in similarity:
        if tag[1] > 50:
            similarity_filtered_res.append(before_filtered[similarity.index(tag)])

    return similarity_filtered_res


def grouped_index(data):
    grouped_data = []

    for i, e in enumerate(data):
        if '/' in e:
            grouped_data.append(i)
    debug_file('group index is %s' % grouped_data)
    return grouped_data


def search_text(text):
    global flag
    # 关键字搜索时，输入完之后再执行搜索，避免返回结果过多
    # 关键字之后加一个空格，表示输入完成
    debug_file('xxx')
    debug_file('keywords is %s ' % text)
    debug_file('end is %s' % text[0][-1])
    if text[0][-1] == '-':
        res_to_process = get_rg_command_result(text[0][:-1])
        debug_file(res_to_process)

        if not res_to_process:
            flag = 0  # 没有结果
            return flag, {'res': 'no res', 'subtitle': text}
        else:
            flag = 2
            return flag, res_to_process
    else:
        flag = 0  # 没有结果
        return flag, {'res': 'searching ...', 'subtitle': text}


def search_filename():
    pass


def main():
    global results
    sys_args = sys.argv[1:]
    valid_args = parse_args(sys_args)
    debug_file(str(valid_args))
    debug_file('====================')

    if valid_args['mode'] == 'tag':
        results = search_tag(valid_args['search_condition'])
    elif valid_args["mode"] == "text":
        results = search_text(valid_args['search_condition'])
    print(to_alfred(results).decode("utf-8"))


if __name__ == '__main__':
    main()
