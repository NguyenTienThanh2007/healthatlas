(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const storage = {
    get(key, fallback = []) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
    set(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
  };

  const escapeHTML = (s='') => String(s).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const escapeAttr = escapeHTML;
  const formatNum = n => Math.abs(n) >= 1000 ? n.toLocaleString(undefined,{maximumFractionDigits:1}) : Number(n).toFixed(1);

  const toast = (title, detail = '') => {
    const wrap = $('.toast-wrap'); if (!wrap) return;
    const el = document.createElement('div'); el.className = 'toast';
    el.innerHTML = `<strong>${escapeHTML(title)}</strong>${detail ? `<small>${escapeHTML(detail)}</small>` : ''}`;
    wrap.appendChild(el); setTimeout(() => el.remove(), 3000);
  };

  // ---------------------------------------------------------
  // Motion, reveal, parallax, magnetic controls, transitions
  // ---------------------------------------------------------
  if (matchMedia('(pointer:fine)').matches) {
    const glow = $('.pointer-glow');
    addEventListener('pointermove', e => { if (glow) { glow.style.left = `${e.clientX}px`; glow.style.top = `${e.clientY}px`; } }, {passive:true});
  }

  const io = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('show'); io.unobserve(entry.target); }
  }), {threshold:.05, rootMargin:'0px 0px -18px'});
  $$('.reveal').forEach(el => io.observe(el));

  const tiltTargets = $$('.tilt,.kpi-card,.panel,.module-card,.country-summary-card,.quality-meter-card');
  tiltTargets.forEach(card => {
    card.addEventListener('pointermove', e => {
      if (!matchMedia('(pointer:fine)').matches || document.documentElement.dataset.motion === 'reduced') return;
      const r = card.getBoundingClientRect();
      const x = (e.clientX-r.left)/r.width-.5, y = (e.clientY-r.top)/r.height-.5;
      card.style.transform = `perspective(1100px) rotateX(${(-y*1.8).toFixed(2)}deg) rotateY(${(x*2.5).toFixed(2)}deg) translateY(-2px)`;
    });
    card.addEventListener('pointerleave', () => card.style.transform = '');
  });

  $$('[data-parallax]').forEach(stage => stage.addEventListener('pointermove', e => {
    if (document.documentElement.dataset.motion === 'reduced') return;
    const r = stage.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
    $$('.float-card',stage).forEach((c,i)=>c.style.transform=`translate3d(${x*(12+i*2)}px,${y*(10+i*2)}px,${20+i*4}px)`);
    $('.globe-v4',stage)?.style.setProperty('transform',`translate3d(${x*-8}px,${y*-6}px,0)`);
  }));

  $$('.magnetic').forEach(btn => {
    btn.addEventListener('pointermove', e => {
      if (document.documentElement.dataset.motion === 'reduced') return;
      const r=btn.getBoundingClientRect();
      btn.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.04}px,${(e.clientY-r.top-r.height/2)*.08}px) translateY(-2px)`;
    });
    btn.addEventListener('pointerleave',()=>btn.style.transform='');
  });

  $$('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('http') || a.target === '_blank') return;
    a.addEventListener('click', e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.dataset.noTransition !== undefined) return;
      e.preventDefault(); document.body.classList.add('leaving'); setTimeout(()=>location.href=href,145);
    });
  });

  // ---------------------------------------------------------
  // Persistent workspace preferences
  // ---------------------------------------------------------
  const savedTheme = localStorage.getItem('gie:theme') || 'light';
  if (savedTheme === 'dark') document.documentElement.dataset.theme = 'dark';
  const savedDensity = localStorage.getItem('gie:density') || 'comfortable';
  if (savedDensity === 'compact') document.documentElement.dataset.density = 'compact';
  const savedMotion = localStorage.getItem('gie:motion') || 'full';
  if (savedMotion === 'reduced') document.documentElement.dataset.motion = 'reduced';

  const toggleTheme = () => {
    const dark = document.documentElement.dataset.theme === 'dark';
    if (dark) delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = 'dark';
    localStorage.setItem('gie:theme', dark ? 'light' : 'dark');
    toast(dark ? 'Light mode enabled' : 'Dark mode enabled');
  };
  $$('[data-action="theme"]').forEach(b=>b.addEventListener('click',toggleTheme));

  $('[data-action="menu"]')?.addEventListener('click',()=>$('#sidebar')?.classList.toggle('open'));
  $$('[data-action="focus"]').forEach(b=>b.addEventListener('click',()=>{document.body.classList.toggle('focus');toast(document.body.classList.contains('focus')?'Focus mode on':'Focus mode off')}));

  // ---------------------------------------------------------
  // Drawer and modal helpers
  // ---------------------------------------------------------
  const drawer = $('[data-drawer]'), drawerBackdrop = $('[data-drawer-backdrop]'), drawerTitle=$('[data-drawer-title]'), drawerKicker=$('[data-drawer-kicker]'), drawerBody=$('[data-drawer-body]');
  const openDrawer = (title, kicker, html) => { if(!drawer)return; drawerTitle.textContent=title; drawerKicker.textContent=kicker; drawerBody.innerHTML=html; drawer.hidden=false; drawerBackdrop.hidden=false; };
  const closeDrawer = () => { if(drawer) drawer.hidden=true; if(drawerBackdrop) drawerBackdrop.hidden=true; };
  $('[data-action="close-drawer"]')?.addEventListener('click',closeDrawer); drawerBackdrop?.addEventListener('click',closeDrawer);

  const modal = $('[data-modal]'), modalBackdrop=$('[data-modal-backdrop]'), modalTitle=$('[data-modal-title]'), modalKicker=$('[data-modal-kicker]'), modalBody=$('[data-modal-body]');
  const openModal = (title,kicker,html) => { if(!modal)return; modalTitle.textContent=title; modalKicker.textContent=kicker; modalBody.innerHTML=html; modal.hidden=false; modalBackdrop.hidden=false; };
  const closeModal = () => { if(modal) modal.hidden=true; if(modalBackdrop) modalBackdrop.hidden=true; };
  $('[data-action="close-modal"]')?.addEventListener('click',closeModal); modalBackdrop?.addEventListener('click',closeModal);

  // ---------------------------------------------------------
  // Saved views + recent navigation
  // ---------------------------------------------------------
  const getViews = () => storage.get('gie:saved-views', []);
  const saveView = () => {
    const views = getViews();
    const defaultName = document.title.replace(' · Country Profile','').replace('HealthAtlas','Overview').replace('Global Immunisation Explorer','Overview');
    const name = prompt('Name this saved view:', `${defaultName} · ${new Date().toLocaleDateString()}`);
    if (!name) return;
    views.unshift({id:Date.now(),name,url:location.href,created:new Date().toISOString()});
    storage.set('gie:saved-views',views.slice(0,30)); toast('View saved','You can reopen it from Saved views.');
  };
  const showSavedViews = () => {
    const views=getViews();
    const html = views.length ? views.map(v=>`<div class="drawer-card"><div class="drawer-card-row"><div><strong>${escapeHTML(v.name)}</strong><small>${new Date(v.created).toLocaleString()}</small></div><button class="row-icon" data-remove-view="${v.id}">×</button></div><button class="mini-action" data-open-view="${escapeAttr(v.url)}">Open saved view →</button></div>`).join('') : `<div class="empty compact"><p>No saved views yet.</p></div>`;
    openDrawer('Saved views','WORKSPACE',html);
    $$('[data-open-view]',drawerBody).forEach(b=>b.addEventListener('click',()=>location.href=b.dataset.openView));
    $$('[data-remove-view]',drawerBody).forEach(b=>b.addEventListener('click',()=>{storage.set('gie:saved-views',getViews().filter(v=>String(v.id)!==b.dataset.removeView));showSavedViews()}));
  };
  $$('[data-action="save-view"]').forEach(b=>b.addEventListener('click',saveView));
  $$('[data-action="saved-views"]').forEach(b=>b.addEventListener('click',showSavedViews));

  const recent=storage.get('gie:recent',[]).filter(x=>x.url!==location.href);
  recent.unshift({title:document.title,url:location.href,visited:new Date().toISOString()});
  storage.set('gie:recent',recent.slice(0,12));

  // ---------------------------------------------------------
  // Watchlist — stores id + name when available
  // ---------------------------------------------------------
  const normaliseWatch = list => list.map(item => typeof item === 'string' ? {name:item,id:''} : item).filter(x=>x?.name);
  const getWatch = () => normaliseWatch(storage.get('gie:watchlist', []));
  const setWatch = list => { storage.set('gie:watchlist', list); syncWatchButtons(); };
  const toggleWatch = (name,id='') => {
    let list=getWatch(); const key=id||name; const exists=list.some(x=>(x.id||x.name)===key);
    list=exists?list.filter(x=>(x.id||x.name)!==key):[{name,id},...list]; setWatch(list);
    toast(exists?'Removed from watchlist':'Added to watchlist',name);
  };
  const syncWatchButtons = () => {
    const list=getWatch();
    $$('[data-action="toggle-watch"]').forEach(b=>{const key=b.dataset.countryId||b.dataset.country;const active=list.some(x=>(x.id||x.name)===key);b.classList.toggle('watch-active',active); if(b.tagName==='BUTTON' && b.childElementCount===0) b.textContent=active?'♥':'♡'});
  };
  const showWatchlist = () => {
    const list=getWatch();
    const html=list.length?list.map(c=>`<div class="drawer-card"><div class="drawer-card-row"><div><strong>${escapeHTML(c.name)}</strong><small>${c.id?escapeHTML(c.id):'Saved country'}</small></div><button class="row-icon watch-active" data-unwatch="${escapeAttr(c.id||c.name)}">♥</button></div>${c.id?`<button class="mini-action" data-open-country="${escapeAttr(c.id)}">Open country profile →</button>`:''}</div>`).join(''):`<div class="empty compact"><p>Your watchlist is empty. Use ♡ on any country.</p></div>`;
    openDrawer('Watchlist','PERSONAL WORKSPACE',html);
    $$('[data-unwatch]',drawerBody).forEach(b=>b.addEventListener('click',()=>{const item=getWatch().find(x=>(x.id||x.name)===b.dataset.unwatch);if(item)toggleWatch(item.name,item.id);showWatchlist()}));
    $$('[data-open-country]',drawerBody).forEach(b=>b.addEventListener('click',()=>location.href=`/country/${encodeURIComponent(b.dataset.openCountry)}`));
  };
  document.addEventListener('click',e=>{const b=e.target.closest('[data-action="toggle-watch"]');if(b){e.preventDefault();toggleWatch(b.dataset.country||'Country',b.dataset.countryId||'')}});
  $$('[data-action="watchlist"]').forEach(b=>b.addEventListener('click',showWatchlist)); syncWatchButtons();

  // ---------------------------------------------------------
  // Compare tray — opens the real server-side compare route
  // ---------------------------------------------------------
  const getCompare=()=>storage.get('gie:compare',[]);
  const setCompare=list=>{storage.set('gie:compare',list.slice(0,4));renderCompareTray()};
  const addCompare = item => {
    let list=getCompare(); const key=item.id||item.country;
    if(list.some(x=>(x.id||x.country)===key)) { toast('Already selected',item.country); return; }
    if(list.length>=4){toast('Compare limit reached','Remove a country before adding another.');return;}
    list.push(item);setCompare(list);toast('Added to compare',item.country);
  };
  const renderCompareTray=()=>{
    const tray=$('[data-compare-tray]'), list=getCompare(); if(!tray)return;
    tray.hidden=!list.length; $('[data-compare-count]').textContent=list.length;
    $('[data-compare-chips]').innerHTML=list.map(x=>`<button class="compare-chip" data-remove-compare="${escapeAttr(x.id||x.country)}">${escapeHTML(x.country)} ×</button>`).join('');
    $$('[data-remove-compare]',tray).forEach(b=>b.addEventListener('click',()=>setCompare(getCompare().filter(x=>(x.id||x.country)!==b.dataset.removeCompare))));
  };
  document.addEventListener('click',e=>{const b=e.target.closest('[data-action="add-compare"]');if(!b)return;e.preventDefault();addCompare({id:b.dataset.countryId||'',country:b.dataset.country,region:b.dataset.region||'—',metric:b.dataset.metric||'Metric',value:b.dataset.value||'—',suffix:b.dataset.suffix||''})});
  $('[data-action="clear-compare"]')?.addEventListener('click',()=>setCompare([]));
  $('[data-action="open-compare"]')?.addEventListener('click',()=>{
    const list=getCompare(); if(!list.length)return;
    const ids=list.map(x=>x.id).filter(Boolean);
    if(ids.length){ const p=new URLSearchParams(); ids.forEach(id=>p.append('countries',id)); location.href=`/compare?${p.toString()}`; return; }
    const max=Math.max(...list.map(x=>Number(x.value)||0),1);
    const cards=list.map(x=>`<article class="compare-card"><small>${escapeHTML(x.region)}</small><strong>${escapeHTML(x.country)}</strong><span>${escapeHTML(x.metric)}</span><div class="profile-stat"><small>Current value</small><strong>${escapeHTML(String(x.value))}${escapeHTML(x.suffix)}</strong></div><div class="quality-meter"><i style="width:${Math.min(100,(Number(x.value)||0)/max*100)}%"></i></div></article>`).join('');
    openModal('Country comparison','COMPARE',`<div class="compare-card-grid">${cards}</div>`);
  }); renderCompareTray();

  // ---------------------------------------------------------
  // Smart insights from visible DOM
  // ---------------------------------------------------------
  const generateInsights = () => {
    const rows=$$('[data-country-row]'); const insights=[];
    if(rows.length){
      const parsed=rows.map(r=>({country:r.dataset.country,value:Number(r.dataset.value)||0,region:r.dataset.region||''})).sort((a,b)=>b.value-a.value);
      const avg=parsed.reduce((s,x)=>s+x.value,0)/parsed.length;
      insights.push(['↗',`${parsed[0].country} leads this view`, `Highest visible value: ${formatNum(parsed[0].value)}.`]);
      insights.push(['◎',`${rows.length} countries are visible`, `Average visible value: ${formatNum(avg)}.`]);
      if(parsed.length>1) insights.push(['⇄','Visible spread', `${formatNum(parsed[0].value-parsed[parsed.length-1].value)} units between highest and lowest.`]);
    } else {
      insights.push(['✦','No active result table yet','Run a query or open the Insights page for dataset-level analysis.']);
    }
    const regionRows=$$('[data-region-summary]');
    if(regionRows.length){const rr=regionRows.map(x=>({n:x.dataset.name,v:Number(x.dataset.value)||0})).sort((a,b)=>b.v-a.v);insights.push(['◉',`${rr[0].n} leads the regional view`,`Visible average: ${formatNum(rr[0].v)}%.`])}
    const html=insights.map(([icon,title,body])=>`<div class="insight-bullet"><span>${icon}</span><div><strong>${escapeHTML(title)}</strong><small>${escapeHTML(body)}</small></div></div>`).join('')+`<div class="drawer-card"><strong>Need deeper context?</strong><small>The Insights page uses the database directly for global leaders, long-term trends and infection context.</small><button class="mini-action" data-open-insights>Open Insights →</button></div>`;
    openDrawer('Smart insights','ON-DEVICE ANALYSIS',html);
    $('[data-open-insights]',drawerBody)?.addEventListener('click',()=>location.href='/insights');
  };
  $$('[data-action="insights"]').forEach(b=>b.addEventListener('click',generateInsights));
  $$('[data-action="data-quality"]').forEach(b=>b.addEventListener('click',()=>location.href='/data-quality'));

  // ---------------------------------------------------------
  // Tables and exports
  // ---------------------------------------------------------
  $$('[data-table-search]').forEach(input=>input.addEventListener('input',()=>{const t=$(input.dataset.tableSearch);if(!t)return;const q=input.value.trim().toLowerCase();$$('tbody tr',t).forEach(tr=>tr.hidden=q&&!tr.innerText.toLowerCase().includes(q))}));
  const currentTable=()=>$$('table').find(t=>t.offsetParent!==null)||$('table');
  const tableText=t=>$$('tr',t).map(tr=>$$('th,td',tr).map(c=>c.innerText.trim()).join('\t')).join('\n');
  const exportTable=()=>{const t=currentTable();if(!t)return toast('Nothing to export','Run a query first.');const rows=$$('tr',t).map(tr=>$$('th,td',tr).map(c=>`"${c.innerText.replace(/"/g,'""').trim()}"`).join(','));const blob=new Blob([rows.join('\n')],{type:'text/csv'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`global-immunisation-${document.body.dataset.endpoint||'data'}.csv`;a.click();URL.revokeObjectURL(url);toast('CSV exported')};
  $$('[data-action="export"]').forEach(b=>b.addEventListener('click',exportTable));
  $$('[data-action="copy-table"]').forEach(b=>b.addEventListener('click',async()=>{const t=currentTable();if(!t)return toast('Nothing to copy');await navigator.clipboard.writeText(tableText(t));toast('Table copied')}));
  $$('[data-action="print"]').forEach(b=>b.addEventListener('click',()=>window.print()));

  // ---------------------------------------------------------
  // Share link, settings, profile menu, shortcuts
  // ---------------------------------------------------------
  $$('[data-action="share"]').forEach(b=>b.addEventListener('click',async()=>{
    try { await navigator.clipboard.writeText(location.href); toast('Link copied','Share this exact view with someone else.'); }
    catch { prompt('Copy this link:',location.href); }
  }));

  const showSettings = () => {
    const theme=document.documentElement.dataset.theme==='dark'?'dark':'light';
    const density=document.documentElement.dataset.density==='compact'?'compact':'comfortable';
    const motion=document.documentElement.dataset.motion==='reduced'?'reduced':'full';
    openDrawer('Workspace settings','PERSONALIZATION',`<div class="settings-grid">
      <div class="setting-row"><div><strong>Appearance</strong><small>Choose light or dark surfaces.</small></div><div class="segmented"><button data-set-theme="light" class="${theme==='light'?'active':''}">Light</button><button data-set-theme="dark" class="${theme==='dark'?'active':''}">Dark</button></div></div>
      <div class="setting-row"><div><strong>Density</strong><small>Control spacing for data-heavy screens.</small></div><div class="segmented"><button data-set-density="comfortable" class="${density==='comfortable'?'active':''}">Comfort</button><button data-set-density="compact" class="${density==='compact'?'active':''}">Compact</button></div></div>
      <div class="setting-row"><div><strong>Motion</strong><small>Reduce animated transitions if preferred.</small></div><div class="segmented"><button data-set-motion="full" class="${motion==='full'?'active':''}">Full</button><button data-set-motion="reduced" class="${motion==='reduced'?'active':''}">Reduced</button></div></div>
      <div class="setting-row"><div><strong>Keyboard shortcuts</strong><small>See faster ways to move around the workspace.</small></div><button class="mini-action" data-open-shortcuts>View shortcuts</button></div>
    </div>`);
    $$('[data-set-theme]',drawerBody).forEach(x=>x.addEventListener('click',()=>{if(x.dataset.setTheme==='dark')document.documentElement.dataset.theme='dark';else delete document.documentElement.dataset.theme;localStorage.setItem('gie:theme',x.dataset.setTheme);showSettings()}));
    $$('[data-set-density]',drawerBody).forEach(x=>x.addEventListener('click',()=>{if(x.dataset.setDensity==='compact')document.documentElement.dataset.density='compact';else delete document.documentElement.dataset.density;localStorage.setItem('gie:density',x.dataset.setDensity);showSettings()}));
    $$('[data-set-motion]',drawerBody).forEach(x=>x.addEventListener('click',()=>{if(x.dataset.setMotion==='reduced')document.documentElement.dataset.motion='reduced';else delete document.documentElement.dataset.motion;localStorage.setItem('gie:motion',x.dataset.setMotion);showSettings()}));
    $('[data-open-shortcuts]',drawerBody)?.addEventListener('click',()=>{closeDrawer();openShortcuts()});
  };
  $$('[data-action="settings"]').forEach(b=>b.addEventListener('click',showSettings));

  $$('[data-action="profile-menu"]').forEach(b=>b.addEventListener('click',()=>{
    const views=getViews().length, watch=getWatch().length, compare=getCompare().length;
    openDrawer('Your workspace','LOCAL PROFILE',`<div class="profile-hero"><div class="profile-meta"><h3>Tiến Thành</h3><p>Local analytics workspace</p></div><div class="profile-flag">T</div></div><div class="profile-grid"><div class="profile-stat"><small>Saved views</small><strong>${views}</strong></div><div class="profile-stat"><small>Watchlist</small><strong>${watch}</strong></div><div class="profile-stat"><small>Compare tray</small><strong>${compare}</strong></div></div><div class="modal-actions"><button class="btn ghost" data-action-local="settings">Settings</button><button class="btn ghost" data-action-local="shortcuts">Shortcuts</button></div>`);
    $('[data-action-local="settings"]',drawerBody)?.addEventListener('click',showSettings);
    $('[data-action-local="shortcuts"]',drawerBody)?.addEventListener('click',()=>{closeDrawer();openShortcuts()});
  }));

  const shortcuts=$('[data-shortcuts]');
  const openShortcuts=()=>{if(shortcuts)shortcuts.hidden=false};
  const closeShortcuts=()=>{if(shortcuts)shortcuts.hidden=true};
  $('[data-action="close-shortcuts"]')?.addEventListener('click',closeShortcuts);
  shortcuts?.addEventListener('click',e=>{if(e.target===shortcuts)closeShortcuts()});

  // range inputs
  $$('[data-range-input]').forEach(input=>{const out=input.parentElement?.querySelector('[data-range-output]');const sync=()=>{if(out)out.value=`${Math.round(Number(input.value))}%`};sync();input.addEventListener('input',sync)});

  // loading state
  $$('form').forEach(form=>form.addEventListener('submit',()=>{const host=form.closest('.filter-card'); if(!host)return; host.style.position='relative';const o=document.createElement('div');o.className='skeleton-overlay';o.innerHTML='<div class="skeleton-loader"><i></i><i></i><i></i></div>';host.appendChild(o)}));

  // ---------------------------------------------------------
  // Command palette + server-backed global search
  // ---------------------------------------------------------
  const palette=$('[data-command-palette]'), paletteBackdrop=$('[data-command-backdrop]'), paletteInput=$('[data-palette-input]'), paletteResults=$('[data-palette-results]');
  const baseCommands=[
    {name:'Overview',detail:'Workspace home',url:'/'},
    {name:'Travel Health Planner',detail:'Build a destination health snapshot',url:'/travel'},
    {name:'Vaccination Explorer',detail:'Filter vaccination coverage',url:'/vaccination'},
    {name:'Improvement Analysis',detail:'Compare two years',url:'/improvement'},
    {name:'Infection Explorer',detail:'Explore disease burden',url:'/infections'},
    {name:'Infection Rate',detail:'Global infection benchmark',url:'/infection-rate'},
    {name:'Country Compare',detail:'Compare up to four countries',url:'/compare'},
    {name:'Global Insights',detail:'Leaders, trends and context',url:'/insights'},
    {name:'Data Quality Center',detail:'Completeness and quality flags',url:'/data-quality'},
    {name:'Mission',detail:'Personas and team',url:'/mission'}
  ];
  function paletteItem(name,detail,url,type){return `<div class="palette-item" data-palette-type="${type}" data-url="${escapeAttr(url)}" data-name="${escapeAttr(name)}"><div><strong>${escapeHTML(name)}</strong><small>${escapeHTML(detail)}</small></div><em>↵</em></div>`}
  const searchAPI = async q => {
    if((q||'').trim().length<2)return [];
    try { const res=await fetch(`/api/search?q=${encodeURIComponent(q.trim())}`); return res.ok?await res.json():[]; }
    catch { return []; }
  };
  const renderPalette = async q => {
    const query=(q||'').toLowerCase(); const views=getViews();
    const pages=baseCommands.filter(x=>(x.name+' '+x.detail).toLowerCase().includes(query));
    const saved=views.filter(x=>x.name.toLowerCase().includes(query)).slice(0,5);
    const remote=await searchAPI(q);
    paletteResults.innerHTML=`<div class="palette-section">Pages</div>${pages.map(x=>paletteItem(x.name,x.detail,x.url,'page')).join('')}${remote.length?`<div class="palette-section">Dataset search</div>${remote.map(x=>paletteItem(x.name,`${x.type} · ${x.id}`,x.url,'page')).join('')}`:''}${saved.length?`<div class="palette-section">Saved views</div>${saved.map(v=>paletteItem(v.name,'Saved workspace',v.url,'page')).join('')}`:''}<div class="palette-section">Actions</div>${paletteItem('Toggle theme','Light / dark mode','#','theme')}${paletteItem('Smart insights','Analyse visible results','#','insights')}${paletteItem('Workspace settings','Density and motion','#','settings')}${paletteItem('Keyboard shortcuts','Navigation help','#','shortcuts')}`;
    $$('[data-palette-type="page"]',paletteResults).forEach(x=>x.addEventListener('click',()=>location.href=x.dataset.url));
    $('[data-palette-type="theme"]',paletteResults)?.addEventListener('click',()=>{toggleTheme();closePalette()});
    $('[data-palette-type="insights"]',paletteResults)?.addEventListener('click',()=>{closePalette();generateInsights()});
    $('[data-palette-type="settings"]',paletteResults)?.addEventListener('click',()=>{closePalette();showSettings()});
    $('[data-palette-type="shortcuts"]',paletteResults)?.addEventListener('click',()=>{closePalette();openShortcuts()});
  };
  const openPalette=()=>{if(!palette)return;palette.hidden=false;paletteBackdrop.hidden=false;paletteInput.value='';renderPalette('');setTimeout(()=>paletteInput.focus(),20)};
  const closePalette=()=>{if(palette)palette.hidden=true;if(paletteBackdrop)paletteBackdrop.hidden=true};
  $$('[data-action="open-command"]').forEach(b=>b.addEventListener('click',openPalette)); paletteBackdrop?.addEventListener('click',closePalette); paletteInput?.addEventListener('input',()=>renderPalette(paletteInput.value));

  const inlineInput=$('[data-command-input]'), inlineMenu=$('[data-command-menu]');
  let inlineToken=0;
  const renderInline=async q=>{
    if(!inlineMenu)return; const token=++inlineToken; const query=(q||'').trim();
    const pages=baseCommands.filter(x=>x.name.toLowerCase().includes(query.toLowerCase())).slice(0,5);
    const remote=await searchAPI(query); if(token!==inlineToken)return;
    const all=[...pages,...remote.map(x=>({name:x.name,detail:`${x.type} · ${x.id}`,url:x.url}))].slice(0,10);
    inlineMenu.innerHTML=all.map(x=>`<a class="command-item" href="${x.url}"><span>${escapeHTML(x.name)}</span><small>${escapeHTML(x.detail||'Open')}</small></a>`).join('');inlineMenu.hidden=!all.length;
  };
  inlineInput?.addEventListener('focus',()=>renderInline(inlineInput.value)); inlineInput?.addEventListener('input',()=>renderInline(inlineInput.value));

  // ---------------------------------------------------------
  // Keyboard navigation
  // ---------------------------------------------------------
  let gPending=false, gTimer=null;
  document.addEventListener('click',e=>{if(inlineMenu&&!e.target.closest('.command-search'))inlineMenu.hidden=true});
  document.addEventListener('keydown',e=>{
    const inputLike=['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName);
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette();return}
    if(e.key==='/'&&!inputLike){e.preventDefault();inlineInput?.focus();return}
    if(e.key==='?'&&!inputLike){e.preventDefault();openShortcuts();return}
    if(e.key==='Escape'){closeDrawer();closeModal();closePalette();closeShortcuts();$('#sidebar')?.classList.remove('open');return}
    if(!inputLike && e.key.toLowerCase()==='g'){gPending=true;clearTimeout(gTimer);gTimer=setTimeout(()=>gPending=false,900);return}
    if(gPending&&!inputLike){const k=e.key.toLowerCase();gPending=false;clearTimeout(gTimer);if(k==='o')location.href='/';else if(k==='c')location.href='/compare';else if(k==='i')location.href='/insights';}
  });
})();
