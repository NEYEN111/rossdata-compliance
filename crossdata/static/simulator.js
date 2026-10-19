'use strict';
document.addEventListener('DOMContentLoaded',()=>{
  const form=document.getElementById('scenario-form'); if(!form) return;
  const catalog=JSON.parse(document.getElementById('scenario-catalog').textContent);
  const token=form.querySelector('[name=csrf_token]').value;
  const get=id=>document.getElementById(id);
  const initialOptions=Array.from(get('country_id').options).map(o=>({value:o.value,label:o.textContent,code:o.dataset.code}));
  let sequence=0,timer,controller;
  function updateChoices(){
    const treatment=catalog.find(t=>String(t.id)===get('treatment_id').value);
    if(!treatment) return;
    const previous=get('country_id').value;
    get('country_id').replaceChildren(...initialOptions.filter(o=>treatment.countries.includes(Number(o.value))).map(o=>{const el=new Option(o.label,o.value);el.dataset.code=o.code;return el;}));
    if(treatment.countries.includes(Number(previous))) get('country_id').value=previous;
    const evidence=get('evidence_id').value;
    get('evidence_id').replaceChildren(new Option('Sin evidencia',''),...treatment.evidences.filter(e=>String(e.country)===get('country_id').value).map(e=>new Option(`${e.name} · ${e.status}`,e.id)));
    if(Array.from(get('evidence_id').options).some(o=>o.value===evidence))get('evidence_id').value=evidence;
  }
  function payload(){const data=Object.fromEntries(new FormData(form).entries());data.checks=Array.from(form.querySelectorAll('[name=checks]:checked')).map(el=>el.value);delete data.csrf_token;return data;}
  function element(tag,text,cls){const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;}
  async function evaluate(){
    const requestId=++sequence;controller?.abort();controller=new AbortController();
    document.querySelector('.lab-output').setAttribute('aria-busy','true');
    try{
      const response=await fetch('/simulador/evaluar',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify(payload()),signal:controller.signal});
      if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('La sesión venció. Recarga la página e inicia sesión.');
      const result=await response.json();if(requestId!==sequence)return;if(!response.ok)throw new Error(result.error||'No se pudo evaluar.');
      get('scenario-error').hidden=true;
      get('before-pending').textContent=result.before_pending;get('after-pending').textContent=result.after_pending;
      get('scenario-outcome').textContent=result.outcome;get('scenario-category').textContent=result.category;get('scenario-risk').textContent=result.initial_risk;
      get('scenario-alerts').replaceChildren(...result.alerts.map(message=>element('p',message,'scenario-alert')));
      get('scenario-checklist').replaceChildren(...result.items.map(item=>{const card=element('article','',''+(item.addressed?'addressed':''));card.append(element('strong',`${item.addressed?'Documentada en ensayo':'Pendiente'} · ${item.title}`),element('p',item.reason));return card;}));
      get('scenario-reference-title').textContent=result.reference.title;get('scenario-reference-link').href=result.reference.source;
    }catch(error){if(error.name!=='AbortError'&&requestId===sequence){get('scenario-error').hidden=false;get('scenario-error').className='alert alert-danger';get('scenario-error').textContent=error.message;get('scenario-outcome').textContent='Evaluación no disponible';get('before-pending').textContent='—';get('after-pending').textContent='—';}}
    finally{if(requestId===sequence)document.querySelector('.lab-output').setAttribute('aria-busy','false');}
  }
  function schedule(){clearTimeout(timer);timer=setTimeout(evaluate,250);}
  form.addEventListener('input',schedule);form.addEventListener('change',event=>{if(['treatment_id','country_id'].includes(event.target.id))updateChoices();schedule();});
  form.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);evaluate();});
  function selectCode(id,code){const option=Array.from(get(id).options).find(o=>o.dataset.code===code);if(option)get(id).value=option.value;}
  function preset(name){form.reset();const t=catalog.find(t=>t.name===(name==='academic'?'Registro académico':'Bienestar estudiantil'))||catalog[0];if(!t)return;get('treatment_id').value=t.id;updateChoices();selectCode('country_id',name==='academic'?'PE':'ES');updateChoices();selectCode('destination_id',name==='academic'?'PE':'US');get('data_type').value=name==='academic'?'Historial académico':'Salud';get('original').value=name==='academic'?'Gestión académica':'Bienestar';get('proposed').value=name==='health'?'Publicidad':get('original').value;document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b.dataset.preset===name));get('scenario-title')&&(get('scenario-title').value=name==='health'?'Salud y nueva finalidad · Caso 7':name==='cloud'?'Bienestar y proveedor cloud · Caso 7':'Uso académico · Caso 7');get('save-message')&&(get('save-message').textContent='');evaluate();}
  document.querySelectorAll('[data-preset]').forEach(button=>button.addEventListener('click',()=>preset(button.dataset.preset)));
  get('reset-scenario').addEventListener('click',()=>preset('health'));
  get('save-scenario')?.addEventListener('click',async()=>{const button=get('save-scenario');button.disabled=true;try{const response=await fetch('/simulador/guardar',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({...payload(),title:get('scenario-title').value})});if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('Recarga la página para renovar la sesión.');const result=await response.json();if(!response.ok)throw new Error(result.error||'No se pudo guardar.');const link=element('a','Comparación guardada. Abrir ensayo →');link.href=result.url;get('save-message').replaceChildren(link);}catch(error){get('save-message').textContent=error.message;}finally{button.disabled=false;}});
  updateChoices();evaluate();
});
