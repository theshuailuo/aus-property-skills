# -*- coding: utf-8 -*-
"""browser_gate.py — 开跑前门卫:检查会话内浏览器要用的站点是否已在 Claude 桌面端站点级允许清单里。
退出码 0 = 全部已放行,可以用会话浏览器;退出码 2 = 有缺项,流水线必须走「无浏览器」路径(curl 源 + 降级),并把缺项清单打给人。
用法:python -X utf8 -I browser_gate.py [站点 ...](默认 www.domain.com.au www.aussie.com.au www.onthehouse.com.au www.allhomes.com.au web.archive.org)"""
import json, os, sys
CFG = os.path.join(os.environ.get('APPDATA', ''), 'Claude', 'claude_desktop_config.json')
need = sys.argv[1:] or ['www.domain.com.au', 'www.aussie.com.au', 'www.onthehouse.com.au', 'www.allhomes.com.au', 'web.archive.org']
try:
    lst = json.load(open(CFG, encoding='utf-8')).get('preferences', {}).get('launchPreviewAllowedOrigins', [])
except Exception as e:
    print('GATE: 读不到桌面端配置(%s)→ 按未放行处理,走无浏览器路径' % e); sys.exit(2)
def ok(h):
    apex = h[4:] if h.startswith('www.') else h
    return f'https://{h}' in lst or f'https://{apex}' in lst or f'https://www.{apex}' in lst
missing = [h for h in need if not ok(h)]
if missing:
    print('GATE: 未放行 →', ', '.join(missing))
    print('GATE: 本次不开会话浏览器;需要人在 设置 → Claude Code → Browser 加上述站点,(设置里加裸域即可,www 自动覆盖)')
    sys.exit(2)
print('GATE: 全部已放行:', ', '.join(need)); sys.exit(0)
