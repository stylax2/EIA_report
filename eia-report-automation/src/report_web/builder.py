"""분석 선택 웹페이지 생성.

분석가가 자기 데이터시트를 놓고 **평가서에 넣을 표·그래프를 고르는** 화면을
만든다. 분류군 → 분석 단위(회차·정점) → 분석항목을 고르면 결과와 그래프가
나오고, 채택한 항목이 목록으로 모인다.

외부 자원을 참조하지 않으므로 브라우저만 있으면 열린다. 화면은 사전 계산된
값을 고르고 그릴 뿐 지수를 계산하지 않는다.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from ..analysis.runner import TaxonResult
from .payload import build_payload

SPECIES_PAGE = 100


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


CSS = """
:root{
  --ink:#16211d; --ink-2:#3d4b45; --ink-3:#6b7a72;
  --paper:#f4f6f3; --surface:#ffffff; --surface-2:#eceff0;
  --line:#d6ddd7; --line-2:#e6ebe6;
  --moss:#2f6b4f; --moss-soft:#e3efe7;
  --critical:#a3341f; --critical-soft:#f7e6e1;
  --warn:#8a6112; --warn-soft:#f6eedc;
  --muted:#8a938c;
}
@media (prefers-color-scheme: dark){
  :root{
    --ink:#e6ece8; --ink-2:#b3bfb8; --ink-3:#8a968f;
    --paper:#101614; --surface:#18211e; --surface-2:#1f2a26;
    --line:#2c3a34; --line-2:#243029;
    --moss:#6fbf95; --moss-soft:#1d3129;
    --critical:#e0836c; --critical-soft:#33211c;
    --warn:#d6ac5c; --warn-soft:#2e2718;
    --muted:#7d8a83;
  }
}
:root[data-theme="dark"]{
  --ink:#e6ece8; --ink-2:#b3bfb8; --ink-3:#8a968f;
  --paper:#101614; --surface:#18211e; --surface-2:#1f2a26;
  --line:#2c3a34; --line-2:#243029;
  --moss:#6fbf95; --moss-soft:#1d3129;
  --critical:#e0836c; --critical-soft:#33211c;
  --warn:#d6ac5c; --warn-soft:#2e2718;
  --muted:#7d8a83;
}
:root[data-theme="light"]{
  --ink:#16211d; --ink-2:#3d4b45; --ink-3:#6b7a72;
  --paper:#f4f6f3; --surface:#ffffff; --surface-2:#eceff0;
  --line:#d6ddd7; --line-2:#e6ebe6;
  --moss:#2f6b4f; --moss-soft:#e3efe7;
  --critical:#a3341f; --critical-soft:#f7e6e1;
  --warn:#8a6112; --warn-soft:#f6eedc;
  --muted:#8a938c;
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",
              system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.num,td.num,.card-value{font-family:"SFMono-Regular",Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}

header.top{border-bottom:1px solid var(--line);background:var(--surface);
  padding:22px clamp(16px,4vw,40px)}
.top-inner{max-width:1240px;margin:0 auto;display:flex;flex-wrap:wrap;
  gap:16px;align-items:flex-end;justify-content:space-between}
h1{font-size:1.42rem;margin:0 0 5px;letter-spacing:-.01em;text-wrap:balance}
.eyebrow{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--moss);font-weight:600;margin:0 0 7px}
.meta{font-size:.78rem;color:var(--ink-3);margin:0;line-height:1.75}
.meta code{background:var(--surface-2);padding:1px 6px;border-radius:3px;color:var(--ink-2)}
.banner{background:var(--warn-soft);border:1px solid var(--warn);color:var(--warn);
  border-radius:4px;padding:8px 13px;font-size:.78rem;font-weight:600}

.shell{max-width:1240px;margin:0 auto;display:grid;
  grid-template-columns:196px minmax(0,1fr);gap:26px;
  padding:24px clamp(16px,4vw,40px) 70px}
@media (max-width:900px){.shell{grid-template-columns:1fr;gap:16px}}

nav.rail{position:sticky;top:18px;align-self:start}
@media (max-width:900px){nav.rail{position:static}}
.rail-title{font-size:.67rem;letter-spacing:.13em;text-transform:uppercase;
  color:var(--ink-3);font-weight:700;margin:0 0 9px;padding-left:10px}
