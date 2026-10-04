(() => {
  const menu=document.getElementById('mobile-menu'),button=document.getElementById('mobile-menu-btn');
  button?.addEventListener('click',()=>{const open=menu.classList.toggle('open');button.setAttribute('aria-expanded',String(open));});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.classList.contains('open')){menu.classList.remove('open');button.setAttribute('aria-expanded','false');button.focus();}});
  const main=document.querySelector('main');if(main&&!main.id)main.id='main-content';
  const stamp=document.getElementById('freshness-times');
  const times=stamp?JSON.parse(stamp.textContent):{};
  const millis=value=>Date.parse(value.replace(' UTC','Z').replace(' EDT','-04:00').replace(' EST','-05:00').replace(' ','T'));
  function freshness(){
    const age=Date.now()-millis(times.generated),obsAge=Date.now()-millis(times.observed);
    const stale=!Number.isFinite(age)||!Number.isFinite(obsAge)||age>90*60000||obsAge>90*60000||age< -5*60000||obsAge< -5*60000;
    if(stale){document.querySelectorAll('[data-official-feed]').forEach(el=>el.textContent='Official alert information is out of date. Check NWS directly.');document.getElementById('freshness-label').textContent='Data stale or unavailable';document.querySelectorAll('[data-current-safety]').forEach(el=>el.hidden=true);const notice=document.getElementById('data-freshness');notice.style.background='#fff7ed';if(!document.getElementById('stale-detail')){const p=document.createElement('p');p.id='stale-detail';p.textContent='Estimates are out of date. Check official forecasts and actual conditions; roads cannot be assumed clear.';notice.append(p);}}
  }
  freshness();setInterval(freshness,60000);
  function offline(){let notice=document.getElementById('offline-notice');if(!navigator.onLine&&!notice){notice=document.createElement('aside');notice.id='offline-notice';notice.setAttribute('role','status');notice.textContent='Offline copy: observations and forecasts may be out of date. Check their times. Map tiles and external warnings need a connection.';document.querySelector('header')?.after(notice);}if(navigator.onLine&&notice)notice.remove();}
  offline();window.addEventListener('online',offline);window.addEventListener('offline',offline);
  if('serviceWorker'in navigator)navigator.serviceWorker.register('service-worker.js').catch(()=>{});
  document.getElementById('copy-topic')?.addEventListener('click',async event=>{const feedback=document.getElementById('copy-feedback');try{await navigator.clipboard.writeText(event.currentTarget.dataset.topic);feedback.textContent='Topic copied. Paste it into ntfy to subscribe.';}catch{feedback.textContent='Copy is unavailable. Select and copy the displayed topic manually.'}});
  const modes=['btn-map-current','btn-map-peak'],zooms=['btn-zoom-community','btn-zoom-property','btn-zoom-county'];
  for(const ids of [modes,zooms])ids.forEach((id,index)=>{const el=document.getElementById(id);if(!el)return;el.setAttribute('aria-pressed',String(index===0));el.addEventListener('click',()=>ids.forEach(other=>document.getElementById(other)?.setAttribute('aria-pressed',String(other===id))));});
  document.getElementById('report-form')?.addEventListener('submit',event=>{
    event.preventDefault();const form=event.currentTarget;if(!form.reportValidity())return;
    const field=name=>form.elements.namedItem(name).value;
    const text=`Observed flooding report (pending review)\nStreet/public location: ${field('location')}\nObserved at: ${field('time')} Eastern local time\nDepth if measured: ${field('depth')} inches\nConditions: ${field('notes')}\nConsent: contributor agrees to maintainer review; no people, home addresses, faces or license plates included.\nThis report is unverified and must not enter model training automatically.`;
    document.getElementById('report-draft').textContent=text;document.getElementById('report-result').hidden=false;
  });
  document.getElementById('download-report')?.addEventListener('click',()=>{const text=document.getElementById('report-draft').textContent;const url=URL.createObjectURL(new Blob([text],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='flood-observation-for-review.txt';a.click();URL.revokeObjectURL(url);});
})();
