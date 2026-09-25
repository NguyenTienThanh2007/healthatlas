(() => {
  const palette = ['#0a84ff','#7458ff','#16c79a','#ff9f0a','#ff5d7d','#30c7e8','#5e5ce6','#34c759'];

  const getJSON = id => {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent || 'null'); } catch { return null; }
  };

  const theme = () => {
    const dark = document.documentElement.dataset.theme === 'dark';
    return {
      dark,
      grid: dark ? 'rgba(255,255,255,.08)' : 'rgba(35,65,125,.09)',
      text: dark ? '#8fa3bf' : '#7b879b',
      axis: dark ? '#5c718f' : '#a9b3c2',
      fill: dark ? 'rgba(10,132,255,.11)' : 'rgba(10,132,255,.10)'
    };
  };

  const niceRange = values => {
    if (!values.length) return [0,100];
    let min = Math.min(...values), max = Math.max(...values);
    if (min === max) { min -= Math.max(1,Math.abs(min)*.1); max += Math.max(1,Math.abs(max)*.1); }
    const pad = (max-min)*.12;
    min -= pad; max += pad;
    if (min > 0 && min < max*.28) min = 0;
    return [min,max];
  };

  const setupCanvas = canvas => {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(rect.width*dpr));
    canvas.height = Math.max(1, Math.round(rect.height*dpr));
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr,0,0,dpr,0,0);
    return {ctx,w:rect.width,h:rect.height};
  };

  const drawGrid = (ctx,w,h,pad,min,max,unit='') => {
    const t=theme();
    ctx.lineWidth=1;
    ctx.font='10px -apple-system,BlinkMacSystemFont,"SF Pro Text",Arial';
    ctx.textBaseline='middle';
    const lines=4;
    for(let i=0;i<=lines;i++){
      const y=pad.top+(h-pad.top-pad.bottom)*(i/lines);
      ctx.strokeStyle=t.grid;ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(w-pad.right,y);ctx.stroke();
      const value=max-(max-min)*(i/lines);
      ctx.fillStyle=t.text;ctx.textAlign='right';
      const formatted=Math.abs(value)>=1000?Math.round(value).toLocaleString():value.toFixed(max-min<20?1:0);
      ctx.fillText(`${formatted}${unit}`,pad.left-9,y);
    }
  };

  const roundedRect = (ctx,x,y,w,h,r) => {
    const rr=Math.min(r,w/2,h/2);
    ctx.beginPath();ctx.moveTo(x+rr,y);ctx.arcTo(x+w,y,x+w,y+h,rr);ctx.arcTo(x+w,y+h,x,y+h,rr);ctx.arcTo(x,y+h,x,y,rr);ctx.arcTo(x,y,x+w,y,rr);ctx.closePath();
  };

  class LineChart {
    constructor(canvas,multi=false){
      this.canvas=canvas;this.multi=multi;this.source=canvas.dataset.source;this.unit=canvas.dataset.unit||'';this.hover=null;
      this.pointerMove=this.pointerMove.bind(this);this.draw=this.draw.bind(this);
      canvas.addEventListener('pointermove',this.pointerMove);canvas.addEventListener('pointerleave',()=>{this.hover=null;this.draw()});
      this.resizeObserver=new ResizeObserver(this.draw);this.resizeObserver.observe(canvas.parentElement||canvas);
      this.draw();
    }
    data(){
      const raw=getJSON(this.source);
      if(this.multi) return Array.isArray(raw)?raw:[];
      return [{id:'series',name:'Series',values:Array.isArray(raw)?raw:[]}];
    }
    normalise(){
      return this.data().map((s,i)=>({id:s.id||String(i),name:s.name||s.id||`Series ${i+1}`,color:palette[i%palette.length],values:(s.values||[]).map(x=>({year:Number(x.year),value:Number(x.value)})).filter(x=>Number.isFinite(x.year)&&Number.isFinite(x.value)).sort((a,b)=>a.year-b.year)})).filter(s=>s.values.length);
    }
    pointerMove(e){
      const r=this.canvas.getBoundingClientRect();this.hover={x:e.clientX-r.left,y:e.clientY-r.top};this.draw();
    }
    draw(){
      const series=this.normalise(); const {ctx,w,h}=setupCanvas(this.canvas);ctx.clearRect(0,0,w,h);if(!series.length){return}
      const pad={left:58,right:20,top:22,bottom:36};
      const years=[...new Set(series.flatMap(s=>s.values.map(v=>v.year)))].sort((a,b)=>a-b);
      const values=series.flatMap(s=>s.values.map(v=>v.value));
      const [min,max]=niceRange(values);const minYear=Math.min(...years),maxYear=Math.max(...years);
      const x=v=>pad.left+(w-pad.left-pad.right)*((v-minYear)/(maxYear-minYear||1));
      const y=v=>pad.top+(h-pad.top-pad.bottom)*(1-(v-min)/(max-min||1));
      drawGrid(ctx,w,h,pad,min,max,this.unit);
      const t=theme();
      const tickCount=Math.min(6,years.length);
      ctx.font='10px -apple-system,BlinkMacSystemFont,"SF Pro Text",Arial';ctx.fillStyle=t.text;ctx.textAlign='center';ctx.textBaseline='top';
      for(let i=0;i<tickCount;i++){
        const idx=Math.round((years.length-1)*(i/(tickCount-1||1)));const yr=years[idx];ctx.fillText(String(yr),x(yr),h-pad.bottom+10);
      }

      let nearest=null;
      if(this.hover){
        const targetYear=minYear+(this.hover.x-pad.left)/(w-pad.left-pad.right)*(maxYear-minYear||1);
        nearest=years.reduce((a,b)=>Math.abs(b-targetYear)<Math.abs(a-targetYear)?b:a,years[0]);
      }

      series.forEach((s,si)=>{
        const points=s.values.map(v=>({x:x(v.year),y:y(v.value),...v}));
        if(!this.multi && points.length>1){
          const grad=ctx.createLinearGradient(0,pad.top,0,h-pad.bottom);grad.addColorStop(0,'rgba(10,132,255,.18)');grad.addColorStop(1,'rgba(10,132,255,0)');
          ctx.beginPath();ctx.moveTo(points[0].x,h-pad.bottom);points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.lineTo(p.x,p.y));ctx.lineTo(points[points.length-1].x,h-pad.bottom);ctx.closePath();ctx.fillStyle=grad;ctx.fill();
        }
        ctx.strokeStyle=s.color;ctx.lineWidth=2.6;ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();
        points.forEach((p,i)=>{if(i===0)ctx.moveTo(p.x,p.y);else{const prev=points[i-1];const mid=(prev.x+p.x)/2;ctx.bezierCurveTo(mid,prev.y,mid,p.y,p.x,p.y)}});ctx.stroke();
        points.forEach(p=>{ctx.fillStyle=theme().dark?'#0b1728':'#fff';ctx.beginPath();ctx.arc(p.x,p.y,3.8,0,Math.PI*2);ctx.fill();ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.stroke()});
      });

      if(nearest!=null){
        const hx=x(nearest);ctx.strokeStyle=t.axis;ctx.lineWidth=1;ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(hx,pad.top);ctx.lineTo(hx,h-pad.bottom);ctx.stroke();ctx.setLineDash([]);
        const items=series.map(s=>({s,p:s.values.find(v=>v.year===nearest)})).filter(x=>x.p);
        if(items.length){
          const boxW=Math.min(220,w-pad.left-pad.right),boxH=28+items.length*19;let bx=hx+12;if(bx+boxW>w-8)bx=hx-boxW-12;let by=pad.top+8;
          roundedRect(ctx,bx,by,boxW,boxH,12);ctx.fillStyle=t.dark?'rgba(16,30,49,.96)':'rgba(255,255,255,.96)';ctx.fill();ctx.strokeStyle=t.grid;ctx.stroke();
          ctx.textAlign='left';ctx.textBaseline='middle';ctx.font='600 10px -apple-system,BlinkMacSystemFont,"SF Pro Text",Arial';ctx.fillStyle=t.dark?'#eaf1ff':'#1d2d47';ctx.fillText(String(nearest),bx+12,by+15);
          items.forEach((item,i)=>{const yy=by+34+i*19;ctx.fillStyle=item.s.color;ctx.beginPath();ctx.arc(bx+14,yy,4,0,Math.PI*2);ctx.fill();ctx.fillStyle=t.text;ctx.font='10px -apple-system,BlinkMacSystemFont,"SF Pro Text",Arial';ctx.fillText(`${item.s.name}: ${item.p.value}${this.unit}`,bx+25,yy)});
        }
      }
    }
  }

  const renderLegends = () => {
    document.querySelectorAll('[data-chart-legend]').forEach(host=>{
      const series=getJSON(host.dataset.chartLegend);if(!Array.isArray(series))return;
      host.innerHTML=series.map((s,i)=>`<span class="legend-item"><i class="legend-swatch" style="background:${palette[i%palette.length]}"></i>${String(s.name||s.id||'Series')}</span>`).join('');
    });
  };

  const instances=[];
  const init=()=>{
    document.querySelectorAll('canvas[data-line-chart]').forEach(c=>{const chart=new LineChart(c,false);instances.push(chart)});
    document.querySelectorAll('canvas[data-multi-line-chart]').forEach(c=>{const chart=new LineChart(c,true);instances.push(chart)});
    renderLegends();
  };

  const observer=new MutationObserver(()=>{instances.forEach(chart=>chart.draw());renderLegends()});
  addEventListener('DOMContentLoaded',()=>{init();observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']})});
})();
