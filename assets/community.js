(() => {
  const menu=document.getElementById('mobile-menu'),button=document.getElementById('mobile-menu-btn');
  button?.addEventListener('click',()=>{const open=menu.classList.toggle('open');button.setAttribute('aria-expanded',String(open));});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.classList.contains('open')){menu.classList.remove('open');button.setAttribute('aria-expanded','false');button.focus();}});
  const main=document.querySelector('main');if(main&&!main.id)main.id='main-content';
  const stamp=document.getElementById('freshness-times');
  const times=stamp?JSON.parse(stamp.textContent):{};
  const millis=value=>Date.parse(String(value||'').replace(' UTC','Z').replace(' EDT','-04:00').replace(' EST','-05:00').replace(' ','T'));
  const ageText=age=>!Number.isFinite(age)?'unknown age':age<0?'clock mismatch':age<3600000?`${Math.floor(age/60000)} minutes old`:`${(age/3600000).toFixed(1)} hours old`;
  function freshness(){
    const age=Date.now()-millis(times.generated),obsAge=Date.now()-millis(times.observed),forecastAge=Date.now()-millis(times.forecastSaved);
    const stale=!Number.isFinite(age)||!Number.isFinite(obsAge)||age>90*60000||obsAge>90*60000||age< -5*60000||obsAge< -5*60000;
    const expired=Number.isFinite(millis(times.forecastEnd))&&Date.now()>millis(times.forecastEnd);
    const degraded=stale||times.quality?.state==='degraded';
    const ageLabel=document.getElementById('update-age');
    if(ageLabel)ageLabel.textContent=`Website update: ${ageText(age)}. Observation: ${ageText(obsAge)}. Forecast saved: ${ageText(forecastAge)}.`;
    if(degraded){
      if(stale)document.querySelectorAll('[data-official-feed]').forEach(el=>el.textContent='Official alert information is out of date. Check NWS directly.');
      const label=document.getElementById('freshness-label');if(label)label.textContent=expired?'Forecast expired: last available estimates shown':'Data stale or incomplete: last available estimates shown';
      document.querySelectorAll('[data-age-label]').forEach(el=>el.textContent=el.dataset.lastLabel);
      document.querySelectorAll('[data-current-safety]').forEach(el=>{
        el.hidden=false;el.classList.add('outdated-estimate');
        if(!el.querySelector('.estimate-age-note')){
          const p=document.createElement('p');p.className='estimate-age-note';
          p.textContent=expired?'Historical forecast: its valid period has ended. These values do not describe current conditions.':'Last available estimates: check the dates below. Current conditions and road safety cannot be confirmed.';
          if(el.tagName==='DETAILS')el.querySelector('summary')?.after(p);else el.prepend(p);
        }
      });
      const notice=document.getElementById('data-freshness');
      if(notice){notice.classList.add('data-degraded');let p=document.getElementById('stale-detail');if(!p){p=document.createElement('p');p.id='stale-detail';notice.append(p);}p.textContent=stale?'Updates are overdue or gauge data is missing. The last saved forecast remains visible for reference. Check pipeline status for failure details and official forecasts for current guidance.':`${(times.quality?.reasons||[]).join(' ')} Last available estimates remain visible for reference.`;}
    }
  }
  freshness();setInterval(freshness,60000);
  document.getElementById('refresh-data')?.addEventListener('click',()=>window.location.reload());
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
