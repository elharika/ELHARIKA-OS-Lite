#!/usr/bin/env python3
"""Merge pinned hardware projects into a resolved platform manifest without path collisions."""
import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def overlay(platform,hardware):
    out=ET.Element('manifest')
    ET.SubElement(out,'remote',{'name':'elharika-hardware','fetch':'https://github.com/'})
    projects=platform.findall('project');removed=set();paths=set()
    for project in hardware.findall('project'):
        path=project.get('path');name=project.get('name');rev=project.get('revision','')
        if not path or not name or not re.fullmatch('[0-9a-f]{40}',rev):raise ValueError('Hardware projects must be fully pinned')
        if path in paths:raise ValueError('Duplicate hardware path')
        paths.add(path)
        for existing in projects:
            if existing.get('path',existing.get('name'))==path or existing.get('name')==name:
                old=existing.get('name')
                if old not in removed:ET.SubElement(out,'remove-project',{'name':old});removed.add(old)
        p=copy.deepcopy(project);p.set('remote','elharika-hardware');out.append(p)
    if 'device/samsung/v1awifi' not in paths:raise ValueError('SM-P900 target missing')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('platform',type=Path);p.add_argument('hardware',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();root=overlay(ET.parse(a.platform).getroot(),ET.parse(a.hardware).getroot());ET.indent(root)
    with a.output.open('xb') as f:ET.ElementTree(root).write(f,encoding='utf-8',xml_declaration=True)
