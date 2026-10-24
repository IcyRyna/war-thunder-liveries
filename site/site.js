const select=document.getElementById('variant'),frame=document.getElementById('preview');
if(select&&frame){const scenes=JSON.parse(frame.dataset.scenes);select.addEventListener('change',()=>{const variant=scenes[Number(select.value)];frame.src='../../viewer/?embed=1&scene='+encodeURIComponent(variant.scene);});}

const filters=[...document.querySelectorAll('[data-category]')],groups=[...document.querySelectorAll('[data-section]')];
if(filters.length){
  function applyCategory(key,writeURL=false){
    if(!filters.some(b=>b.dataset.category===key))key='all';
    for(const b of filters)b.setAttribute('aria-pressed',String(b.dataset.category===key));
    for(const group of groups)group.hidden=key!=='all'&&group.dataset.section!==key;
    const count=groups.filter(g=>!g.hidden).reduce((n,g)=>n+g.querySelectorAll('.work').length,0);
    const label=key==='all'?'全部作品':groups.find(g=>g.dataset.section===key).querySelector('h2').textContent;
    document.getElementById('filterResult').textContent=label+' · '+count+' 套';
    if(writeURL){const url=new URL(location.href);key==='all'?url.searchParams.delete('category'):url.searchParams.set('category',key);history.pushState({},'',url);}
  }
  for(const b of filters)b.addEventListener('click',()=>applyCategory(b.dataset.category,true));
  addEventListener('popstate',()=>applyCategory(new URLSearchParams(location.search).get('category')||'all'));
  applyCategory(new URLSearchParams(location.search).get('category')||'all');
}
