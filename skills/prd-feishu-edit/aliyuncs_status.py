#!/usr/bin/env python3
"""Shared helpers for linking a Feishu PRD operation to an Aliyun DevOps requirement."""

import json
import os
import re
import stat
import tempfile
from pathlib import Path


def find_aliyuncs_config(start_paths):
    """Find the nearest .aliyuncs.json by walking upward from each start path."""
    for start in start_paths:
        if not start:
            continue
        path = Path(start).resolve()
        if path.is_file():
            path = path.parent
        while True:
            candidate = path / '.aliyuncs.json'
            if candidate.exists():
                return candidate
            if path == path.parent:
                break
            path = path.parent
    return None


def feishu_document_key(url):
    """Return a stable key for a Feishu wiki/docx URL, ignoring host/query/slashes."""
    match = re.search(r'/(?:wiki|docx)/([A-Za-z0-9]+)', url or '')
    return match.group(1) if match else (url or '').rstrip('/')


def match_requirement(config, target_url):
    """Match a requirement by the document token contained in feishu_url."""
    target_key = feishu_document_key(target_url)
    return next(
        (item for item in config.get('requirements', [])
         if feishu_document_key(item.get('feishu_url')) == target_key),
        None,
    )


def _value(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _atomic_write_json(path, data):
    """Atomically replace a JSON file while preserving its existing permissions."""
    path = Path(path)
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def build_client(config):
    from alibabacloud_devops20210625.client import Client
    from alibabacloud_tea_openapi.models import Config

    return Client(Config(
        access_key_id=config['accessKeyId'],
        access_key_secret=config['accessKeySecret'],
        endpoint='devops.cn-hangzhou.aliyuncs.com',
    ))


def sync_requirement_status(config_path, config, requirement, target_status, client=None):
    """Update the matched requirement status by name and persist it locally.

    Returns ``(old_status, changed)``. Missing statuses and API failures are raised so
    callers cannot report an entirely successful workflow after a partial result.
    """
    from alibabacloud_devops20210625.models import (
        GetWorkItemWorkFlowInfoRequest,
        UpdateWorkItemRequest,
    )

    client = client or build_client(config)
    organization_id = config['organizationId']
    requirement_id = requirement['identifier']

    info = client.get_work_item_info(organization_id, requirement_id)
    workitem = _value(_value(info, 'body'), 'workitem')
    old_status = _value(workitem, 'status', '') or ''

    changed = old_status != target_status
    if changed:
        workflow_request = GetWorkItemWorkFlowInfoRequest(configuration_id='')
        workflow_response = client.get_work_item_work_flow_info(
            organization_id, requirement_id, workflow_request)
        workflow = _value(_value(workflow_response, 'body'), 'workflow')
        statuses = _value(workflow, 'statuses', []) or []
        target = next((status for status in statuses
                       if _value(status, 'name') == target_status), None)
        if target is None:
            available = '、'.join(filter(None, (_value(status, 'name') for status in statuses)))
            raise RuntimeError(
                f'需求工作流中不存在状态“{target_status}”'
                + (f'（可用状态：{available}）' if available else '')
            )
        status_identifier = _value(target, 'identifier')
        if not status_identifier:
            raise RuntimeError(f'状态“{target_status}”缺少 identifier')
        client.update_work_item(organization_id, UpdateWorkItemRequest(
            identifier=requirement_id,
            field_type='status',
            property_key='status',
            property_value=status_identifier,
        ))

    # Re-read immediately before writing so unrelated edits made during the API call survive.
    latest_config = json.load(open(config_path, encoding='utf-8'))
    latest_requirement = next(
        (item for item in latest_config.get('requirements', [])
         if item.get('identifier') == requirement_id),
        None,
    )
    if latest_requirement is None:
        raise RuntimeError(f'.aliyuncs.json 中已找不到需求 {requirement_id}，未同步本地状态')
    latest_requirement['status'] = target_status
    _atomic_write_json(config_path, latest_config)
    requirement['status'] = target_status
    return old_status, changed
