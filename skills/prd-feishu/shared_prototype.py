"""Keep one downloadable interactive HTML file in a PRD's iteration wiki document."""

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests


SHARED_FILENAME = '共用交互原型.html'


class SharedPrototypeError(RuntimeError):
    pass


def _data(response, operation):
    try:
        payload = response.json()
    except ValueError as exc:
        raise SharedPrototypeError(f'{operation}：飞书未返回 JSON') from exc
    if payload.get('code') != 0:
        raise SharedPrototypeError(f'{operation}：{payload}')
    return payload.get('data', {})


def _wiki_node(base, headers, token, session):
    data = _data(session.get(f'{base}/wiki/v2/spaces/get_node', headers=headers,
                             params={'token': token}), '读取 wiki 节点')
    return data['node']


def resolve_iteration_parent(base, headers, prd_url, parent_url=None, session=requests):
    """Resolve the immediate wiki parent; never silently select an ancestor or another iteration."""
    match = re.search(r'/wiki/([A-Za-z0-9]+)', prd_url)
    if not match:
        raise SharedPrototypeError('需求文档必须是 wiki 节点，才能自动定位上一层迭代文档')
    child = _wiki_node(base, headers, match.group(1), session)
    parent_token = child.get('parent_node_token')
    if not parent_token:
        raise SharedPrototypeError('需求 wiki 节点没有父节点')
    if parent_url:
        explicit = re.search(r'/wiki/([A-Za-z0-9]+)', parent_url)
        if not explicit or explicit.group(1) != parent_token:
            raise SharedPrototypeError('指定的版本文档不是该需求的直接父节点')
    parent = _wiki_node(base, headers, parent_token, session)
    if parent.get('obj_type') != 'docx':
        raise SharedPrototypeError('版本节点不是 docx 文档，无法放置 HTML 文件附件')
    host = urlsplit(prd_url).netloc
    return {
        'url': f'https://{host}/wiki/{parent_token}',
        'node_token': parent_token,
        'doc_id': parent['obj_token'],
        'title': parent.get('title', ''),
    }


def list_blocks(base, headers, doc_id, session=requests):
    items, page_token = [], None
    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        data = _data(session.get(f'{base}/docx/v1/documents/{doc_id}/blocks',
                                 headers=headers, params=params), '列出文档块')
        items.extend(data.get('items', []))
        if not data.get('has_more'):
            return items
        page_token = data.get('page_token')
        if not page_token:
            raise SharedPrototypeError('文档块分页缺少 page_token')


def sync_shared_prototype(base, headers, parent, prototype_path,
                          expected_sha256=None, session=requests):
    """Replace the existing file block's content or create exactly one file block."""
    path = Path(prototype_path)
    if not path.is_file():
        raise SharedPrototypeError(f'原型文件不存在：{path}')
    content = path.read_bytes()
    if not content or b'<html' not in content.lower():
        raise SharedPrototypeError('原型文件必须是完整的非空 HTML')
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise SharedPrototypeError('原型文件哈希与已批准版本不一致')

    doc_id = parent['doc_id']
    blocks = list_blocks(base, headers, doc_id, session)
    matches = [b for b in blocks if b.get('block_type') == 23
               and b.get('file', {}).get('name') == SHARED_FILENAME]
    if len(matches) > 1:
        raise SharedPrototypeError('版本文档中存在多个同名共用原型文件，停止以避免改错附件')
    if matches:
        file_block_id = matches[0]['block_id']
        created = False
    else:
        root = next((b for b in blocks if b.get('block_type') == 1), None)
        if not root:
            raise SharedPrototypeError('版本文档缺少根块')
        root_children = [b for b in blocks if b.get('parent_id') == root['block_id']]
        _data(session.post(f'{base}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
                           headers={**headers, 'Content-Type': 'application/json'},
                           json={'children': [{'block_type': 23, 'file': {}}],
                                 'index': len(root_children)}), '新建共用原型文件块')
        time.sleep(0.35)
        newer = list_blocks(base, headers, doc_id, session)
        old_ids = {b['block_id'] for b in blocks}
        added = [b for b in newer if b.get('block_type') == 23
                 and b['block_id'] not in old_ids]
        if len(added) != 1:
            raise SharedPrototypeError(f'新增文件块数量异常：{len(added)}')
        file_block_id = added[0]['block_id']
        created = True

    with path.open('rb') as stream:
        fields = {
            'file_name': (None, SHARED_FILENAME),
            'parent_type': (None, 'docx_file'),
            'parent_node': (None, file_block_id),
            'size': (None, str(len(content))),
            'file': (SHARED_FILENAME, stream, 'text/html'),
        }
        upload = _data(session.post(f'{base}/drive/v1/medias/upload_all',
                                    headers=headers, files=fields), '上传共用原型')
    file_token = upload['file_token']
    _data(session.patch(f'{base}/docx/v1/documents/{doc_id}/blocks/{file_block_id}',
                        headers={**headers, 'Content-Type': 'application/json'},
                        json={'replace_file': {'token': file_token}}), '更新共用原型文件块')
    checked = _data(session.get(f'{base}/docx/v1/documents/{doc_id}/blocks/{file_block_id}',
                                headers=headers), '读回共用原型文件块').get('block', {})
    actual = checked.get('file', {})
    if actual.get('token') != file_token or actual.get('name') != SHARED_FILENAME:
        raise SharedPrototypeError('共用原型文件块读回结果与上传版本不一致')
    return {'url': parent['url'], 'block_id': file_block_id,
            'file_token': file_token, 'sha256': digest, 'created': created}