.rail ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:1px}
@media (max-width:900px){.rail ul{flex-direction:row;flex-wrap:wrap;gap:5px}}
.rail button{width:100%;display:flex;justify-content:space-between;align-items:center;
  gap:8px;background:none;border:0;border-left:2px solid transparent;padding:8px 10px;
  font:inherit;font-size:.85rem;color:var(--ink-2);cursor:pointer;text-align:left;
  border-radius:0 3px 3px 0}
.rail button:hover{background:var(--surface);color:var(--ink)}
.rail button[aria-current="true"]{background:var(--moss-soft);border-left-color:var(--moss);
  color:var(--moss);font-weight:700}
.rail .badge{font-size:.73rem;color:var(--ink-3);font-family:Menlo,monospace;
  font-variant-numeric:tabular-nums}
.rail button[aria-current="true"] .badge{color:var(--moss)}
button:focus-visible,input:focus-visible{outline:2px solid var(--moss);outline-offset:2px}

main{min-width:0;display:flex;flex-direction:column;gap:18px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:5px;
  padding:18px 20px}
.panel h3{font-size:.92rem;margin:0 0 12px;display:flex;align-items:center;gap:9px}
.panel h4{font-size:.82rem;margin:0 0 7px;color:var(--ink-2)}
.hint{font-size:.77rem;color:var(--ink-3);margin:0 0 11px;line-height:1.65}
.tier{font-size:.63rem;letter-spacing:.08em;font-weight:700;background:var(--surface-2);
  color:var(--ink-3);padding:2px 6px;border-radius:3px;font-family:Menlo,monospace}

