#!/usr/bin/env python3
"""Split source Markdown ## headings into publishable section knowledge packages."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def slugify(title: str) -> str:
    title = re.sub(r'^Section\s+\d+\s*:\s*', '', title, flags=re.I)
    title = re.sub(r'[^a-zA-Z0-9]+', '-', title).strip('-').lower()
    return title or 'section'

def split_markdown(text: str):
    matches = list(re.finditer(r'^##\s+(.+?)\s*$', text, re.M))
    return [(m.group(1).strip(), text[m.start(): matches[i+1].start() if i+1 < len(matches) else len(text)].strip()) for i,m in enumerate(matches)]

def section_title(title: str) -> str:
    return re.sub(r'^Section\s+\d+\s*:\s*', '', title, flags=re.I).strip()

def build(args):
    source = ROOT / 'content' / 'source' / args.source
    chapter_dir = ROOT / 'content' / 'chapters' / args.chapter_dir
    base = ROOT / 'content' / 'sections' / args.course
    sections = split_markdown(source.read_text(encoding='utf-8'))
    if not sections: raise SystemExit(f'No ## headings in {source}')
    entries=[]
    for idx,(heading, block) in enumerate(sections):
        sid = f'{args.chapter_id}-S{idx:02d}'
        slug = slugify(heading)
        out = base / f'{sid}-{slug}'
        out.mkdir(parents=True, exist_ok=True)
        plain = re.sub(r'[#*_>`]', '', block)
        plain = re.sub(r'\s+', ' ', plain).strip()
        body = plain[:260] + ('...' if len(plain)>260 else '')
        title = section_title(heading)
        chapter = {
          'id': sid, 'chapter_id': args.chapter_id, 'section_index': idx,
          'slug': slug, 'title': heading, 'title_zh': title,
          'source': f'content/source/{args.source}#{slug}',
          'attribution': '系统设计全书', 'template': args.template,
          'target_duration_sec': 45 if idx == 0 or idx == len(sections)-1 else 60,
          'content_markdown': block
        }
        # Keep a compatible chapter.json while exposing the documented section.json.
        (out/'source.md').write_text(block + '\n', encoding='utf-8')
        (out/'section.md').write_text(block + '\n', encoding='utf-8')
        (out/'section.json').write_text(json.dumps(chapter,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (out/'chapter.json').write_text(json.dumps(chapter,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        next_title = section_title(sections[idx+1][0]) if idx+1 < len(sections) else None
        scenes=[
          {'scene':'01','id':f'{sid}_hook','scene_type':'hook','title':title,'narration':f'这一节我们解决一个关键问题：{title}。{body}'},
          {'scene':'02','id':f'{sid}_explain','scene_type':'problem' if idx else 'flow','title':title,'scene_type':'problem' if idx else 'flow','narration':body,'actions':[]},
          {'scene':'03','id':f'{sid}_tradeoff','scene_type':'flow','title':'关键权衡','narration':f'理解{title}后，还要关注容量、延迟、可靠性与复杂度之间的权衡。','actions':[]},
        ]
        if next_title:
          scenes.append({'scene':'04','id':f'{sid}_preview','scene_type':'preview','title':f'下节：{next_title}','narration':f'下节我们继续：{next_title}。','actions':[]})
        scenes.append({'scene':f'{len(scenes)+1:02d}','id':f'{sid}_summary','scene_type':'summary','title':'本节要点','narration':f'记住本节核心：{title}。','actions':[]})
        (out/'scenes.json').write_text(json.dumps({'title':heading,'scenes':scenes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        entries.append({'id':sid,'chapter_id':args.chapter_id,'section_index':idx,'slug':slug,'source':chapter['source'],'source_heading':heading,'title_zh':title,'template':chapter['template'],'status':'ready','dir':str(out.relative_to(ROOT)),'target_duration_sec':chapter['target_duration_sec'],'next_id':f'{args.chapter_id}-S{idx+1:02d}' if idx+1<len(sections) else None})
    cat = ROOT/'content'/'catalog.json'
    data=json.loads(cat.read_text(encoding='utf-8'))
    data['sections']=[e for e in data.get('sections',[]) if e['chapter_id'] != args.chapter_id] + entries
    cat.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'created {len(entries)} sections for chapter {args.chapter_id}')

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--source',default='01-scaling.md'); p.add_argument('--chapter-dir',default='01-scaling'); p.add_argument('--chapter-id',default='01'); p.add_argument('--course',default='system-design'); p.add_argument('--template',default='system_evolution'); build(p.parse_args())
