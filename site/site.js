const select=document.getElementById('variant'),frame=document.getElementById('preview');
if(select&&frame){const scenes=JSON.parse(frame.dataset.scenes);select.addEventListener('change',()=>{const variant=scenes[Number(select.value)];frame.src='../../viewer/?embed=1&scene='+encodeURIComponent(variant.scene);});}
