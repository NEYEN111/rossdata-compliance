'use strict';
document.addEventListener('DOMContentLoaded', () => {
  const source = document.getElementById('dashboard-data');
  if (!source || typeof Chart === 'undefined') return;
  const data = JSON.parse(source.textContent);
  Chart.defaults.font.family = 'Segoe UI, Arial, sans-serif';
  Chart.defaults.font.size = 9;
  Chart.defaults.color = '#8694a5';
  const common = {responsive:true,maintainAspectRatio:false,animation:{duration:550},plugins:{legend:{display:false}}};
  new Chart(document.getElementById('risk-chart'), {
    type:'bar',data:{labels:Object.keys(data.risks),datasets:[{data:Object.values(data.risks),backgroundColor:['#7ca996','#e0bd72','#ce9391','#ad626a'],borderRadius:4,barThickness:29}]},
    options:{...common,scales:{x:{grid:{display:false},border:{display:false}},y:{beginAtZero:true,ticks:{precision:0},grid:{color:'#edf1f5'},border:{display:false}}}}
  });
  new Chart(document.getElementById('country-chart'), {
    type:'bar',data:{labels:Object.keys(data.countries),datasets:[{data:Object.values(data.countries),backgroundColor:'#648faa',borderRadius:3,barThickness:10}]},
    options:{...common,indexAxis:'y',scales:{x:{beginAtZero:true,ticks:{precision:0},grid:{color:'#eff3f7'},border:{display:false}},y:{grid:{display:false},border:{display:false}}}}
  });
  new Chart(document.getElementById('state-chart'), {
    type:'doughnut',data:{labels:Object.keys(data.states),datasets:[{data:Object.values(data.states),backgroundColor:['#75a58f','#dfbd73','#bf787b','#c4ced9'],borderWidth:4,borderColor:'#fff',hoverOffset:3}]},
    options:{...common,cutout:'73%'}
  });
});