/* 분석 단위 */
.scope-groups{display:flex;flex-direction:column;gap:9px}
.scope-group{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
.scope-kind{font-size:.7rem;color:var(--ink-3);font-weight:700;min-width:52px}
.scope-chips{display:flex;flex-wrap:wrap;gap:5px}
.scope-chip{background:var(--surface-2);border:1px solid transparent;border-radius:3px;
  padding:4px 10px;font:inherit;font-size:.79rem;color:var(--ink-2);cursor:pointer}
.scope-chip:hover{border-color:var(--moss);color:var(--moss)}
.scope-chip[aria-pressed="true"]{background:var(--moss);color:#fff;font-weight:700}
:root[data-theme="dark"] .scope-chip[aria-pressed="true"],
@media (prefers-color-scheme:dark){.scope-chip[aria-pressed="true"]{color:#101614}}
.scope-chip .n{opacity:.7;margin-left:5px;font-family:Menlo,monospace}

/* 항목 체크리스트 */
.item-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:6px}
.item-check{display:flex;align-items:flex-start;gap:8px;padding:7px 9px;
  border:1px solid var(--line-2);border-radius:4px;cursor:pointer;background:var(--surface)}
.item-check:hover{border-color:var(--moss)}
.item-check.off{opacity:.5;cursor:not-allowed;background:var(--surface-2)}
.item-check input{margin-top:3px;accent-color:var(--moss)}
.item-check .body{min-width:0;flex:1}
.item-check .nm{font-size:.81rem;font-weight:600;display:block}
.item-check .rs{font-size:.71rem;color:var(--ink-3);display:block;margin-top:1px}
.marks{font-size:.73rem;font-family:Menlo,monospace;white-space:nowrap}
.m-ok{color:var(--moss);font-weight:700}
.m-lim{color:var(--warn);font-weight:700}
.m-no{color:var(--muted);font-weight:700}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:11px}
.btn{padding:5px 12px;border:1px solid var(--line);border-radius:4px;background:var(--surface);
  color:var(--ink-2);font:inherit;font-size:.78rem;cursor:pointer}
.btn:hover{border-color:var(--moss);color:var(--moss)}

/* 결과 카드 */
.result{background:var(--surface);border:1px solid var(--line);border-radius:5px;
  padding:16px 18px;display:flex;flex-direction:column;gap:12px}
.result-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.result-head h3{margin:0;font-size:.94rem}
.result-head .spacer{flex:1}
.adopt{display:flex;align-items:center;gap:6px;font-size:.77rem;color:var(--ink-2);
  cursor:pointer;white-space:nowrap}
.adopt input{accent-color:var(--moss)}
.block{display:flex;flex-direction:column;gap:7px}
.block-note{font-size:.75rem;color:var(--ink-3)}
.empty{font-size:.8rem;color:var(--ink-3);margin:0}
.na{background:var(--surface-2);border-radius:4px;padding:13px 15px}
.na strong{display:block;color:var(--muted);font-size:.85rem;margin-bottom:4px}
.na p{margin:0;font-size:.79rem;color:var(--ink-2)}

table{border-collapse:collapse;width:100%;font-size:.82rem}
.scroll-x{overflow-x:auto}
.kv th{text-align:left;font-weight:500;color:var(--ink-2);padding:6px 0;
  border-bottom:1px solid var(--line-2)}
.kv td{text-align:right;padding:6px 0;border-bottom:1px solid var(--line-2);font-weight:600}
.kv tr:last-child th,.kv tr:last-child td{border-bottom:0}
.grid th,.grid td{padding:6px 10px;border-bottom:1px solid var(--line-2);text-align:left;
  white-space:nowrap}
.grid thead th{font-size:.73rem;color:var(--ink-3);border-bottom:1px solid var(--line)}
.grid td.num,.grid th.num{text-align:right}
.species th,.species td{padding:5px 9px;border-bottom:1px solid var(--line-2);
  text-align:left;white-space:nowrap;font-size:.79rem}
.species thead th{font-size:.72rem;color:var(--ink-3);position:sticky;top:0;
  background:var(--surface);border-bottom:1px solid var(--line)}
.species .sci{font-style:italic;color:var(--ink-2)}
.species .abb{font-weight:700;color:var(--critical);font-size:.73rem}
.species .mark{text-align:center;color:var(--moss);font-weight:700}
.species .dash{text-align:center;color:var(--line)}
.tools{display:flex;gap:10px;align-items:center;margin-bottom:9px;flex-wrap:wrap}
.search{flex:1;min-width:180px;padding:6px 10px;border:1px solid var(--line);
  border-radius:4px;background:var(--paper);color:var(--ink);font:inherit;font-size:.82rem}
.result-count{font-size:.76rem;color:var(--ink-3);font-family:Menlo,monospace}

svg.chart{display:block;width:100%;height:auto;overflow:visible}
svg.chart text{fill:var(--ink-2);font-size:11px;
  font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif}
svg.chart text.val{fill:var(--ink-3);font-family:Menlo,monospace}
svg.chart .bar{fill:var(--moss)}
svg.chart .grid{stroke:var(--line-2);stroke-width:1}
svg.chart .seg-0{fill:var(--muted)}
svg.chart .seg-1{fill:var(--moss)}
svg.chart .seg-2{fill:var(--warn)}
svg.chart .cell-label{font-size:10px}

.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{display:inline-flex;align-items:baseline;gap:4px;background:var(--surface-2);
  border-radius:3px;padding:3px 8px;font-size:.77rem}
.chip.critical{background:var(--critical-soft);color:var(--critical);font-weight:600}
.chip.warn{background:var(--warn-soft);color:var(--warn);font-weight:600}
.chip.more{background:none;color:var(--ink-3);border:1px dashed var(--line)}
.chip-group{padding:9px 0;border-bottom:1px solid var(--line-2)}
.chip-group:last-child{border-bottom:0;padding-bottom:0}
.chip-group:first-child{padding-top:0}
.count{font-size:.73rem;color:var(--moss);font-weight:700}

/* 채택 목록 */
.adopted-list{display:flex;flex-direction:column;gap:3px;margin-bottom:11px}
.adopted-row{display:flex;align-items:center;gap:9px;padding:6px 0;
  border-bottom:1px solid var(--line-2);font-size:.8rem}
.adopted-row:last-child{border-bottom:0}
.adopted-row .где{color:var(--ink-3);font-size:.75rem}
.adopted-row .rm{margin-left:auto;background:none;border:0;color:var(--ink-3);
  cursor:pointer;font:inherit;font-size:.75rem;padding:2px 6px;border-radius:3px}
.adopted-row .rm:hover{color:var(--critical);background:var(--critical-soft)}
.copy-area{width:100%;min-height:96px;padding:9px 11px;border:1px solid var(--line);
  border-radius:4px;background:var(--paper);color:var(--ink-2);font-size:.77rem;
  font-family:Menlo,monospace;resize:vertical}

footer{border-top:1px solid var(--line);padding:20px clamp(16px,4vw,40px);
  font-size:.77rem;color:var(--ink-3)}
footer .inner{max-width:1240px;margin:0 auto}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


JS = r"""
(function(){
  var D = window.__DATA__, CFG = window.__CFG__;
  var state = {taxon:null, scope:null, items:new Set(), adopted:new Map(), species:{}};
  var $ = function(s,r){return (r||document).querySelector(s);};

  function esc(s){var d=document.createElement('span');d.textContent=s==null?'':s;return d.innerHTML;}
  function num(v){return typeof v==='number'?v.toLocaleString():esc(v);}
  function el(tag,cls,html){var e=document.createElement(tag);if(cls)e.className=cls;
    if(html!=null)e.innerHTML=html;return e;}
  function markCls(m){return m===CFG.OK?'m-ok':(m===CFG.LIMITED?'m-lim':'m-no');}

  /* ── SVG 차트 ───────────────────────────────────────────────── */
  var SVGNS='http://www.w3.org/2000/svg';
  function svgEl(tag,attrs){var e=document.createElementNS(SVGNS,tag);
    for(var k in attrs) e.setAttribute(k,attrs[k]); return e;}

  function barChart(items, unit){
    var W=760, LABEL=160, VALUE=74, ROW=25, PAD=6;
    var barArea = W-LABEL-VALUE;
    var H = items.length*ROW + PAD*2;
    var max = 0; items.forEach(function(it){ if(it[1]>max) max=it[1]; });
    if(max<=0) max=1;
    var svg = svgEl('svg',{'class':'chart',viewBox:'0 0 '+W+' '+H,
      role:'img','aria-label':'막대 그래프'});
    items.forEach(function(it,i){
      var y = PAD + i*ROW;
      var w = Math.max(1, it[1]/max*barArea);
      var label = svgEl('text',{x:LABEL-9,y:y+16,'text-anchor':'end'});
      label.textContent = it[0].length>18 ? it[0].slice(0,17)+'…' : it[0];
      svg.appendChild(label);
      svg.appendChild(svgEl('rect',{'class':'bar',x:LABEL,y:y+5,width:w,height:ROW-11,rx:2}));
      var val = svgEl('text',{'class':'val',x:LABEL+barArea+8,y:y+16});
      val.textContent = it[1].toLocaleString()+(unit?' '+unit:'');
      svg.appendChild(val);
    });
    return svg;
  }

  function stackedBar(segments, total){
    var W=760, H=62, PAD=4, BAR=26;
    var sum = segments.reduce(function(a,s){return a+s[1];},0) || 1;
    var svg = svgEl('svg',{'class':'chart',viewBox:'0 0 '+W+' '+H,
      role:'img','aria-label':'누적 막대'});
    var x=0;
    segments.forEach(function(s,i){
      var w = s[1]/sum*W;
      svg.appendChild(svgEl('rect',{'class':'seg-'+(i%3),x:x,y:PAD,width:Math.max(0,w),
        height:BAR,rx:2}));
      if(w>52){
        var t=svgEl('text',{x:x+w/2,y:PAD+18,'text-anchor':'middle'});
        t.setAttribute('fill','var(--paper)'); t.textContent=s[1].toLocaleString();
        svg.appendChild(t);
      }
      var lg=svgEl('text',{x:x,y:H-6});
      lg.textContent=s[0]+' '+s[1].toLocaleString();
      svg.appendChild(lg);
      x+=w;
    });
    return svg;
  }

  function heatmap(labels, values){
    var CELL=54, LEFT=52, TOP=22, W=LEFT+labels.length*CELL, H=TOP+labels.length*CELL;
    var svg=svgEl('svg',{'class':'chart',viewBox:'0 0 '+W+' '+H,
      role:'img','aria-label':'지점간 유사도 히트맵'});
    // 격자는 정사각이라 컨테이너 폭까지 늘리면 셀이 지나치게 커진다
    svg.style.maxWidth = W+'px';
    labels.forEach(function(l,i){
      var t=svgEl('text',{x:LEFT+i*CELL+CELL/2,y:14,'text-anchor':'middle'});
      t.textContent=l; svg.appendChild(t);
      var t2=svgEl('text',{x:LEFT-8,y:TOP+i*CELL+CELL/2+4,'text-anchor':'end'});
      t2.textContent=l; svg.appendChild(t2);
    });
    for(var i=0;i<labels.length;i++){
      for(var j=0;j<labels.length;j++){
        var v=values[i][j];
        var r=svgEl('rect',{x:LEFT+j*CELL,y:TOP+i*CELL,width:CELL-2,height:CELL-2,rx:2});
        r.setAttribute('fill','var(--moss)');
        r.setAttribute('fill-opacity', (0.10+0.85*v).toFixed(3));
        svg.appendChild(r);
        var t=svgEl('text',{'class':'cell-label',x:LEFT+j*CELL+(CELL-2)/2,
          y:TOP+i*CELL+CELL/2+4,'text-anchor':'middle'});
        t.setAttribute('fill', v>0.55 ? 'var(--paper)' : 'var(--ink-2)');
        t.textContent=v.toFixed(2);
        svg.appendChild(t);
      }
    }
    return svg;
  }

  /* ── 블록 렌더러 ────────────────────────────────────────────── */
  function renderBlock(b, taxon, scope){
    var wrap = el('div','block');
    if(b.note) wrap.appendChild(el('p','block-note',esc(b.note)));

    if(b.kind==='kv'){
      var rows=b.rows.map(function(r){
        return '<tr><th>'+esc(r[0])+'</th><td class="num">'+num(r[1])+'</td></tr>';}).join('');
      wrap.appendChild(el('table','kv','<tbody>'+rows+'</tbody>'));
    }
    else if(b.kind==='bars'){
      wrap.appendChild(barChart(b.items, b.unit==='종'?'':b.unit));
      if(b.truncated) wrap.appendChild(el('p','block-note','외 '+b.truncated+'개 생략'));
    }
    else if(b.kind==='stacked'){
      wrap.appendChild(stackedBar(b.segments, b.total));
    }
    else if(b.kind==='matrix'){
      var head='<tr>'+b.columns.map(function(c,i){
        return '<th'+(i?' class="num"':'')+'>'+esc(c)+'</th>';}).join('')+'</tr>';
      var body=b.rows.map(function(r){
        return '<tr>'+r.map(function(c,i){
          return i? '<td class="num">'+num(c)+'</td>' : '<th>'+esc(c)+'</th>';
        }).join('')+'</tr>';}).join('');
      var d=el('div','scroll-x');
      d.appendChild(el('table','grid','<thead>'+head+'</thead><tbody>'+body+'</tbody>'));
      wrap.appendChild(d);
    }
    else if(b.kind==='heatmap'){
      wrap.appendChild(heatmap(b.labels,b.values));
    }
    else if(b.kind==='chips'){
      b.groups.forEach(function(g){
        var box=el('div','chip-group');
        box.appendChild(el('h4',null,esc(g.title)+' <span class="count">'+g.count+'종</span>'));
        if(!g.items.length){ box.appendChild(el('p','empty','해당 없음')); }
        else{
          var cs=g.items.map(function(s){
            return '<span class="chip '+(g.tone||'')+'">'+esc(s)+'</span>';}).join('');
          if(g.count>g.items.length) cs+='<span class="chip more">외 '+(g.count-g.items.length)+'종</span>';
          box.appendChild(el('div','chips',cs));
        }
        wrap.appendChild(box);
      });
    }
    else if(b.kind==='species'){
      wrap.appendChild(speciesTable(taxon,scope));
    }
    return wrap;
  }

  /* ── 종목록 (단위로 선별) ───────────────────────────────────── */
  function speciesTable(taxon, scope){
    var T=D[taxon], idx=scope.columns.map(function(c){return T.columns.indexOf(c);})
      .filter(function(i){return i>=0;});
    var rows=T.species.filter(function(r){
      return idx.some(function(i){return r[4][i]==='1';});
    });
    var box=el('div');
    var tools=el('div','tools');
    var input=el('input','search'); input.type='search';
    input.placeholder='국명 · 학명 · 과명 검색'; input.setAttribute('aria-label','종 검색');
    var count=el('span','result-count');
    tools.appendChild(input); tools.appendChild(count); box.appendChild(tools);

    var scroll=el('div','scroll-x');
    var head='<tr><th>과명</th><th>학명</th><th>국명</th><th>법정지위</th>'+
      scope.columns.map(function(c){return '<th>'+esc(c)+'</th>';}).join('')+'</tr>';
    var table=el('table','species','<thead>'+head+'</thead><tbody></tbody>');
    scroll.appendChild(table); box.appendChild(scroll);
    var more=el('button','btn','더 보기'); more.type='button'; box.appendChild(more);

    var shown=Math.min(CFG.PAGE, rows.length), filtered=rows;
    function draw(){
      var slice=filtered.slice(0,shown);
      table.querySelector('tbody').innerHTML = slice.map(function(r){
        var marks=idx.map(function(i){
          return r[4][i]==='1' ? '<td class="mark">●</td>' : '<td class="dash">·</td>';}).join('');
        return '<tr><td>'+esc(r[0])+'</td><td class="sci">'+esc(r[1])+'</td><td>'+esc(r[2])+
          '</td><td class="abb">'+esc(r[3]||'')+'</td>'+marks+'</tr>';
      }).join('');
      count.textContent=filtered.length.toLocaleString()+'종 중 '+slice.length.toLocaleString()+'종 표시';
      more.hidden = shown>=filtered.length;
    }
    var timer;
    input.addEventListener('input',function(){
      clearTimeout(timer);
      timer=setTimeout(function(){
        var q=input.value.trim().toLowerCase();
        filtered = q ? rows.filter(function(r){
          return (r[0]+' '+r[1]+' '+r[2]).toLowerCase().indexOf(q)>=0;}) : rows;
        shown=Math.min(CFG.PAGE,filtered.length); draw();
      },140);
    });
    more.addEventListener('click',function(){
      shown=Math.min(shown+CFG.PAGE*5, filtered.length); draw();});
    draw();
    return box;
  }

  /* ── 화면 구성 ─────────────────────────────────────────────── */
  function currentScope(){
    var T=D[state.taxon];
    return T.scopes.filter(function(s){return s.key===state.scope;})[0] || T.scopes[0];
  }

  function renderRail(){
    var ul=$('#rail-list'); ul.innerHTML='';
    Object.keys(D).forEach(function(code){
      var T=D[code];
      var li=el('li');
      var b=el('button',null,'<span>'+esc(T.label)+'</span><span class="badge">'+
        T.scopes.filter(function(s){return s.key==='all';})[0].total.toLocaleString()+'</span>');
      b.type='button';
      b.setAttribute('aria-current', String(code===state.taxon));
      b.addEventListener('click',function(){
        state.taxon=code; state.scope='all'; state.items=new Set(); renderAll();});
      li.appendChild(b); ul.appendChild(li);
    });
  }

  function renderScopes(){
    var T=D[state.taxon], box=$('#scopes'); box.innerHTML='';
    var order=['문헌','정점','회차','종합'], groups={};
    T.scopes.forEach(function(s){ (groups[s.kind]=groups[s.kind]||[]).push(s); });
    order.forEach(function(kind){
      if(!groups[kind]) return;
      var g=el('div','scope-group');
      g.appendChild(el('span','scope-kind',kind));
      var chips=el('div','scope-chips');
      groups[kind].forEach(function(s){
        var b=el('button','scope-chip',esc(s.label)+'<span class="n">'+s.total.toLocaleString()+'</span>');
        b.type='button';
        b.setAttribute('aria-pressed', String(s.key===state.scope));
        b.addEventListener('click',function(){ state.scope=s.key; renderScopes(); renderItems(); renderResults();});
        chips.appendChild(b);
      });
      g.appendChild(chips); box.appendChild(g);
    });
  }

  function renderItems(){
    var sc=currentScope(), box=$('#items'); box.innerHTML='';
    sc.items.forEach(function(it){
      var usable = it.table[0]!==CFG.NONE;
      var lab=el('label','item-check'+(usable?'':' off'));
      var cb=el('input'); cb.type='checkbox'; cb.disabled=!usable;
      cb.checked = usable && state.items.has(it.code);
      cb.addEventListener('change',function(){
        if(cb.checked) state.items.add(it.code); else state.items.delete(it.code);
        renderResults();
      });
      lab.appendChild(cb);
      var body=el('div','body',
        '<span class="nm">'+esc(it.name)+'</span>'+
        '<span class="rs">'+esc(usable?it.table[1]:it.table[1])+'</span>');
      lab.appendChild(body);
      lab.appendChild(el('span','marks',
        '<span class="'+markCls(it.table[0])+'" title="표">'+it.table[0]+'</span>'+
        '<span class="'+markCls(it.graph[0])+'" title="그래프: '+esc(it.graph[1])+'">'+it.graph[0]+'</span>'));
      box.appendChild(lab);
    });
    var n=sc.items.filter(function(i){return i.table[0]!==CFG.NONE;}).length;
    $('#item-summary').textContent = sc.items.length+'개 항목 중 '+n+'개 산출 가능';
  }

  function renderResults(){
    var sc=currentScope(), box=$('#results'); box.innerHTML='';
    var picked=sc.items.filter(function(i){return state.items.has(i.code);});
    if(!picked.length){
      box.appendChild(el('div','panel','<p class="empty">위에서 분석항목을 고르면 결과가 여기에 나옵니다.</p>'));
      return;
    }
    picked.forEach(function(it){
      var card=el('div','result');
      var head=el('div','result-head',
        '<span class="tier">'+esc(it.tier)+'</span><h3>'+esc(it.name)+'</h3>'+
        '<span class="marks"><span class="'+markCls(it.table[0])+'">'+it.table[0]+'</span>'+
        '<span class="'+markCls(it.graph[0])+'">'+it.graph[0]+'</span></span><span class="spacer"></span>');
      var key=state.taxon+'|'+state.scope+'|'+it.code;
      var lab=el('label','adopt');
      var cb=el('input'); cb.type='checkbox'; cb.checked=state.adopted.has(key);
      cb.addEventListener('change',function(){
        if(cb.checked) state.adopted.set(key,{taxon:D[state.taxon].label,scope:sc.label,
          code:it.code,name:it.name,table:it.table[0],graph:it.graph[0]});
        else state.adopted.delete(key);
        renderAdopted();
      });
      lab.appendChild(cb); lab.appendChild(document.createTextNode('평가서 반영'));
      head.appendChild(lab); card.appendChild(head);

      if(!it.blocks.length){
        card.appendChild(el('div','na','<strong>산출 불가</strong><p>'+esc(it.table[1])+'</p>'));
      } else {
        it.blocks.forEach(function(b){ card.appendChild(renderBlock(b,state.taxon,sc)); });
      }
      box.appendChild(card);
    });
  }

  function renderAdopted(){
    var box=$('#adopted'), list=el('div','adopted-list');
    box.innerHTML='';
    if(!state.adopted.size){
      box.appendChild(el('p','empty','항목 카드의 "평가서 반영"을 체크하면 여기에 모입니다.'));
      $('#copy').value='';
      $('#adopted-count').textContent='0건';
      return;
    }
    var lines=[];
    state.adopted.forEach(function(v,k){
      var row=el('div','adopted-row',
        '<span class="tier">'+esc(v.code)+'</span><strong>'+esc(v.name)+'</strong>'+
        '<span class="где">'+esc(v.taxon)+' · '+esc(v.scope)+'</span>'+
        '<span class="marks"><span class="'+markCls(v.table)+'">'+v.table+'</span>'+
        '<span class="'+markCls(v.graph)+'">'+v.graph+'</span></span>');
      var rm=el('button','rm','제거'); rm.type='button';
      rm.addEventListener('click',function(){ state.adopted.delete(k); renderAdopted(); renderResults();});
      row.appendChild(rm); list.appendChild(row);
      lines.push([v.taxon,v.scope,v.code,v.name,
        '표 '+v.table,'그래프 '+v.graph].join('\t'));
    });
    box.appendChild(list);
    $('#copy').value='분류군\t분석단위\t코드\t항목\t표\t그래프\n'+lines.join('\n');
    $('#adopted-count').textContent=state.adopted.size+'건';
  }

  function renderAll(){ renderRail(); renderScopes(); renderItems(); renderResults(); }

  /* 기본 선택 */
  $('#pick-all').addEventListener('click',function(){
    currentScope().items.forEach(function(i){ if(i.table[0]!==CFG.NONE) state.items.add(i.code);});
    renderItems(); renderResults();});
  $('#pick-none').addEventListener('click',function(){
    state.items=new Set(); renderItems(); renderResults();});
  $('#pick-graph').addEventListener('click',function(){
    state.items=new Set();
    currentScope().items.forEach(function(i){ if(i.graph[0]===CFG.OK) state.items.add(i.code);});
    renderItems(); renderResults();});
  $('#copy-btn').addEventListener('click',function(){
    var ta=$('#copy'); ta.select();
    if(navigator.clipboard) navigator.clipboard.writeText(ta.value);
    else document.execCommand('copy');
    var b=$('#copy-btn'); b.textContent='복사됨'; setTimeout(function(){b.textContent='복사';},1400);
  });

  state.taxon=Object.keys(D)[0]; state.scope='all';
  renderAll(); renderAdopted();
})();
"""


def build_body(results: list[TaxonResult], master_path: str, survey_path: str) -> str:
    """`<body>` 안에 들어갈 내용만 만든다(style·script 포함)."""
    payload = build_payload(results)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    cfg = {"OK": "○", "LIMITED": "△", "NONE": "✗", "PAGE": SPECIES_PAGE}

    return f"""<style>{CSS}</style>
<header class="top">
  <div class="top-inner">
    <div>
      <p class="eyebrow">환경영향평가 동·식물상</p>
      <h1>분석항목 선택 작업대</h1>
      <p class="meta">
        마스터DB <code>{_esc(Path(master_path).name)}</code> ·
        조사자료 <code>{_esc(Path(survey_path).name)}</code><br>
        분류군을 고르고 분석 단위를 정한 뒤, 평가서에 넣을 항목을 선택하십시오. · 생성 {generated}
      </p>
    </div>
    <div class="banner">파일럿 가상데이터 — 실제 조사 결과 아님</div>
  </div>
</header>

<div class="shell">
  <nav class="rail" aria-label="분류군">
    <p class="rail-title">분류군</p>
    <ul id="rail-list"></ul>
  </nav>
  <main>
    <section class="panel">
      <h3>분석 단위</h3>
      <p class="hint">평가서에 실을 표·그래프의 범위를 정합니다.
         정점조사를 하는 분류군은 정점 단위까지 고를 수 있습니다.</p>
      <div class="scope-groups" id="scopes"></div>
    </section>

    <section class="panel">
      <h3>분석항목 <span class="tier" id="item-summary"></span></h3>
      <p class="hint">각 항목의 두 기호는 <b>표 · 그래프</b> 순서입니다.
         고른 단위가 지지하지 않는 항목은 사유와 함께 비활성으로 표시되며 선택할 수 없습니다.</p>
      <div class="toolbar">
        <button class="btn" type="button" id="pick-all">산출 가능한 항목 전체</button>
        <button class="btn" type="button" id="pick-graph">그래프 가능한 항목만</button>
        <button class="btn" type="button" id="pick-none">선택 해제</button>
      </div>
      <div class="item-grid" id="items"></div>
    </section>

    <div id="results"></div>

    <section class="panel">
      <h3>채택 목록 <span class="tier" id="adopted-count">0건</span></h3>
      <p class="hint">평가서에 넣기로 한 항목입니다. 아래 텍스트를 복사해 작성 계획에 쓰십시오.</p>
      <div id="adopted"></div>
      <div class="toolbar"><button class="btn" type="button" id="copy-btn">복사</button></div>
      <textarea class="copy-area" id="copy" readonly aria-label="채택 목록 복사용"></textarea>
    </section>
  </main>
</div>

<footer><div class="inner">
  화면의 모든 수치는 Python 분석 계층이 확정한 값입니다. 이 페이지는 다시 계산하지 않습니다.
  산출할 수 없는 항목은 0으로 채우지 않고 사유와 함께 표시합니다.
</div></footer>

<script>window.__CFG__={json.dumps(cfg, ensure_ascii=False)};
window.__DATA__={json.dumps(payload, ensure_ascii=False, separators=(",", ":"))};</script>
<script>{JS}</script>"""


def build_html(results: list[TaxonResult], master_path: str, survey_path: str) -> str:
    """브라우저로 바로 여는 자체 완결형 HTML 문서."""
    body = build_body(results, master_path, survey_path)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>분석항목 선택 작업대</title>
</head>
<body>
{body}
</body>
</html>"""


def write_report(results: list[TaxonResult], out_path: Path | str,
                 master_path: str, survey_path: str, fragment: bool = False) -> Path:
    """HTML 파일로 저장한다.

    fragment=True 면 문서 골격 없이 내용만 쓴다. 게시 시 골격을 감싸주는
    환경에 넘길 때 사용한다.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    build = build_body if fragment else build_html
    out.write_text(build(results, master_path, survey_path), encoding="utf-8")
    return out
