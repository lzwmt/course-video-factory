#!/usr/bin/env python3
"""Author one section with the AI authoring endpoint and compile it."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.ai_author import _llm_chat, _extract_json
from scripts.compile_chapter import ChapterCompiler

def main():
    p=argparse.ArgumentParser(); p.add_argument('--course',required=True); p.add_argument('--section',required=True); p.add_argument('--input-section',required=True); p.add_argument('--next-title',default=''); p.add_argument('--model',default='gemini-3.7-flash-tiered'); args=p.parse_args()
    c=ChapterCompiler(course_id=args.course)
    entry, out=c.resolve_entry(section_id=args.section)
    md=Path(args.input_section).read_text(encoding='utf-8')
    prompt=f'''为系统设计短视频节生成 JSON。口播、标题、卡片必须全中文，禁止英文标题，禁止把 Markdown/HTML/图片标签粘进 narration。只能依据下面这一节 Markdown，不得引入后续内容。输出 {{"section":{{}},"scenes":{{"scenes":[]}}}}。section 必须有 id、chapter_id、section_index、title、title_zh、template、attribution、target_duration_sec（35-75）。scenes 必须严格 3-5 个镜头，包含 hook 和 summary；最后一个 preview 可提及下一节但不能讲解下一节。每镜包含 scene、id、scene_type、title、narration、actions；problem/flow/evolve 必须带 graph.nodes（只用 client/lb/web/redis/mysql/mq/worker/single）。节 ID：{args.section}；下一节标题：{args.next_title}\n\n{md}'''
    payload=_extract_json(_llm_chat([{'role':'system','content':'你是严谨的中文技术短视频编剧，只输出 JSON。'},{'role':'user','content':prompt}],args.model))
    meta=payload.get('section') or payload.get('chapter')
    scenes=payload.get('scenes'); scenes={'scenes':scenes} if isinstance(scenes,list) else scenes
    if not meta or not scenes or not 3 <= len(scenes.get('scenes',[])) <= 5: raise SystemExit('AI output must contain 3-5 scenes and section metadata')
    meta.update({'id':args.section,'chapter_id':entry.get('chapter_id'),'section_index':entry.get('section_index'),'attribution':meta.get('attribution','系统设计全书')})
    out.mkdir(parents=True,exist_ok=True)
    (out/'section.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'chapter.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(c.compile_target(section_id=args.section))
if __name__=='__main__': main()
